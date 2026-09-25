"""Groq client (OpenAI-compatible) returning validated Pydantic models, with an optional fallback model.

Several API keys can be configured; on a rate limit the call moves to the key that is
available soonest, so one exhausted key (e.g. its daily token cap) does not stop the run.
"""

import json
import logging
import re
import threading
import time
from typing import TypeVar


from openai import (APIConnectionError, APITimeoutError, AuthenticationError, BadRequestError, InternalServerError,
                    OpenAI, RateLimitError)
from pydantic import BaseModel, ValidationError

from .config import Settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

CHARS_PER_TOKEN = 3.8  # measured ~4.5 on this workload; kept slightly conservative
MIN_OUTPUT_TOKENS = 1500
# If every key is blocked for longer than this (daily caps), fail instead of waiting.
MAX_RATE_LIMIT_WAIT_SECONDS = 120
FALLBACK_RATE_LIMIT_RETRIES = 3
_TRY_AGAIN_RE = re.compile(r"try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", re.I)


class LLMError(RuntimeError):
    pass


def _retry_after(exc: RateLimitError) -> float:
    """Seconds until the key is usable again, from the header or Groq's message."""
    header = exc.response.headers.get("retry-after") if exc.response is not None else None
    try:
        if header:
            return float(header)
    except ValueError:
        pass
    if m := _TRY_AGAIN_RE.search(str(exc)):
        h, mnt, sec = (float(x) if x else 0.0 for x in m.groups())
        if h or mnt or sec:
            return h * 3600 + mnt * 60 + sec
    return 20.0


class _KeyPool:
    """API clients, one per key, with a per-key cooldown after a 429 (thread-safe)."""

    def __init__(self, settings: Settings):
        keys = settings.all_groq_keys()
        if not keys and not settings.fallback_llm_api_key.get_secret_value():
            raise LLMError("No Groq API key configured. Set GROQ_API_KEY (and optionally GROQ_API_KEYS) "
                           "or FALLBACK_LLM_API_KEY in .env.")
        # Rate limits are handled here (switch key); the SDK still retries 5xx / connection errors.
        self.clients = [
            OpenAI(
                api_key=k,
                base_url=settings.groq_base_url,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            )
            for k in keys
        ]
        self.ready_at = [0.0] * len(keys)
        self.lock = threading.Lock()

    def pick(self) -> tuple[int, float]:
        """Index of the key available soonest, and how long until it is."""
        with self.lock:
            idx = min(range(len(self.clients)), key=lambda i: self.ready_at[i])
            return idx, max(0.0, self.ready_at[idx] - time.time())

    def cool_down(self, idx: int, seconds: float) -> None:
        with self.lock:
            self.ready_at[idx] = max(self.ready_at[idx], time.time() + seconds)


def _extract_json(text: str) -> str:
    """Strip reasoning (<think> blocks of reasoning models), markdown fences and prose around a JSON object."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("Model response did not contain a JSON object.")
    return text[start : end + 1]


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._keys = _KeyPool(settings)
        self._fallback = (
            OpenAI(
                api_key=settings.fallback_llm_api_key.get_secret_value(),
                base_url=settings.fallback_llm_base_url,
                timeout=settings.fallback_llm_timeout_seconds,
                max_retries=1,
            )
            if settings.fallback_llm_api_key.get_secret_value()
            else None
        )
        log.info("Groq keys configured: %d; fallback model: %s", len(self._keys.clients),
                 settings.fallback_llm_model if self._fallback else "none")

    def _create(self, *, use_groq: bool = True, **kwargs):
        """Groq first; the fallback model when Groq is exhausted, failing or not configured."""
        if use_groq and self._keys.clients:
            try:
                return self._create_groq(**kwargs)
            except (LLMError, AuthenticationError) as exc:
                if not self._fallback:
                    raise
                log.warning("Groq unavailable (%s); using fallback model %s", exc, self.settings.fallback_llm_model)
        if not self._fallback:
            raise LLMError("Request too large for Groq and no FALLBACK_LLM_API_KEY is configured.")
        return self._create_fallback(**kwargs)

    def _create_fallback(self, *, model, reasoning_effort=None, **kwargs):
        """Same request on the fallback API (OpenAI by default). Parameters a model rejects (e.g. a custom
        temperature on reasoning models, or reasoning_effort on non-reasoning ones) are dropped and the call
        is retried; rate limits are retried with a pause."""
        kwargs["model"] = self.settings.fallback_llm_model
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        for attempt in range(FALLBACK_RATE_LIMIT_RETRIES + 1):
            try:
                return self._fallback.chat.completions.create(**kwargs)
            except BadRequestError as exc:
                bad = next((p for p in ("reasoning_effort", "temperature", "response_format") if p in kwargs and p in str(exc)), None)
                if "max_completion_tokens" in str(exc) and "max_completion_tokens" in kwargs:
                    kwargs["max_tokens"] = kwargs.pop("max_completion_tokens")   # older OpenAI-compatible servers
                elif bad:
                    log.info("Fallback model does not accept %s; retrying without it", bad)
                    kwargs.pop(bad)
                else:
                    raise
            except RateLimitError:
                if attempt == FALLBACK_RATE_LIMIT_RETRIES:
                    raise LLMError(f"Fallback model {self.settings.fallback_llm_model} is rate-limited; try again later.")
                log.warning("Fallback model rate-limited; retrying in %ds", 15 * (attempt + 1))
                time.sleep(15 * (attempt + 1))
            except (APIConnectionError, APITimeoutError) as exc:
                raise LLMError(f"Fallback model at {self.settings.fallback_llm_base_url} is unreachable: {exc}") from exc
        raise LLMError("Fallback request kept failing.")

    def _create_groq(self, **kwargs):
        """chat.completions.create with key rotation on 429 and backoff on transient errors."""
        for attempt in range(self.settings.llm_max_retries * len(self._keys.clients) + 1):
            idx, wait = self._keys.pick()
            # With a fallback model, switch to it quickly; without one, wait for the cap to reset
            # (up to LLM_MAX_WAIT_MINUTES) rather than fail, so the run finishes at full quality.
            max_wait = MAX_RATE_LIMIT_WAIT_SECONDS if self._fallback else self.settings.llm_max_wait_minutes * 60
            if wait > max_wait:
                raise LLMError(
                    f"All {len(self._keys.clients)} Groq key(s) are rate-limited (daily cap reached); "
                    f"the next one is free in about {wait / 60:.0f} minutes. Add another key to "
                    "GROQ_API_KEYS in .env or try later."
                )
            if wait > MAX_RATE_LIMIT_WAIT_SECONDS:
                log.warning("All Groq keys hit their cap; waiting %.0f minutes (until %s) and continuing",
                            wait / 60, time.strftime("%H:%M", time.localtime(time.time() + wait)))
            elif wait:
                log.info("All keys cooling down; waiting %.0fs", wait)
            if wait:
                time.sleep(wait)
            try:
                return self._keys.clients[idx].chat.completions.create(**kwargs)
            except RateLimitError as exc:
                seconds = _retry_after(exc)
                self._keys.cool_down(idx, seconds)
                log.warning("Groq key #%d rate-limited for %.0fs; switching key if possible", idx + 1, seconds)
            except (APIConnectionError, APITimeoutError, InternalServerError) as exc:
                delay = min(30.0, 2.0 ** attempt)
                log.warning("Groq request failed (%s); retrying in %.0fs", type(exc).__name__, delay)
                time.sleep(delay)
        raise LLMError("Groq request kept failing after retries.")

    def _output_budget(self, messages: list[dict]) -> int:
        """Largest max_completion_tokens that keeps the request within the TPM limit."""
        cap = self.settings.llm_max_tokens
        if not self.settings.llm_tpm_limit:
            return cap
        est_input = int(sum(len(m["content"]) for m in messages) / CHARS_PER_TOKEN) + 50
        budget = min(cap, self.settings.llm_tpm_limit - est_input - 200)
        if budget < MIN_OUTPUT_TOKENS:
            raise LLMError(
                f"Input is too large (~{est_input} tokens) for the Groq rate limit of "
                f"{self.settings.llm_tpm_limit} tokens/minute. Shorten the job description "
                "or upgrade the Groq plan and set LLM_TPM_LIMIT=0."
            )
        return budget

    def structured(
        self,
        system: str,
        user: str,
        model_cls: type[T],
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        temperature: float | None = None,
        prefix: str = "",
        attempts: int = 2,
    ) -> T:
        """Single-turn call whose JSON answer is parsed into `model_cls`.

        On malformed JSON the request is re-sent once with the error appended.
        `prefix` is sent first, before `system`: shared context (the resume) placed there is
        identical across calls, so the provider's prompt cache can reuse it.
        """
        model = model or self.settings.groq_model
        effort = reasoning_effort or self.settings.reasoning_effort
        note = ""
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            messages = [
                *([{"role": "system", "content": prefix}] if prefix else []),
                {"role": "system", "content": system},
                {"role": "user", "content": user + note},
            ]
            started = time.perf_counter()
            try:
                budget, use_groq = self._output_budget(messages), True
            except LLMError:
                if not self._fallback:
                    raise
                budget, use_groq = self.settings.llm_max_tokens, False  # too large for Groq's per-minute limit
            try:
                response = self._create(
                    use_groq=use_groq,
                    model=model,
                    temperature=self.settings.llm_temperature if temperature is None else temperature,
                    max_completion_tokens=budget,
                    reasoning_effort=effort,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except BadRequestError as exc:
                # Groq rejects generations that are not valid JSON (code json_validate_failed).
                if "json_validate_failed" not in str(exc):
                    raise
                last_error = exc
                log.warning("%s attempt %d: invalid JSON from model", model_cls.__name__, attempt)
                # Usually the reasoning used up the output budget; think less on the retry.
                effort = "low"
                note = "\n\nIMPORTANT: your previous answer was not valid JSON. Return one valid JSON object."
                continue

            choice = response.choices[0]
            usage = response.usage
            details = getattr(usage, "prompt_tokens_details", None)
            log.info(
                "LLM %s via %s attempt %d: %.1fs, tokens in=%s (cached=%s) out=%s",
                model_cls.__name__,
                getattr(response, "model", None) or model,
                attempt,
                time.perf_counter() - started,
                getattr(usage, "prompt_tokens", "?"),
                getattr(details, "cached_tokens", 0) if details else 0,
                getattr(usage, "completion_tokens", "?"),
            )
            try:
                return model_cls.model_validate_json(_extract_json(choice.message.content or ""))
            except (ValidationError, LLMError, json.JSONDecodeError) as exc:
                last_error = exc
                log.warning(
                    "%s attempt %d: unusable JSON (finish_reason=%s): %s",
                    model_cls.__name__, attempt, choice.finish_reason, exc,
                )
                if choice.finish_reason == "length":
                    effort = "low"
                    note = (
                        "\n\nIMPORTANT: your previous answer was cut off by the length limit. "
                        "Think briefly and return the complete JSON object only."
                    )
                else:
                    note = f"\n\nIMPORTANT: your previous answer failed validation:\n{exc}\nReturn the corrected JSON object only."

        raise LLMError(f"Model failed to return valid {model_cls.__name__} JSON: {last_error}")

"""Groq client (OpenAI-compatible) returning validated Pydantic models."""

import json
import logging
import re
import time
from typing import TypeVar

from openai import BadRequestError, OpenAI
from pydantic import BaseModel, ValidationError

from .config import Settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

CHARS_PER_TOKEN = 3.8  # measured ~4.5 on this workload; kept slightly conservative
MIN_OUTPUT_TOKENS = 1500


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> str:
    """Strip accidental markdown fences / prose around a JSON object."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("Model response did not contain a JSON object.")
    return text[start : end + 1]


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        # The SDK retries 429 / 5xx / connection errors, honouring Groq's retry-after header.
        self._client = OpenAI(
            api_key=settings.groq_api_key.get_secret_value(),
            base_url=settings.groq_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

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
        attempts: int = 2,
    ) -> T:
        """Single-turn call whose JSON answer is parsed into `model_cls`.

        On malformed JSON the request is re-sent once with the error appended.
        """
        model = model or self.settings.groq_model
        note = ""
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user + note},
            ]
            started = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    temperature=self.settings.llm_temperature,
                    max_completion_tokens=self._output_budget(messages),
                    reasoning_effort=self.settings.reasoning_effort,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except BadRequestError as exc:
                # Groq rejects generations that are not valid JSON (code json_validate_failed).
                if "json_validate_failed" not in str(exc):
                    raise
                last_error = exc
                log.warning("%s attempt %d: invalid JSON from model", model_cls.__name__, attempt)
                note = "\n\nIMPORTANT: your previous answer was not valid JSON. Return one valid JSON object."
                continue

            choice = response.choices[0]
            usage = response.usage
            log.info(
                "LLM %s via %s attempt %d: %.1fs, tokens in=%s out=%s",
                model_cls.__name__,
                model,
                attempt,
                time.perf_counter() - started,
                getattr(usage, "prompt_tokens", "?"),
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
                    note = (
                        "\n\nIMPORTANT: your previous answer was cut off by the length limit. "
                        "Think briefly and return the complete JSON object only."
                    )
                else:
                    note = f"\n\nIMPORTANT: your previous answer failed validation:\n{exc}\nReturn the corrected JSON object only."

        raise LLMError(f"Model failed to return valid {model_cls.__name__} JSON: {last_error}")

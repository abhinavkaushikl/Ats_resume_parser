"""Command-line entry point.

    python resume_tailor.py --jd flaconi_jd.txt      # one-off generation from a file
    python resume_tailor.py --serve                  # start the web UI (http://127.0.0.1:8000)
    python resume_tailor.py --show-base              # print how the base resume PDF was parsed
"""

import argparse
import logging
import sys
from pathlib import Path

from ats_tailor.base_resume import load_base
from ats_tailor.config import get_settings
from ats_tailor.documents import DocumentError, extract_jd_text
from ats_tailor.pipeline import TailoringPipeline, job_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Tailor your resume and cover letter to a job description.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--jd", type=Path, help="Job description file (.txt, .md, .pdf, .docx)")
    group.add_argument("--serve", action="store_true", help="Run the web UI")
    group.add_argument("--show-base", action="store_true", help="Print the parsed base resume and exit")
    parser.add_argument("--company", help="Company name for file names (default: detected from the JD)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.serve:
        import uvicorn

        uvicorn.run("ats_tailor.web:app", host=args.host, port=args.port)
        return 0

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    settings = get_settings()
    if args.show_base:
        print(load_base(settings.base_resume_path).as_text())
        return 0
    try:
        jd = extract_jd_text(args.jd.name, args.jd.read_bytes())
        result = TailoringPipeline(settings).run(jd, company=args.company)
    except (DocumentError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out = job_dir(settings, result.job_id)
    print(f"\n{result.company} — {result.role}")
    print(f"  Added: {result.added}")
    for name in result.files.values():
        print(f"  {out / name}")
    for warning in result.warnings:
        print(f"  WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

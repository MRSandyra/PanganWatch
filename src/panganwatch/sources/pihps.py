"""F3a: PIHPS Bank Indonesia / Panel Harga Badan Pangan (NOT USED).

This module exists to record status and give the module a CLI: a source
module may stay in the repo even when it isn't the one used, as long as it
carries no dummy/fabricated data.

PIHPS/Panel Harga is not used as a price source in this project. Three
different approaches to reach it were tried and all failed:

1. robots.txt / site status check: panelharga.badanpangan.go.id was showing a
   "Website Sedang Dalam Pemeliharaan" (under maintenance) modal that blocks
   all interaction, and has no robots.txt (Angular SPA catch-all instead).
2. Direct endpoint probing: `panelharga.badanpangan.go.id/api/harga` falls
   through to the same SPA shell (not a JSON API); the legacy
   `bi.go.id/hargapangan` panel requires an ASP.NET session with an
   anti-forgery token (`__RequestVerificationToken`), not a plain GET.
3. Public reference research (read-only, no clone): no publicly documented,
   stable JSON endpoint for PIHPS hargapangan was found; the closest public
   reference (suryast/indonesia-gov-apis) explicitly flags bi.go.id pages as
   requiring ASP.NET ViewState handling.

The actual F3a price source is HDX WFP: `panganwatch.sources.hdx_wfp`.

CLI: `uv run python -m panganwatch.sources.pihps --status`
"""

from __future__ import annotations

import argparse
import uuid

from panganwatch.governance.pipeline_runs import skip_run

SOURCE_NAME = "PIHPS"
STATUS = "not_used"
REASON = (
    "PIHPS/Panel Harga not used: 3 different approaches failed "
    "(site under maintenance, endpoint isn't a JSON API, requires an ASP.NET "
    "session with an anti-forgery token). "
    "F3a price source: HDX WFP (panganwatch.sources.hdx_wfp)."
)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m panganwatch.sources.pihps",
        description="PIHPS / Panel Harga status (not used as a price source).",
    )
    p.add_argument(
        "--status",
        action="store_true",
        help="Print status and record a 'skipped' row in governance.pipeline_runs",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    print(f"[PIHPS] status={STATUS}")
    print(f"[PIHPS] {REASON}")
    if args.status:
        run_id = str(uuid.uuid4())
        skip_run(run_id, SOURCE_NAME, REASON)
        print(f"[PIHPS] recorded skipped run_id={run_id} in governance.pipeline_runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

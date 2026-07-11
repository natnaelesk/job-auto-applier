"""Daily run orchestrator.

Each phase plugs in here as it gets built. Run everything:
    python src/main.py
or a single step:
    python src/main.py scan | extract | apply | ui | gmail
"""
import asyncio
import sys

import cv_generator
import db
import extractor
import gmail_scanner
import matcher
import notion_tracker
import telegram_watcher
from applier import agent as applier_agent
from applier.orchestrator import launch as launch_ui


def step_scan() -> None:
    print("[1/7] Scanning Telegram channel...")
    count = asyncio.run(telegram_watcher.scan_channel())
    print(f"      {count} new message(s) saved.")
    enriched = asyncio.run(telegram_watcher.resolve_source_links())
    print(f"      {enriched} message(s) enriched from source posts.")


def step_extract() -> None:
    print("[2/7] Extracting jobs from new messages...")
    processed, found = extractor.extract_pending()
    print(f"      {processed} message(s) processed, {found} new job(s) found.")


def step_match() -> None:
    print("[3/7] Matching jobs against your profile...")
    counts = matcher.match_pending()
    print(f"      {counts}")


def step_rematch() -> None:
    print("[3b] Rematching existing jobs (remote/backend preference)...")
    counts = matcher.rematch_existing()
    print(f"      {counts}")


def step_cv() -> None:
    print("[4/7] Generating tailored CVs for matched jobs...")
    n = cv_generator.generate_for_matched()
    print(f"      {n} CV(s) generated.")


def step_apply() -> None:
    print("[5/7] Opening orchestrator (Apply tab) — you drive each application...")
    launch_ui()


def step_ui() -> None:
    print("Opening orchestrator control panel...")
    launch_ui()


def step_notion() -> None:
    print("[6/7] Syncing everything to Notion...")
    created, updated = notion_tracker.sync_jobs()
    print(f"      {created} page(s) created, {updated} updated.")


def step_gmail() -> None:
    print("[7/7] Scanning Gmail for company replies...")
    counts = gmail_scanner.scan_inbox()
    print(f"      {counts}")


def summary() -> None:
    conn = db.connect()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"
    ).fetchall()
    conn.close()
    if rows:
        print("\nJob pipeline:")
        for row in rows:
            print(f"  {row['status']}: {row['n']}")


# Default daily order: prepare (1-4) + notion, then human apply UI
STEPS = {
    "scan": step_scan,
    "extract": step_extract,
    "match": step_match,
    "cv": step_cv,
    "notion": step_notion,
    "apply": step_apply,
    "gmail": step_gmail,
}

EXTRA_STEPS = {
    "rematch": step_rematch,
    "ui": step_ui,
}


def main() -> None:
    args = sys.argv[1:]
    all_steps = {**STEPS, **EXTRA_STEPS}
    if args:
        for name in args:
            if name not in all_steps:
                raise SystemExit(
                    f"Unknown step '{name}'. Available: {', '.join(all_steps)}"
                )
            all_steps[name]()
    else:
        # 1–4 prepare, sync, then orchestrator (Apply). Updates from panel or:
        #   python src/main.py gmail
        for name in ("scan", "extract", "match", "cv", "notion", "apply"):
            STEPS[name]()
    summary()


if __name__ == "__main__":
    main()

"""Minimal crash diagnostics without exception messages, source text, or locals."""

from datetime import datetime, timezone
from pathlib import Path
import traceback


def record_failure(error, directory="logs"):
    """Return a report path, or None when the diagnostic directory is unwritable."""
    lines = [f"UTC: {datetime.now(timezone.utc).isoformat()}",
             f"Exception: {type(error).__name__}"]
    for frame in traceback.extract_tb(error.__traceback__):
        lines.append(f"  {Path(frame.filename).name}:{frame.lineno} in {frame.name}")
    # Messages, source lines and locals can contain API keys or player text.
    try:
        path = Path(directory) / "crash_report.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path)
    except OSError:
        return None


def failure_message(error, report):
    location = f" Diagnostic: {report}." if report else " Could not write a diagnostic file."
    return (f"The game stopped unexpectedly ({type(error).__name__})." + location +
            " Restart and load your last save. No recovery save was written.")

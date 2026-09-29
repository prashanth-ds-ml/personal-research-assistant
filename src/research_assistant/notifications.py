"""Native Windows notification when a research run completes.

Wrapped so a notification failure (missing WinRT bits, no display session,
etc.) never fails an otherwise-successful research run.
"""

import os


def notify_run_complete(research_topic: str, report_path: str | None) -> None:
    try:
        from win11toast import notify

        notify(
            title="Research complete",
            body=research_topic,
            on_click=(lambda _: os.startfile(report_path)) if report_path else None,
        )
    except Exception as e:
        print(f"Warning: notification failed: {e}")

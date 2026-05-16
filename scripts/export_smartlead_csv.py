import argparse
from pathlib import Path

from app.integrations.sheets.fake import FakeSheetClient
from app.services.export_service import export_approved_leads_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--sheet-path", default="examples/leads_demo.csv")
    parser.add_argument("--output", default="smartlead_export.csv")
    args = parser.parse_args()

    if not args.fake:
        raise SystemExit("Phase 11 CLI supports --fake only.")

    content = export_approved_leads_csv(FakeSheetClient(args.sheet_path), platform="smartlead")
    Path(args.output).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()

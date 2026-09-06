"""Run the GUI, or export directly from a terminal."""
import argparse
import sys
from pathlib import Path

from .core import (ALL_COLUMNS, DEFAULT_COLUMNS, default_collection_path, extract_collection,
                   filter_rows, load_catalog, refresh_catalog, render_export, save_export)


def main():
    parser = argparse.ArgumentParser(description="Export your Marvel Snap collection locally.")
    parser.add_argument("--export", type=Path, help="Save directly to a file instead of opening the app")
    parser.add_argument("--collection", type=Path, help="Override the collection path (also works with the GUI)")
    parser.add_argument("--format", choices=("csv", "tsv", "json", "prompt"), default="csv")
    parser.add_argument("--refresh", action="store_true", help="Download fresh public card data")
    parser.add_argument("--columns", default=",".join(DEFAULT_COLUMNS), help="Comma-separated: " + ",".join(ALL_COLUMNS))
    parser.add_argument("--search", default="")
    parser.add_argument("--cost", choices=("Any", "0", "1", "2", "3", "4", "5", "6+"), default="Any")
    parser.add_argument("--request", default="", help="Custom instructions for a prompt export")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing export file")
    args = parser.parse_args()
    if args.export is None:
        if (args.refresh or args.format != "csv" or args.columns != ",".join(DEFAULT_COLUMNS)
                or args.search or args.cost != "Any" or args.request or args.force):
            parser.error("Export options require --export PATH. Use --collection PATH to select a file in the GUI.")
        from .gui import main as gui_main
        gui_main(collection_path=args.collection)
        return 0
    try:
        source = (args.collection or default_collection_path()).expanduser()
        if not source.is_file():
            raise FileNotFoundError("Collection file not found. Open SNAP once, or pass --collection PATH.")
        args.export = args.export.expanduser()
        if args.export.exists() and not args.force:
            raise FileExistsError("The export already exists. Choose a new filename or use --force to replace it.")
        columns = [c.strip() for c in args.columns.split(",")]
        if "name" not in columns or any(c not in ALL_COLUMNS for c in columns) or len(set(columns)) != len(columns):
            raise ValueError("Choose unique valid export columns, including name.")
        if args.refresh:
            catalog = refresh_catalog()
        else:
            try:
                catalog = load_catalog()
            except (OSError, ValueError, KeyError, TypeError):
                catalog = refresh_catalog()
        collection = extract_collection(source, catalog)
        rows = filter_rows(collection.rows, args.search, args.cost)
        format_name = "AI prompt" if args.format == "prompt" else args.format.upper()
        output = render_export(rows, columns, format_name,
                               catalog, collection, args.request, bool(args.search or args.cost != "Any"))
        save_export(args.export, output, format_name, source)
        print(f"Saved {len(rows)} unique cards to {args.export} ({collection.duplicates} duplicate copies removed).")
        if collection.missing:
            print("Warning: UNKNOWN metadata for " + ", ".join(collection.missing), file=sys.stderr)
        if collection.ignored:
            print(f"Warning: skipped {collection.ignored} entries without a card ID.", file=sys.stderr)
        return 0
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# Snap Extract

A small Windows desktop app that turns your local Marvel Snap collection into a clean export for AI deck building. No account, API key, browser server, or subscription is needed.

[![Tests and Windows build](https://github.com/switchfire6/snap-extract/actions/workflows/ci.yml/badge.svg)](https://github.com/switchfire6/snap-extract/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Windows · Python 3.10+ · No third-party runtime dependencies**

## Features

- One row per owned card, including cards owned only as variants.
- Names, energy costs, power, and clean ability text; optional series, keywords, and IDs.
- CSV, TSV, JSON, and a ready-to-paste AI deck-building prompt.
- Search, cost filters, sorting, column selection, and an exact export preview.
- Cached public metadata for offline extraction after the first download.
- Read-only access to your game files; no collection uploads or analytics.

## Start

### Run from source

Install Python 3.10 or newer with Tcl/Tk enabled (included by default in the python.org Windows installer), then:

```powershell
git clone https://github.com/switchfire6/snap-extract.git
cd snap-extract
python run_app.py
```

No `pip install` is required to run from the source folder. Optionally install with `python -m pip install .` to get the `snap-extract` and `snap-extract-gui` commands.

### Run a Windows build

Download a Windows ZIP from [Releases](https://github.com/switchfire6/snap-extract/releases), when one is available. Development builds are available as artifacts on successful [Actions runs](https://github.com/switchfire6/snap-extract/actions/workflows/ci.yml) (GitHub sign-in required for artifact downloads).

Extract `Snap-Extract-Windows.zip` and open **Snap Extract.exe**. Python is not required for the packaged app. Binaries are not committed to the source tree. You can also build your own executable with `build.ps1`. The optional `Start Snap Extract.vbs` launcher uses a local `dist/Snap Extract.exe` if present, otherwise `pythonw.exe`; run from source directly if Windows Script Host is unavailable.

### Export your cards

1. The app loads `CollectionState.json` from your Windows profile automatically. Use **Browse** for a different file.
2. Review the collection. Optionally search card names/abilities, filter energy cost, change sorting, or choose columns. Filters apply to the export too.
3. Choose **CSV** or **AI prompt**, then **Copy export** or **Save**. The Export preview tab shows the exact text.
4. After getting new cards, open SNAP so it saves your collection, then click **Load collection**. Use **Refresh card data** after balance changes.

**CSV is the recommended general format**: compact, readable by AI tools, and easy to open in spreadsheets. **AI prompt** wraps the CSV in instructions to use only your owned cards and suggest decks. TSV supports pasting into spreadsheet columns; JSON is available for other tools. Saved CSV files use UTF-8 with a BOM for Excel compatibility; clipboard text has no BOM.

## What gets exported

Default columns: `name,cost,power,ability`. Optional columns: `series,keywords,card_id`.

Ownership comes only from `ServerState.Cards`, deduplicated by `CardDefId`. A card owned only as a variant still counts. Splits and cosmetic variants collapse into one row. Avatars, card backs, titles, currencies, boosters, account IDs, and match history are never exported. Non-owned catalog entries—including generated tokens and unreleased cards—are never added to the collection. Flavor text on cards explicitly marked “No Ability” is replaced with `No ability.`

Search can match card names, abilities, keywords, or card IDs. Cost `6+` includes cards costing more than six energy. Cards with unknown metadata are retained with their ID as the name, empty numeric fields, and a prominent `UNKNOWN` ability; the app reports how many need attention. Malformed ownership entries without a usable card ID are skipped and counted.

## Card data and privacy

The local collection file does **not** contain names, costs, powers, or ability text. The app fetches the public [Snap.fan card catalog](https://snap.fan/cards/) once and caches it. Refresh downloads the same complete public page; it never sends your collection, account details, file path, or owned card IDs. Collection extraction works offline after the first successful download.

The catalog retrieval date is shown in the app and included in AI prompt exports. It is **not** a guarantee that the third-party catalog reflects the latest balance update. The app recommends refreshing caches older than seven days. Local game balance patches are not mixed into third-party descriptions. A failed refresh keeps the previous cache and export available. If Snap.fan changes its page structure, the parser may need an update.

Settings and public card metadata are stored in `%LOCALAPPDATA%\SnapExtract\`. The app reads the game file without modifying it. Export dialogs and the CLI reject saves into the source state folder. Nothing is sent to an AI automatically; you choose what to paste.

The AI prompt targets standard 12-card decks. Use the optional request field for archetypes, favorite cards, or other preferences. It identifies filtered exports as a subset of your collection.

## Command line

```powershell
python -m snap_extract --export exports\my-collection.csv
python -m snap_extract --export exports\deck-prompt.txt --format prompt
python -m snap_extract --export exports\ongoing.csv --search Ongoing --refresh
python -m snap_extract --export exports\cards.json --format json --columns name,cost,power,ability,card_id
```

Use `--collection "C:\path\CollectionState.json"` for a different collection file, including when opening the GUI. Other CLI export options require `--export`. Existing export files are preserved unless you pass `--force`. The GUI's save dialog asks before replacing an existing file.

The first run downloads public metadata if there is no valid cache. `--refresh` explicitly updates it. `python -m snap_extract --help` lists options.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check snap_extract tests run_app.py tools
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The tests are offline and use fictional ownership data. CI runs on Windows with Python 3.10 and 3.13. GUI tests need a graphical session. The CLI can process a copied collection on other systems with Python, but the desktop app and game-path discovery are supported on Windows.

The build script creates `.build-venv` and uses PyInstaller 6.22.2 to produce a Windows executable plus `dist/Snap-Extract-Windows.zip` and SHA-256 checksums. The ZIP includes application and third-party license notices. Game data and personal collection files are not bundled.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow, [SECURITY.md](SECURITY.md) for private reporting, and [CHANGELOG.md](CHANGELOG.md) for changes.

## Troubleshooting

- **Collection file not found:** launch the Steam version of SNAP once and open your collection, then use Browse if your state file is stored elsewhere.
- **First download or refresh fails:** check your connection. The previous cache remains available after a failed refresh; the first use requires a successful catalog download. Snap.fan's availability and page format may change.
- **Missing or stale stats:** refresh card data. Unknown cards remain visible and are flagged instead of being silently dropped. Check important balance changes in-game.
- **ImportError for Tkinter:** install Tcl/Tk through the Python installer, or use the packaged Windows build.
- **Small display:** resize the window and scroll the options panel. Select a card to read the complete ability below the table.

## License

Application source is available under the [MIT license](LICENSE). That license does not apply to Marvel Snap game content or Snap.fan's catalog. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This is an unofficial personal utility, unaffiliated with Marvel, Second Dinner, or Snap.fan. Card names and game text belong to their respective owners.

# Snap Extract

<img src="assets/app.png" alt="Snap Extract icon" width="80" align="right">

A small Windows desktop app that turns your local Marvel Snap collection into a clean export for AI deck building. No account, API key, browser server, or subscription is needed.

[![Tests and Windows build](https://github.com/switchfire6/snap-extract/actions/workflows/ci.yml/badge.svg)](https://github.com/switchfire6/snap-extract/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Windows 10/11 · No Python installation needed for the installer**

## Install in three steps

1. [Download the Windows installer](https://github.com/switchfire6/snap-extract/releases/download/v1.1.0/Snap-Extract-1.1.0-Setup.exe).
2. Double-click **Snap-Extract-1.1.0-Setup.exe** and follow the setup steps. Select **Create a desktop shortcut** if you want one.
3. Open **Snap Extract** from the Start menu or desktop shortcut.

No administrator access or Python installation is needed. Requires Windows 10/11 with an x64-compatible processor. The app is unsigned, so Windows may show an unknown-publisher or SmartScreen warning; only run downloads you trust.

**First use:** open Marvel Snap and view your collection once, then launch Snap Extract. It finds your local collection automatically and downloads public card details. Choose **Copy export** or **Save CSV** to export your cards; choose **Saved decks…** to export decks. Internet is needed for the first card-data download.

Prefer no installer? [Download the portable ZIP](https://github.com/switchfire6/snap-extract/releases/download/v1.1.0/Snap-Extract-1.1.0-Windows-x64.zip), extract the entire folder, and open **Snap Extract.exe**. Keep `_internal` beside the executable.

[All releases and checksums](https://github.com/switchfire6/snap-extract/releases/latest)

## Features

- One row per owned card, including cards owned only as variants.
- Names, energy costs, power, and clean ability text; optional series, keywords, and IDs.
- CSV, TSV, JSON, and a ready-to-paste AI deck-building prompt.
- Select saved decks individually or all at once, then copy or save their names and card lists.
- Windows installer with Start menu launcher, optional desktop shortcut, and uninstaller.
- Search, cost filters, sorting, column selection, and an exact export preview.
- Cached public metadata for offline extraction after the first download.
- Read-only access to your game files; no collection uploads or analytics.

## Other setup options

### Update or uninstall

The app installs for your Windows account into `%LOCALAPPDATA%\Programs\Snap Extract`. Install a newer version in the same location to upgrade. Uninstall through **Settings → Apps → Installed apps**; your exports, preferences, and cached card data are preserved. To reset preferences and cache, remove `%LOCALAPPDATA%\SnapExtract` after closing the app.

For download verification, `SHA256SUMS.txt` accompanies the installer and portable ZIP. Compare a download using `Get-FileHash .\Snap-Extract-1.1.0-Setup.exe -Algorithm SHA256`. A matching checksum detects a changed download but does not replace publisher signing.

Development builds are available on successful [Actions runs](https://github.com/switchfire6/snap-extract/actions/workflows/ci.yml) (GitHub sign-in required). Download and extract the artifact, then run its installer.

### Run from source

If you already have the project folder and Python installed, double-click **Start Snap Extract.cmd**. It opens `dist/Snap Extract/Snap Extract.exe` when available, otherwise uses the local `.venv` or installed Python. To run current source code while developing, use the command below.

Install Python 3.10 or newer with Tcl/Tk enabled (included by default in the python.org Windows installer), then:

```powershell
git clone https://github.com/switchfire6/snap-extract.git
cd snap-extract
python run_app.py
```

No `pip install` is required to run from the source folder. Optionally install with `python -m pip install .` to get the `snap-extract` and `snap-extract-gui` commands.

### Portable Windows build

Extract **Snap-Extract-1.1.0-Windows-x64.zip** into a permanent folder and double-click **Snap Extract.exe**. Keep the `_internal` folder beside the executable; it contains the bundled runtime. Python is not required. Double-click **Create Desktop Shortcut.vbs** once for an optional shortcut, or right-click the executable and use **Send to → Desktop (create shortcut)**. Portable refers to installation: preferences and cache still use `%LOCALAPPDATA%\SnapExtract`.

Binaries are not committed to the source tree. You can also build your own executable with `build.ps1`. **Start Snap Extract.cmd** works from both the source folder and the extracted Windows ZIP. The optional `.vbs` launcher opens the executable or local `.venv` without a console window, falling back to the `.cmd` launcher for other Python installations.

### Export your cards

1. The app loads `CollectionState.json` from your Windows profile automatically. Use **Browse** for a different file.
2. Review the collection. Optionally search card names/abilities, filter energy cost, change sorting, or choose columns. Filters apply to the export too.
3. Choose **CSV** or **AI prompt**, then **Copy export** or **Save**. The Export preview tab shows the exact text.
4. After getting new cards, open SNAP so it saves your collection, then click **Load collection**. Use **Refresh card data** after balance changes.

**CSV is the recommended general format**: compact, readable by AI tools, and easy to open in spreadsheets. **AI prompt** wraps the CSV in instructions to use only your owned cards and suggest decks. TSV supports pasting into spreadsheet columns; JSON is available for other tools. Saved CSV files use UTF-8 with a BOM for Excel compatibility; clipboard text has no BOM.

## What gets exported

### Export your saved decks

1. Load your collection, then click **Saved decks…** next to **Load collection**.
2. Click the checkboxes or deck rows to include or exclude decks. Use **Select all** or **Clear selection** for a fresh selection. With keyboard focus on the list, use the arrow keys and **Space** to toggle a deck.
3. Choose **Text**, **CSV**, **TSV**, or **JSON**. The preview shows exactly what will be copied or saved.
4. Click **Copy selected** or **Save selected…**. All selected decks go into one export; unselected decks are excluded.

Text includes each deck's name and its cards' costs, powers, and abilities, ready to share or paste into an AI. CSV and TSV include `deck_number` and `deck_name` before the card columns so decks with the same name stay distinct. JSON stores a list of named decks with their card details. These are readable/data exports, not in-game import codes.

Decks are read from `ServerState.Decks` in the loaded `CollectionState.json`. The export preserves saved card order and empty decks; collection search and cost filters do not remove cards from decks. Missing metadata is marked `UNKNOWN`. Unreadable decks are skipped with a visible warning rather than exporting a partial card list. If no decks appear, save a deck in SNAP and reload the collection. Account IDs, card instance IDs, and cosmetics are excluded.

### Collection columns

Default columns: `name,cost,power,ability`. Optional columns: `series,keywords,card_id`.

Ownership comes only from `ServerState.Cards`, deduplicated by `CardDefId`. A card owned only as a variant still counts. Splits and cosmetic variants collapse into one row. Avatars, card backs, titles, currencies, boosters, account IDs, and match history are never exported. Non-owned catalog entries—including generated tokens and unreleased cards—are never added to the collection. Flavor text on cards explicitly marked “No Ability” is replaced with `No ability.`

Search can match card names, abilities, keywords, or card IDs. Cost `6+` includes cards costing more than six energy. Cards with unknown metadata are retained with their ID as the name, empty numeric fields, and a prominent `UNKNOWN` ability; the app reports how many need attention. Malformed ownership entries without a usable card ID are skipped and counted.

## Card data and privacy

The local collection file does **not** contain names, costs, powers, or ability text. The app fetches the public [Snap.fan card catalog](https://snap.fan/cards/) once and caches it. Refresh downloads the same complete public page; it never sends your collection, account details, file path, or owned card IDs. Collection extraction works offline after the first successful download.

The catalog retrieval date is shown in the app and included in AI prompt exports. It is **not** a guarantee that the third-party catalog reflects the latest balance update. The app recommends refreshing caches older than seven days. Local game balance patches are not mixed into third-party descriptions. A failed refresh keeps the previous cache and export available. If Snap.fan changes its page structure, the parser may need an update.

Settings and public card metadata are stored in `%LOCALAPPDATA%\SnapExtract\`. The app reads the game file without modifying it. Export dialogs and the CLI reject saves into both the source state folder and the default game state folder, including when reading a copied collection. Nothing is sent to an AI automatically; you choose what to paste.

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
python -m pip_audit -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The application tests are offline and use fictional ownership data. CI runs on Windows with Python 3.10, 3.13, and 3.14; the dependency audit needs network access. GUI tests need a graphical session. The CLI can process a copied collection on other systems with Python, but the desktop app and game-path discovery are supported on Windows.

Build using a current **64-bit Python 3.13+** installation with Tcl/Tk; pass `-Python C:\path\python.exe` if needed. `build.ps1` creates `.build-venv`, installs the pinned PyInstaller from `requirements-build.txt`, and downloads a pinned Inno Setup compiler into `build/tools` after verifying its SHA-256 and publisher signature. Use `-IsccPath C:\path\ISCC.exe` for an existing compiler, or `-PortableOnly` to skip the installer.

Outputs in `dist/` are the versioned installer, portable ZIP, and `SHA256SUMS.txt`. Both distributions include application and third-party licenses. The installed app launches directly from its bundled runtime without extracting a temporary copy on each launch. Game data and personal collection files are not bundled. CI also tests portable launch, installation, upgrade, shortcut targets, and uninstall using fictional data.

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

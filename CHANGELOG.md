# Changelog

## 1.1.0

- Per-user Windows installer with Start menu launcher, optional desktop shortcut, upgrade support, and uninstaller that preserves user data.
- Versioned portable ZIP, complete license notices, original app icon, executable version metadata, and checksums for both downloads.
- Faster packaged startup using a folder bundle; export format changes preserve table selection and scroll position.
- Hardened CSV/TSV quoting and formula handling, same-origin HTTPS redirects, and stricter catalog validation.
- Atomic CLI no-overwrite saves and protection for the default game state folder when reading a copied collection.
- Single-source app version, dependency audits, weekly CI, and install/upgrade/uninstall smoke tests.
- Double-click launcher with executable, local virtual environment, and Python fallback.
- Optional desktop shortcut helper, also included in the Windows ZIP.
- Saved-deck selection with checkboxes, select all, clear selection, and an exact export preview.
- Copy or save selected decks as readable text, CSV, TSV, or JSON, including names and card details.
- Saved-deck parsing keeps card order, handles instance references, and reports unreadable decks without blocking collection exports.

## 1.0.0

- Native Windows collection preview with search, energy-cost filtering, and selectable columns.
- Deduplication by card ID; variants and splits count as one owned card.
- CSV, TSV, JSON, and AI prompt exports, with clipboard and file actions.
- Cached public metadata with explicit refresh and missing-card reporting.
- Local-only ownership processing and protection against overwriting game state.
- CLI validation and explicit `--force` for replacing existing export files.
- Offline regression tests and Windows CI builds.

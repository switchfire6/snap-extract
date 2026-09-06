# Contributing

Bug reports and focused pull requests are welcome. Be respectful, describe the problem clearly, and keep discussion about the work.

## Local setup

Use Windows with Python 3.10 or newer, including Tcl/Tk. The application has no third-party runtime dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m ruff check snap_extract tests run_app.py tools
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_app.py
```

The tests use synthetic collections and mocked catalog downloads. They must not read a contributor's real game files, contact Snap.fan, or require GitHub credentials. GUI tests need a graphical session; run only `test_core.py` and `test_cli.py` when working without a display.

## Pull requests

- Explain the user-visible issue and resulting behavior.
- Add a regression test for data handling or behavior changes. Keep fixtures fictional and minimal.
- Run lint and the tests. For UI changes, also verify normal and minimum window sizes on Windows.
- For parser changes, verify a public catalog refresh locally without committing the downloaded catalog.
- Keep collection processing local. Do not introduce uploads, analytics, or account authentication as a side effect of exporting.
- Never attach real `CollectionState.json`, settings, exports, credentials, or screenshots containing personal paths to a public issue or PR.

## Project layout

- `snap_extract/core.py`: ownership parsing, catalog cache, filtering, and serialization.
- `snap_extract/gui.py`: native Tkinter interface and background loading.
- `snap_extract/__main__.py`: CLI and GUI entry point.
- `tests/`: offline regression tests.
- `build.ps1`: isolated Windows executable build and distributable ZIP.
- `tools/`: build support scripts.

## Releases

Update both `pyproject.toml` and `snap_extract/__init__.py`, document the changes in `CHANGELOG.md`, then run `build.ps1`. The Windows CI build also produces a downloadable artifact. Distribute the ZIP, which includes license notices, rather than just the executable. Publishing a release is a maintainer action; pushes do not automatically create releases.

By contributing, you agree that your original contribution is provided under the repository's MIT license. Game content and third-party components keep their own licensing terms.

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
.\.venv\Scripts\python.exe -m pip_audit -r requirements-dev.txt
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
- `build.ps1`: isolated Windows executable, portable ZIP, and installer build.
- `installer/`: per-user Inno Setup installer with shortcuts and uninstall support.
- `assets/`: original app icon; regenerate with `tools/New-AppIcon.ps1`.
- `tools/`: build support scripts.

## Releases

1. Update the version in `snap_extract/__init__.py` (the package and Windows version resources use this single value), the download filenames in `README.md`, and `CHANGELOG.md`.
2. Run lint, offline tests, and `python -m pip_audit -r requirements-dev.txt`.
3. Run `build.ps1` using current 64-bit Python 3.13+ with Tcl/Tk. The compiler bootstrap verifies a pinned Inno Setup download's checksum and publisher signature. Review the upstream release and checksum when updating that pin.
4. Run `tools/Test-WindowsDistribution.ps1` in a clean Windows account. This installs, upgrades, launches, and uninstalls the app, including Start menu and desktop shortcuts. It refuses to touch an existing Snap Extract install or shortcut. Use `-PortableOnly` on your normal account if necessary. Test fixtures and logs stay under ignored `build/smoke/`.
5. Inspect the installer visually and check normal and minimum app window sizes. Confirm that `dist/SHA256SUMS.txt` matches the versioned installer and portable ZIP. If signing binaries, sign the app before packaging and the installer after compilation, then regenerate checksums with `python tools/package_distribution.py --checksums --installer`.
6. Attach the installer, portable ZIP, and checksums from the same successful build to a GitHub release. Distribute complete bundles with license notices, never the executable alone.

CI performs the same Windows build and installer smoke test and uploads all three release assets. Weekly CI runs check dependency advisories even when source has not changed. Publishing a release is a maintainer action; pushes do not automatically create releases. Current builds are unsigned; do not describe checksums as proof of publisher identity.

By contributing, you agree that your original contribution is provided under the repository's MIT license. Game content and third-party components keep their own licensing terms.

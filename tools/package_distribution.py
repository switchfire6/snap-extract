"""Package the Windows executable with notices from the actual build environment."""
import argparse
import hashlib
import importlib.metadata
import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from snap_extract import __version__  # noqa: E402


def third_party_licenses(root: Path) -> str:
    base = Path(sys.base_prefix)
    python_license = base / "LICENSE.txt"
    tk_licenses = list((base / "tcl").glob("tk*/license.terms"))
    if not python_license.is_file() or not tk_licenses:
        raise FileNotFoundError("Cannot locate the build's Python and Tk licenses; distribution was not created.")
    licenses = [
        ("Python and bundled components", python_license),
        ("Tcl 8.6", root / "third_party/Tcl-LICENSE.txt"),
        ("Tk", tk_licenses[0]),
    ]
    distribution = importlib.metadata.distribution("pyinstaller")
    bootloader = next((distribution.locate_file(p) for p in distribution.files or []
                       if str(p).endswith("COPYING.txt")), None)
    if bootloader is None:
        raise FileNotFoundError("Cannot locate PyInstaller's license; distribution was not created.")
    licenses.append(("PyInstaller and bootloader exception", bootloader))
    return "\n\n".join(f"{'=' * 72}\n{title}\n{'=' * 72}\n{path.read_text(encoding='utf-8')}"
                            for title, path in licenses)


def package(root: Path = ROOT) -> Path:
    destination = root / "dist"
    application = destination / "Snap Extract"
    if not (application / "Snap Extract.exe").is_file() or not (application / "_internal").is_dir():
        raise FileNotFoundError("Build dist/Snap Extract with PyInstaller before packaging.")
    content = third_party_licenses(root)
    for name in ("LICENSE", "README.md", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md",
                 "Start Snap Extract.cmd", "Start Snap Extract.vbs", "Create Desktop Shortcut.vbs"):
        shutil.copyfile(root / name, application / name)
    (application / "assets").mkdir(exist_ok=True)
    shutil.copyfile(root / "assets/app.png", application / "assets/app.png")
    (application / "THIRD_PARTY_LICENSES.txt").write_text(content, encoding="utf-8")
    archive = destination / f"Snap-Extract-{__version__}-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(application.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(application))
    return archive


def write_checksums(destination: Path, *, installer: bool = False) -> None:
    files = [destination / f"Snap-Extract-{__version__}-Windows-x64.zip"]
    if installer:
        files.append(destination / f"Snap-Extract-{__version__}-Setup.exe")
    checksums = ""
    for path in files:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        checksums += f"{digest.hexdigest()}  {path.name}\n"
    (destination / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checksums", action="store_true")
    parser.add_argument("--installer", action="store_true")
    args = parser.parse_args()
    if args.checksums:
        write_checksums(ROOT / "dist", installer=args.installer)
        print("Created SHA256SUMS.txt.")
    else:
        print(f"Created {package().name} with third-party licenses.")


if __name__ == "__main__":
    main()

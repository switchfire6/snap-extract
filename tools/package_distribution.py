"""Package the Windows executable with notices from the actual build environment."""
import hashlib
import importlib.metadata
import sys
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / "dist"
    executable = destination / "Snap Extract.exe"
    if not executable.is_file():
        raise FileNotFoundError("Build dist/Snap Extract.exe before packaging.")
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
    content = "\n\n".join(f"{'=' * 72}\n{title}\n{'=' * 72}\n{path.read_text(encoding='utf-8')}"
                            for title, path in licenses)
    archive = destination / "Snap-Extract-Windows.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(executable, executable.name)
        for name in ("LICENSE", "README.md", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md"):
            bundle.write(root / name, name)
        bundle.writestr("THIRD_PARTY_LICENSES.txt", content)
    checksums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                        for p in (archive, executable))
    (destination / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    print(f"Created {archive.name} with third-party licenses and SHA256SUMS.txt.")


if __name__ == "__main__":
    main()

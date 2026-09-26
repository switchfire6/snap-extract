"""Generate executable version metadata from the application's single version."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from snap_extract import __version__  # noqa: E402


def main():
    version = tuple(int(part) for part in __version__.split('.')) + (0,)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'switchfire6'),
    StringStruct('FileDescription', 'Snap Extract'),
    StringStruct('FileVersion', '{__version__}'),
    StringStruct('InternalName', 'Snap Extract'),
    StringStruct('OriginalFilename', 'Snap Extract.exe'),
    StringStruct('ProductName', 'Snap Extract'),
    StringStruct('ProductVersion', '{__version__}')
  ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])
"""
    destination = ROOT / "build/version-info.txt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()

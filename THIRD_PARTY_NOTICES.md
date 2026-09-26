# Third-party notices

## Application source

The MIT license in `LICENSE` covers this project's original source and documentation. It does not grant rights to third-party game content, artwork, trademarks, or external databases.

## Marvel Snap and Snap.fan

Marvel Snap names, game text, and trademarks belong to their respective owners. This project is unofficial and is not affiliated with Marvel, Second Dinner, or Snap.fan.

Card metadata is retrieved at runtime from <https://snap.fan/cards/>. No scraped card database, artwork, or real player collection is included in the source repository or application distribution. Access to external services is subject to their own terms and availability. The software license does not relicense content obtained from them.

## Windows distribution

The packaged app includes Python and Tcl/Tk and is built with PyInstaller. These components retain their original licenses:

- Python: Python Software Foundation License and bundled third-party notices, <https://docs.python.org/3/license.html>.
- Tcl/Tk: Tcl/Tk licenses, <https://www.tcl-lang.org/software/tcltk/license.html>.
- PyInstaller bootloader: GPL with a bootloader exception, <https://pyinstaller.org/en/stable/license.html>.

The build collects the installed components' license files into `THIRD_PARTY_LICENSES.txt` in both the installer and portable ZIP. This file is generated for the actual build environment. PyInstaller's build dependencies are development tools, not application imports. The installer is created with [Inno Setup](https://jrsoftware.org/isinfo.php), whose [license](https://jrsoftware.org/files/is/license.txt) permits distributing generated installations.

The Tcl 8.6 notice is also preserved in `third_party/Tcl-LICENSE.txt`, obtained from the [Tcl project's 8.6 source branch](https://github.com/tcltk/tcl/blob/core-8-6-branch/license.terms). The Windows build currently targets Python installations with Tcl/Tk 8.6.

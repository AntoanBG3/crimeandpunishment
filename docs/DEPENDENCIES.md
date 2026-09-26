# Reproducible dependencies and builds

Install runtime dependencies with `python -m pip install -r requirements.txt`.
For development, also install `-r requirements-dev.txt`; for standalone executables,
install `-r requirements-build.txt` and run `python scripts/build_release.py`.
The build also writes `dist/<name>-THIRD_PARTY_NOTICES.txt` from the executable's
own archive: every bundled Python distribution with its license files, CPython's
license, and each native library's license from `licenses/`. An unrecognised
native library fails the build; add its license text to `licenses/` and
`NATIVE_LIBRARIES` in `scripts/third_party_notices.py`. `readline` and `curses`
are excluded from builds so GPL readline and ncurses are not bundled.

All three files use `constraints.txt`, which pins the complete resolved dependency
graph, including Python 3.10 and OS-specific packages. The direct version choices
live in `requirements.in`. Update those choices deliberately, then regenerate with:

```sh
uv pip compile --universal --python-version 3.10 --no-annotate --no-header \
  requirements.in -o constraints.txt
```

The initial lock was generated with uv 0.11.8. Installing the lock uses ordinary pip;
uv is only needed to regenerate it. Version constraints reproduce package versions,
not byte-identical native binaries or release signing. Review dependency updates and
run the matrix before shipping them.

`Audit validation` runs offline tests, actual-SDK mocked-transport contracts, branch
coverage, scripted endings and engine/TUI soaks on Python 3.10 and 3.13 across the
three operating systems. Python 3.13 frozen builds then run from a temporary path
containing spaces and Unicode. Coverage and soak metrics are retained as artifacts.
These checks run on pull requests and development pushes independently of the
tag-triggered `Release` workflow; they do not publish a release.

Builds and release rehearsals use the same Python build script. Frozen console
smokes exercise startup, character selection, look, quit, and EOF with a deadline.
Headless Textual checks exercise the source app; they do not establish compatibility
with every terminal emulator or a visually inspected frozen TUI.

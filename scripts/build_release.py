"""Build the same bundled application locally and on every release platform."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

from third_party_notices import write_notices

# Only optional imports in bundled libraries reach these; the game uses neither.
# Bundling readline would ship GPL libreadline and ncurses on Linux and macOS.
EXCLUDED_MODULES = ('readline', 'curses', '_curses')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='crimeandpunishment')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    excludes = [arg for module in EXCLUDED_MODULES for arg in ('--exclude-module', module)]
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
        '--name', args.name, '--collect-all', 'textual',
        '--collect-submodules', 'google.genai', '--hidden-import', 'google.genai',
        '--copy-metadata', 'google-genai', '--add-data', f'data{os.pathsep}data',
        *excludes, 'main.py',
    ], cwd=root, check=True)
    binary = root / 'dist' / (args.name + ('.exe' if sys.platform == 'win32' else ''))
    write_notices(binary, root / 'dist' / f'{args.name}-THIRD_PARTY_NOTICES.txt')


if __name__ == '__main__':
    main()

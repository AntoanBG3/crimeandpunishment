"""Build the same bundled application locally and on every release platform."""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='crimeandpunishment')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
        '--name', args.name, '--collect-all', 'textual',
        '--collect-submodules', 'google.genai', '--hidden-import', 'google.genai',
        '--copy-metadata', 'google-genai', '--add-data', f'data{os.pathsep}data', 'main.py',
    ], cwd=root, check=True)


if __name__ == '__main__':
    main()

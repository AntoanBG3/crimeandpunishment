"""Write the third-party notices for a frozen PyInstaller executable.

The notices are derived from the executable's own archive, so they list exactly
what was bundled: every Python distribution with its license files, the CPython
license with its incorporated software, and every native library. A bundled
component without a known license text fails the build instead of shipping an
executable without its notices.
"""

import argparse
from importlib import metadata
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LICENSES = ROOT / 'licenses'

# Native libraries outside Python packages: (file name pattern, component, license
# file in licenses/). None means CPython's license document already covers it.
NATIVE_LIBRARIES = (
    (r'^(lib)?python3', 'Python', None),
    (r'^lib(ssl|crypto)', 'OpenSSL', None),
    (r'^libffi', 'libffi', None),
    (r'^libz\.', 'zlib', None),
    (r'^libbz2', 'bzip2', 'bzip2.txt'),
    (r'^liblzma', 'liblzma (XZ Utils)', 'xz-liblzma.txt'),
    (r'^libuuid', 'libuuid (util-linux)', 'libuuid.txt'),
    (r'^lib(gcc_s|objc)', 'GCC runtime library (GPL-3.0-or-later, see LICENSE, '
     'with the GCC Runtime Library Exception)', 'gcc-runtime-exception.txt'),
    (r'^(vcruntime140|ucrtbase|api-ms-win-)', 'Microsoft C runtime',
     'microsoft-runtime.txt'),
)

_NATIVE_FILE = re.compile(r'\.(dylib|dll)$|\.so(\.\d+)*$', re.IGNORECASE)
_EXTENSION_MODULE = re.compile(r'cpython-|abi3|\.pyd$|lib-dynload', re.IGNORECASE)
_EXTENSION_FILE = re.compile(r'\.(so|pyd)$', re.IGNORECASE)
_LICENSE_FILE = re.compile(r'licen[cs]e|copying|notice|authors', re.IGNORECASE)


def archive_contents(binary):
    """(module names, archive entry names) of a PyInstaller onefile executable."""
    from PyInstaller.archive.readers import CArchiveReader  # pylint: disable=import-outside-toplevel

    archive = CArchiveReader(str(binary))
    entries = list(archive.toc)
    modules = set(archive.open_embedded_archive('PYZ.pyz').toc)
    for entry in entries:
        path = entry.replace('\\', '/')
        if _EXTENSION_FILE.search(path) and 'lib-dynload/' not in path:
            directory, _, name = path.rpartition('/')
            modules.add('.'.join(filter(None, directory.split('/') + [name.split('.')[0]])))
    return modules, entries


def _module_name(path):
    path = str(path).replace('\\', '/')
    if path.startswith('..'):
        return None
    if path.endswith('.py'):
        name = path[:-3]
    elif _EXTENSION_FILE.search(path):
        directory, _, base = path.rpartition('/')
        name = f'{directory}/{base.split(".")[0]}' if directory else base.split('.')[0]
    else:
        return None
    name = name.replace('/', '.')
    return name[:-len('.__init__')] if name.endswith('.__init__') else name


def bundled_distributions(modules, distributions=None):
    """Installed distributions that provided any of the bundled modules."""
    owners = {}
    for dist in distributions if distributions is not None else metadata.distributions():
        for path in dist.files or ():
            name = _module_name(path)
            if name:
                owners.setdefault(name, dist)
    found = {}
    for module in modules:
        dist = owners.get(module)
        if dist is not None:
            found.setdefault(dist.metadata['Name'].lower(), dist)
    return [found[key] for key in sorted(found)]


def native_libraries(entries):
    """(file name, component, license file) for every bundled native library."""
    libraries, unknown = [], []
    for entry in entries:
        name = entry.replace('\\', '/').rpartition('/')[2]
        if not _NATIVE_FILE.search(name) or _EXTENSION_MODULE.search(entry):
            continue
        for pattern, component, license_file in NATIVE_LIBRARIES:
            if re.search(pattern, name, re.IGNORECASE):
                libraries.append((name, component, license_file))
                break
        else:
            unknown.append(name)
    if unknown:
        raise ValueError('No license notice is known for bundled native libraries: '
                         + ', '.join(sorted(unknown))
                         + '. Add their license text to licenses/ and NATIVE_LIBRARIES.')
    return sorted(set(libraries))


def license_texts(dist):
    """(relative path, text) for each license-like file a distribution installed."""
    texts = []
    for path in dist.files or ():
        if _LICENSE_FILE.search(path.name) and path.suffix.lower() in ('', '.txt', '.md', '.rst'):
            text = Path(dist.locate_file(path)).read_text(encoding='utf-8', errors='replace')
            texts.append((str(path), text))
    if not texts:
        raise ValueError(f'{dist.metadata["Name"]} {dist.version} installed no license file.')
    return texts


def _license_summary(dist):
    expression = dist.metadata.get('License-Expression')
    if expression:
        return expression
    classifiers = [c.split('::')[-1].strip() for c in dist.metadata.get_all('Classifier') or ()
                   if c.startswith('License ::')]
    if classifiers:
        return '; '.join(classifiers)
    return (dist.metadata.get('License') or 'see license text').splitlines()[0][:80]


def _section(title, body):
    return f'{"=" * 78}\n{title}\n{"=" * 78}\n\n{body.strip()}\n\n'


def render(executable_name, version, distributions, libraries):
    lines = [
        f'Third-party notices for Crime and Punishment {version} ({executable_name})',
        '',
        'Crime and Punishment is free software under the GNU General Public License,',
        'version 3 or later; see LICENSE. This executable also contains the',
        'components below, each distributed under its own license.',
        '',
        'Python packages:',
    ]
    lines += [f'  {d.metadata["Name"]} {d.version} ({_license_summary(d)})' for d in distributions]
    lines += ['', 'Python runtime and native libraries:', '  Python (PSF License)']
    lines += [f'  {name}: {component}' for name, component, _ in libraries]
    parts = ['\n'.join(lines) + '\n\n']
    parts.append(_section('Python, and software incorporated in it (OpenSSL, libffi, zlib, '
                          'expat, libmpdec and others)',
                          (LICENSES / 'python.rst').read_text(encoding='utf-8')))
    for dist in distributions:
        body = '\n\n'.join(f'--- {path} ---\n\n{text.strip()}' for path, text in license_texts(dist))
        parts.append(_section(f'{dist.metadata["Name"]} {dist.version}', body))
    for license_file in sorted({f for _, _, f in libraries if f}):
        components = sorted({c for _, c, f in libraries if f == license_file})
        parts.append(_section(', '.join(components),
                              (LICENSES / license_file).read_text(encoding='utf-8')))
    return ''.join(parts)


def game_version():
    config = (ROOT / 'game_engine' / 'game_config.py').read_text(encoding='utf-8')
    return re.search(r'^GAME_VERSION = "([^"]+)"', config, re.MULTILINE).group(1)


def write_notices(binary, output):
    modules, entries = archive_contents(binary)
    text = render(Path(binary).name, game_version(), bundled_distributions(modules),
                  native_libraries(entries))
    Path(output).write_text(text, encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('binary', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    write_notices(args.binary, args.output)


if __name__ == '__main__':
    main()

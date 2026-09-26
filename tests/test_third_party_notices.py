"""Third-party notices must cover every bundled component or fail the build."""

import email.message
from pathlib import Path, PurePosixPath
import tempfile
import unittest

from scripts import third_party_notices as notices


class FakeDistribution:
    def __init__(self, root, name, version, files, license_expression='MIT'):
        self._root = Path(root)
        self.version = version
        self.metadata = email.message.Message()
        self.metadata['Name'] = name
        self.metadata['License-Expression'] = license_expression
        self.files = [PurePosixPath(path) for path in files]

    def locate_file(self, path):
        return self._root / path


class TestThirdPartyNotices(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / 'rich-1.0.dist-info').mkdir()
        (root / 'rich-1.0.dist-info' / 'LICENSE').write_text('Rich MIT text', encoding='utf-8')
        (root / 'google_auth-2.0.dist-info').mkdir()
        (root / 'google_auth-2.0.dist-info' / 'LICENSE').write_text('Apache text', encoding='utf-8')
        self.rich = FakeDistribution(root, 'rich', '1.0', [
            'rich/__init__.py', 'rich/console.py', 'rich-1.0.dist-info/LICENSE'])
        self.auth = FakeDistribution(root, 'google-auth', '2.0', [
            'google/auth/__init__.py', 'google_auth-2.0.dist-info/LICENSE'], 'Apache-2.0')
        self.core = FakeDistribution(root, 'pydantic_core', '2.0', [
            'pydantic_core/_pydantic_core.cpython-313-darwin.so'])
        self.unused = FakeDistribution(root, 'google-other', '1.0', ['google/other/__init__.py'])

    def test_namespace_packages_resolve_to_the_owning_distribution(self):
        found = notices.bundled_distributions(
            {'rich.console', 'google.auth', 'json'},
            [self.rich, self.auth, self.unused])
        self.assertEqual([d.metadata['Name'] for d in found], ['google-auth', 'rich'])

    def test_extension_modules_resolve_to_their_distribution(self):
        found = notices.bundled_distributions({'pydantic_core._pydantic_core'}, [self.core])
        self.assertEqual(found, [self.core])

    def test_distribution_without_license_file_is_an_error(self):
        with self.assertRaisesRegex(ValueError, 'pydantic_core 2.0 installed no license file'):
            notices.license_texts(self.core)

    def test_native_libraries_are_classified_and_extensions_skipped(self):
        libraries = notices.native_libraries([
            'libssl.3.dylib', 'VCRUNTIME140.dll', 'libbz2.so.1.0', 'python313.dll',
            'lib-dynload/_ssl.cpython-313-darwin.so', 'cryptography\\_rust.pyd', 'base_library.zip'])
        self.assertEqual(libraries, [
            ('VCRUNTIME140.dll', 'Microsoft C runtime', 'microsoft-runtime.txt'),
            ('libbz2.so.1.0', 'bzip2', 'bzip2.txt'),
            ('libssl.3.dylib', 'OpenSSL', None),
            ('python313.dll', 'Python', None),
        ])

    def test_unknown_native_library_fails(self):
        with self.assertRaisesRegex(ValueError, 'libreadline.so.8'):
            notices.native_libraries(['libreadline.so.8', 'libssl.so.3'])

    def test_rendered_notices_include_every_license_text(self):
        text = notices.render('game.exe', '9.9.9', [self.auth, self.rich],
                              [('libbz2.so.1.0', 'bzip2', 'bzip2.txt')])
        self.assertIn('Crime and Punishment 9.9.9 (game.exe)', text)
        self.assertIn('google-auth 2.0 (Apache-2.0)', text)
        for expected in ('Apache text', 'Rich MIT text', 'PYTHON SOFTWARE FOUNDATION LICENSE',
                         'OpenSSL', 'Julian R Seward'):
            self.assertIn(expected, text)

    def test_every_referenced_license_file_is_vendored(self):
        for _, _, license_file in notices.NATIVE_LIBRARIES:
            if license_file:
                self.assertTrue((notices.LICENSES / license_file).is_file(), license_file)

    def test_game_version_matches_config(self):
        from game_engine.game_config import GAME_VERSION
        self.assertEqual(notices.game_version(), GAME_VERSION)


if __name__ == '__main__':
    unittest.main()

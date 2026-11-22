"""Standard-library tests. All fixtures stay inside the local test_folder."""

import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import main


class IntegrityCheckerTests(unittest.TestCase):
    def setUp(self):
        # Never edit the portfolio samples or create fixtures outside test_folder.
        self.temporary = tempfile.TemporaryDirectory(prefix="tests-", dir=main.TEST_FOLDER)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.patch = mock.patch.object(main, "TEST_FOLDER", self.folder)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.output = io.StringIO()
        self.errors = io.StringIO()
        self.stdout = contextlib.redirect_stdout(self.output)
        self.stderr = contextlib.redirect_stderr(self.errors)
        self.stdout.__enter__()
        self.stderr.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)
        self.addCleanup(self.stderr.__exit__, None, None, None)

    def sample(self, name="file1.txt", data=b"Hello integrity!\n"):
        path = self.folder / name
        path.write_bytes(data)
        return path

    def test_sha256_is_default_and_matches_known_digest(self):
        path = self.sample(data=b"abc")
        self.assertEqual(main.hash_file(path),
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(main.main([]), 0)
        self.assertIn("SHA-256 hashes", self.output.getvalue())

    def test_hashes_every_regular_file(self):
        for number in range(1, 6):
            self.sample(f"file{number}.txt", f"Sample {number}".encode())
        self.assertEqual(main.scan_files(), (5, 0))
        for path in self.folder.iterdir():
            self.assertIn(path.name, self.output.getvalue())
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), self.output.getvalue())

    def test_chunked_binary_hash(self):
        data = bytes(range(256)) * 50  # More than three 4096-byte chunks.
        self.assertEqual(main.hash_file(self.sample(data=data)), hashlib.sha256(data).hexdigest())

    def test_one_character_changes_hash(self):
        path = self.sample(data=b"Hello")
        original = main.hash_file(path)
        path.write_bytes(b"hello")
        self.assertNotEqual(original, main.hash_file(path))

    def test_two_unchanged_scans_are_identical(self):
        self.sample()
        main.scan_files()
        first = self.output.getvalue()
        self.output.seek(0)
        self.output.truncate()
        main.scan_files()
        self.assertEqual(first, self.output.getvalue())

    def test_missing_file(self):
        self.assertIsNone(main.hash_file(self.folder / "missing.txt"))
        self.assertIn("Cannot hash missing.txt", self.errors.getvalue())

    def test_permission_error(self):
        path = self.sample()
        # Portable even on Windows or when tests run as root.
        with mock.patch.object(Path, "open", side_effect=PermissionError("Access denied")):
            self.assertIsNone(main.hash_file(path))
        self.assertIn("Access denied", self.errors.getvalue())

    def test_read_error(self):
        path = self.sample()
        with mock.patch.object(Path, "open") as opened:
            opened.return_value.__enter__.return_value.read.side_effect = OSError("Read failed")
            self.assertIsNone(main.hash_file(path))
        self.assertIn("Read failed", self.errors.getvalue())

    def test_unreadable_file_does_not_stop_scan(self):
        first = self.sample("a.txt")
        self.sample("b.txt")
        real_open = Path.open

        def selective_open(path, *args, **kwargs):
            if path == first:
                raise PermissionError("Access denied")
            return real_open(path, *args, **kwargs)

        with mock.patch.object(Path, "open", selective_open):
            self.assertEqual(main.scan_files(), (1, 1))
        self.assertIn("b.txt", self.output.getvalue())

    def test_empty_folder_and_directories(self):
        (self.folder / "subfolder").mkdir()
        self.assertEqual(main.scan_files(), (0, 0))
        self.assertIn("No regular files", self.output.getvalue())
        self.assertIsNone(main.hash_file(self.folder / "subfolder"))

    def test_missing_folder(self):
        with mock.patch.object(main, "TEST_FOLDER", self.folder / "missing"):
            self.assertEqual(main.scan_files(), (0, 1))

    def test_outside_file_rejected_before_reading(self):
        self.assertIsNone(main.hash_file(Path(__file__)))
        self.assertIn("Only files inside test_folder", self.errors.getvalue())

    def test_symlinks_rejected(self):
        target = self.sample()
        link = self.folder / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Creating symbolic links is unavailable on this platform")
        self.assertIsNone(main.hash_file(link))
        self.assertEqual(main.scan_files(), (1, 0))
        with mock.patch.object(main, "TEST_FOLDER", link):
            self.assertEqual(main.scan_files(), (0, 1))

    def test_sha1(self):
        path = self.sample(data=b"abc")
        self.assertEqual(main.hash_file(path, "sha1"), hashlib.sha1(b"abc").hexdigest())
        self.assertEqual(main.main(["--algorithm", "SHA-1"]), 0)
        self.assertIn("SHA-1 hashes", self.output.getvalue())

    def test_invalid_algorithm_has_helpful_cli_error(self):
        with self.assertRaises(SystemExit) as error:
            main.main(["--algorithm", "md5"])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("Choose sha256", self.errors.getvalue())

    def test_demo_preserves_original_and_cleans_up(self):
        path = self.sample()
        original = path.read_bytes()
        self.assertTrue(main.demonstrate_integrity())
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.folder.iterdir()), [path])
        self.assertIn("CHANGED:", self.output.getvalue())
        self.assertIn("Original hash:", self.output.getvalue())

    def test_demo_is_opt_in(self):
        self.sample()
        with mock.patch.object(main, "demonstrate_integrity") as demo:
            self.assertEqual(main.main([]), 0)
            demo.assert_not_called()

    def test_demo_missing_or_empty_source(self):
        self.assertFalse(main.demonstrate_integrity())
        self.sample(data=b"")
        self.assertFalse(main.demonstrate_integrity())

    def test_readme_notice(self):
        readme = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
        self.assertIn(
            "Scanning or attacking systems you do not own or have written permission to test "
            "is illegal. This tool only monitors your own test folder.", readme,
        )


if __name__ == "__main__":
    unittest.main()

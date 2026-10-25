import tempfile
import unittest
from pathlib import Path
from safe_patch_worker import apply_patch, sha256

class SafePatchTests(unittest.TestCase):
    def test_real_atomic_patch_and_sha(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "fixture.txt"
            file.write_text("one\ntwo\nthree\n", encoding="utf-8")
            before = sha256(file.read_bytes())
            r = apply_patch(root, "fixture.txt", expected_sha256=before, old="two", new="TWO")
            self.assertEqual(r["status"], "DONE")
            self.assertEqual(file.read_text(), "one\nTWO\nthree\n")
            self.assertEqual(r["after_sha256"], sha256(file.read_bytes()))
            self.assertNotEqual(before, r["after_sha256"])
            self.assertEqual(r["production_writes"], 0)

    def test_real_python_source_patch_preserves_syntax(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "fixture.py"
            file.write_text("value = 1\n", encoding="utf-8")
            before = sha256(file.read_bytes())
            report = apply_patch(root, "fixture.py", expected_sha256=before,
                                 old="value = 1", new="value = 2")
            self.assertEqual(file.read_text(), "value = 2\n")
            self.assertNotEqual(report["before_sha256"], report["after_sha256"])

    def test_syntax_breaking_python_patch_rejected_without_write(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "fixture.py"
            file.write_text("value = 1\n", encoding="utf-8")
            before = file.read_bytes()
            with self.assertRaises(SyntaxError):
                apply_patch(root, "fixture.py", expected_sha256=sha256(before),
                            old="value = 1", new="value = (")
            self.assertEqual(file.read_bytes(), before)

    def test_stale_sha_refused(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "fixture.txt"
            file.write_text("old")
            with self.assertRaisesRegex(ValueError, "SHA precondition"):
                apply_patch(root, "fixture.txt", expected_sha256="0"*64, old="old", new="new")
            self.assertEqual(file.read_text(), "old")

    def test_ambiguous_patch_refused(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "fixture.txt"
            file.write_text("same same")
            with self.assertRaisesRegex(ValueError, "exactly once"):
                apply_patch(root, "fixture.txt", expected_sha256=sha256(file.read_bytes()), old="same", new="X")

    def test_escape_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as root:
            outside = Path(root).parent / "outside-never-write.txt"
            with self.assertRaises(ValueError):
                apply_patch(root, "../outside-never-write.txt", expected_sha256="0"*64, old="a", new="b")
            (Path(root)/"fixture.txt").symlink_to(outside)
            with self.assertRaises(ValueError):
                apply_patch(root, "fixture.txt", expected_sha256="0"*64, old="a", new="b")

    def test_symlink_scratch_root_refused_without_write(self):
        with tempfile.TemporaryDirectory() as root:
            real = Path(root) / "real"
            real.mkdir()
            target = real / "fixture.py"
            target.write_text("value = 1\n", encoding="utf-8")
            alias = Path(root) / "alias"
            alias.symlink_to(real, target_is_directory=True)
            before = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "symlink scratch root"):
                apply_patch(alias, "fixture.py", expected_sha256=sha256(before),
                            old="value = 1", new="value = 2")
            self.assertEqual(target.read_bytes(), before)

    def test_binary_or_oversize_refused(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "fixture.txt"
            file.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                apply_patch(root, "fixture.txt", expected_sha256=sha256(file.read_bytes()), old="a", new="b")
            file.write_bytes(b"a"*8193)
            with self.assertRaisesRegex(ValueError, "too large"):
                apply_patch(root, "fixture.txt", expected_sha256=sha256(file.read_bytes()), old="a", new="b")

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TimeSnapCliTests(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, "-m", "timesnap", *args],
            cwd=cwd or ROOT,
            text=True,
            capture_output=True,
        )

    def test_help_lists_snapshot_and_restore_commands(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("snapshot", result.stdout)
        self.assertIn("restore", result.stdout)
        self.assertIn(".timeSnap", result.stdout)

    def test_snapshot_writes_manifest_without_file_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "sample"
            target.mkdir()
            note = target / "note.txt"
            note.write_text("version-1", encoding="utf-8")

            result = self.run_cli("snapshot", str(target))

            self.assertEqual(result.returncode, 0, result.stderr)
            state_dir = target / ".timeSnap" / "snapshots"
            manifests = list(state_dir.glob("*/manifest.json"))
            self.assertEqual(len(manifests), 1)

            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["target_root"], str(target.resolve()))
            self.assertEqual(manifest["files"][0]["relative_path"], "note.txt")
            self.assertFalse((manifests[0].parent / "files").exists())

    def test_restore_reverts_file_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "sample"
            target.mkdir()
            note = target / "note.txt"
            note.write_text("before", encoding="utf-8")
            original_mtime = time.time() - 3600
            os.utime(note, (original_mtime, original_mtime))
            os.chmod(note, 0o640)

            snapshot_result = self.run_cli("snapshot", str(target))
            self.assertEqual(snapshot_result.returncode, 0, snapshot_result.stderr)

            snapshot_id = snapshot_result.stdout.strip().split()[-1]
            note.write_text("after", encoding="utf-8")
            changed_mtime = time.time()
            os.utime(note, (changed_mtime, changed_mtime))
            os.chmod(note, 0o600)

            restore_result = self.run_cli("restore", str(target), snapshot_id)

            self.assertEqual(restore_result.returncode, 0, restore_result.stderr)
            self.assertEqual(note.read_text(encoding="utf-8"), "after")
            restored_stats = note.stat()
            self.assertEqual(oct(restored_stats.st_mode & 0o777), "0o640")
            self.assertAlmostEqual(restored_stats.st_mtime, original_mtime, delta=2)


if __name__ == "__main__":
    unittest.main()

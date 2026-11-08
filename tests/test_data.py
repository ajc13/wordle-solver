"""Tests for data file location, legacy migration and own-solve detection.

Run with:  python3 -m unittest discover -s tests
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import wordle_solver as ws  # noqa: E402


class DataDirTests(unittest.TestCase):
    def test_list_paths_are_under_script_data_dir(self):
        script_dir = Path(ws.__file__).resolve().parent
        self.assertEqual(ws.DATA_DIR, script_dir / "data")
        self.assertEqual(ws.WORD_LIST_FILE.parent, ws.DATA_DIR)
        self.assertEqual(ws.USED_LIST_FILE.parent, ws.DATA_DIR)


class MigrateLegacyFilesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old_dir = self.root / "elsewhere"
        self.old_dir.mkdir()
        data = self.root / "data"
        for name, value in [
            ("DATA_DIR", data),
            ("WORD_LIST_FILE", data / "valid_word_list.txt"),
            ("USED_LIST_FILE", data / "used_word_list.txt"),
            ("LOG_DIR", self.root / "logs"),
        ]:
            patcher = mock.patch.object(ws, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        print_patch = mock.patch("builtins.print")
        print_patch.start()
        self.addCleanup(print_patch.stop)

    def test_moves_legacy_files_into_data(self):
        (self.old_dir / "valid_word_list.txt").write_text("arose\n")
        (self.old_dir / "used_word_list.txt").write_text("wrest\n")
        ws.migrate_legacy_data_files(self.old_dir)
        self.assertEqual(ws.WORD_LIST_FILE.read_text(), "arose\n")
        self.assertEqual(ws.USED_LIST_FILE.read_text(), "wrest\n")
        self.assertFalse((self.old_dir / "valid_word_list.txt").exists())

    def test_does_not_overwrite_existing_data(self):
        ws.DATA_DIR.mkdir()
        ws.WORD_LIST_FILE.write_text("newer\n")
        (self.old_dir / "valid_word_list.txt").write_text("older\n")
        ws.migrate_legacy_data_files(self.old_dir)
        self.assertEqual(ws.WORD_LIST_FILE.read_text(), "newer\n")
        self.assertTrue((self.old_dir / "valid_word_list.txt").exists())

    def test_nothing_to_move(self):
        ws.migrate_legacy_data_files(self.old_dir)
        self.assertFalse(ws.DATA_DIR.exists())


class OwnSolvesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.log_dir = Path(tmp.name)

    def write_log(self, rel, text):
        path = self.log_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_parses_current_and_older_formats(self):
        self.write_log(
            "2026/10/wordle_solver_2026-10-19.log",
            "[2026-10-20 08:00:00] # Session started\n"
            "[2026-10-20 08:01:00] 1,arose,?G?GY (10 left)\n"
            "[2026-10-20 08:03:00] 4,wrest,GGGGG (1 left)\n"
            "[2026-10-20 08:03:00] # Game Summary:\n"
            "[2026-10-20 08:03:00] #   4. wrest      → GGGGG (1 → 1 left, 0 cut)\n",
        )
        self.write_log("wordle_solver_2025-05-26.log", "1,arose,?????\n3,borne,GGGGG\n")
        self.assertEqual(ws.load_own_solves(self.log_dir), {"wrest", "borne"})

    def test_ignores_non_solves(self):
        self.write_log(
            "x.log",
            "[2026-10-20 08:01:00] 2,dress,?GGG? (5 left)\n"
            "[2026-10-20 08:01:00] #   1. crane      → GGGGG (9 → 1 left, 8 cut)\n"
            "not a log line wrest,GGGGG\n",
        )
        self.assertEqual(ws.load_own_solves(self.log_dir), set())

    def test_missing_log_dir(self):
        self.assertEqual(ws.load_own_solves(self.log_dir / "nope"), set())


class PastAnswerMarkTests(unittest.TestCase):
    def test_marks(self):
        used, own = {"wrest", "abide"}, {"wrest", "borne"}
        self.assertEqual(ws.past_answer_mark("wrest", used, own), ws.OWN_SOLVE_MARK)
        self.assertEqual(ws.past_answer_mark("borne", used, own), ws.OWN_SOLVE_MARK)
        self.assertEqual(ws.past_answer_mark("abide", used, own), ws.PAST_ANSWER_MARK)
        self.assertEqual(ws.past_answer_mark("crest", used, own), "")
        self.assertEqual(ws.past_answer_mark("wrest"), "")


if __name__ == "__main__":
    unittest.main()

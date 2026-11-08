"""Tests for session flow and list refresh error handling.

Run with:  python3 -m unittest discover -s tests
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import wordle_solver as ws  # noqa: E402

WORDS = {"arose", "crest", "wrest", "dress", "unity"}
FREQ = {c: 1 / 26 for c in "abcdefghijklmnopqrstuvwxyz"}


class TempLogDirMixin:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(ws, "LOG_DIR", Path(self._tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def log_text(self):
        return "".join(p.read_text() for p in Path(self._tmp.name).rglob("*.log"))


class PlayGameTests(TempLogDirMixin, unittest.TestCase):
    def play(self, inputs):
        with mock.patch("builtins.input", side_effect=inputs), mock.patch(
            "builtins.print"
        ):
            return ws.play_game(WORDS, FREQ, set())

    def test_restart_returns_restart(self):
        self.assertEqual(self.play(["r"]), "restart")

    def test_quit_returns_none(self):
        self.assertIsNone(self.play(["q"]))

    def test_no_words_remaining_logs_summary_once(self):
        # "crest/?????" eliminates every word containing c, r, e, s or t.
        self.play(["crest/?????", "q"])
        log = self.log_text()
        self.assertIn("# No words remaining", log)
        self.assertNotIn("Session ended (no words remaining)", log)
        self.assertEqual(log.count("# Game Summary:"), 1)
        self.assertIn("Session ended (user quit)", log)


class SolveRestartTests(TempLogDirMixin, unittest.TestCase):
    def test_restart_does_not_refresh_lists_again(self):
        with mock.patch.object(ws, "refresh_word_lists") as refresh, mock.patch.object(
            ws, "load_words", return_value=WORDS
        ) as load, mock.patch.object(
            ws, "play_game", side_effect=["restart", "restart", None]
        ) as play, mock.patch(
            "builtins.print"
        ), mock.patch.object(
            sys, "argv", ["wordle_solver.py"]
        ):
            ws.solve()
        self.assertEqual(refresh.call_count, 1)
        self.assertEqual(load.call_count, 1)
        self.assertEqual(play.call_count, 3)


class ScrapeFallbackTests(TempLogDirMixin, unittest.TestCase):
    def test_failed_insecure_retry_does_not_crash(self):
        target = Path(self._tmp.name) / "used.txt"
        with mock.patch.object(
            ws.requests,
            "get",
            side_effect=[
                requests.exceptions.SSLError("bad cert"),
                requests.exceptions.ConnectionError("offline"),
            ],
        ) as get, mock.patch("builtins.print"):
            ws.fetch_used_words_from_fiveforks(str(target))
        self.assertEqual(get.call_count, 2)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

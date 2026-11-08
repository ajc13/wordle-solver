"""Tests for scoring, Hard Mode checks, ranking, tables and the simulator.

Run with:  python3 -m unittest discover -s tests
"""

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import wordle_lab as lab  # noqa: E402
import wordle_solver as ws  # noqa: E402
from test_filter import reference_feedback  # noqa: E402


class ScoreGuessTests(unittest.TestCase):
    def test_known_cases(self):
        self.assertEqual(ws.score_guess("wrest", "arose"), "?G?GY")
        self.assertEqual(ws.score_guess("wrest", "dress"), "?GGG?")
        self.assertEqual(ws.score_guess("abide", "speed"), "??Y?Y")
        self.assertEqual(ws.score_guess("under", "undid"), "GGG??")

    def test_matches_reference(self):
        rng = random.Random(2)
        for _ in range(20_000):
            a = "".join(rng.choice("abcde") for _ in range(5))
            g = "".join(rng.choice("abcde") for _ in range(5))
            self.assertEqual(ws.score_guess(a, g), reference_feedback(a, g))


class HardModeTests(unittest.TestCase):
    history = [("arose", "?G?GY")]  # r green at 2, s green at 4, e yellow

    def test_legal(self):
        self.assertIsNone(ws.hard_mode_violation("dress", self.history))
        self.assertIsNone(ws.hard_mode_violation("crest", self.history))
        # Gray letters may be reused, and yellow may stay in place in NYT Hard Mode.
        self.assertIsNone(ws.hard_mode_violation("arese", self.history))

    def test_green_must_stay(self):
        self.assertEqual(
            ws.hard_mode_violation("rinse", self.history), "R must be in position 2"
        )

    def test_yellow_must_be_used(self):
        self.assertEqual(ws.hard_mode_violation("prost", self.history), "must use E")

    def test_repeated_letters_counted(self):
        history = [("eerie", "YY???")]  # two e's revealed
        self.assertEqual(ws.hard_mode_violation("teach", history), "must use E 2 times")
        self.assertIsNone(ws.hard_mode_violation("geese", history))

    def test_no_history(self):
        self.assertTrue(ws.is_hard_mode_legal("zzzzz", []))


class RankingTests(unittest.TestCase):
    def test_expected_remaining(self):
        # After crest ?GGGG: prest, trest, wrest. Guessing prest either solves
        # or shows ?GGGG for both trest and wrest, which stay together:
        # expected 2*2/3 left, worst case 2.
        expected, worst = ws.expected_remaining("prest", ["prest", "trest", "wrest"])
        self.assertAlmostEqual(expected, 4 / 3)
        self.assertEqual(worst, 2)

    def test_rank_prefers_candidates_on_tie(self):
        candidates = ["prest", "trest", "wrest"]
        ranked = ws.rank_guesses(candidates, ["crest", "prest", "trest", "wrest"])
        self.assertEqual([w for w, _, _ in ranked[:3]], ["prest", "trest", "wrest"])
        self.assertEqual(ranked[-1][0], "crest")
        self.assertFalse(ranked[-1][2])

    def test_suggest_uses_frequency_on_first_turn(self):
        words = {"arose", "crest", "wrest"}
        freq = {c: 0.1 for c in "acerostw"}
        method, ranked = ws.suggest(sorted(words), [], words, freq)
        self.assertEqual(method, "frequency")
        self.assertEqual(len(ranked), 3)

    def test_suggest_buckets_within_limit_and_stays_legal(self):
        words = {"arose", "crest", "wrest", "prest", "trest", "dress", "zzzzz"}
        history = [("arose", "?G?GY")]
        candidates = ws.filter_word_list(sorted(words), "arose", "?G?GY")
        method, ranked = ws.suggest(candidates, history, words, {}, work_limit=1000)
        self.assertEqual(method, "bucket")
        self.assertNotIn("zzzzz", [w for w, _, _ in ranked])  # breaks Hard Mode

    def test_suggest_falls_back_to_frequency_over_limit(self):
        words = {"arose", "crest", "wrest", "prest", "trest", "dress"}
        candidates = ["crest", "wrest", "prest", "trest", "dress"]
        freq = {c: 0.1 for c in "acdeoprstw"}
        method, _ = ws.suggest(candidates, [("arose", "?G?GY")], words, freq, work_limit=10)
        self.assertEqual(method, "frequency")

    def test_suggest_uses_table_on_turn_two(self):
        words = {"arose", "crest", "wrest", "prest", "trest", "dress"}
        tables = {"arose": {"?G?GY": [["crest", 2.7, True], ["notaword", 1.0, True]]}}
        candidates = ["crest", "wrest", "prest"]
        freq = {c: 0.1 for c in "acdeoprstw"}
        method, ranked = ws.suggest(candidates, [("arose", "?G?GY")], words, freq, tables)
        self.assertEqual(method, "table")
        self.assertEqual(ranked[0], ("crest", 2.7, True))
        self.assertNotIn("notaword", [w for w, _, _ in ranked])
        self.assertEqual({w for w, _, _ in ranked}, {"crest", "wrest", "prest"})


class TableLoadingTests(unittest.TestCase):
    def test_loads_and_skips_bad_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "second_guess_arose.json").write_text(
                json.dumps({"opener": "arose", "patterns": {"?????": [["linty", 20.0, True]]}})
            )
            (d / "second_guess_bad.json").write_text("{not json")
            with mock.patch("builtins.print"):
                tables = ws.load_second_guess_tables(d)
        self.assertEqual(list(tables), ["arose"])
        self.assertEqual(tables["arose"]["?????"][0][0], "linty")

    def test_committed_arose_table_is_valid(self):
        path = ws.SECOND_GUESS_DIR / "second_guess_arose.json"
        data = json.loads(path.read_text())
        self.assertEqual(data["opener"], "arose")
        self.assertIn("?G?GY", data["patterns"])
        for feedback, entries in data["patterns"].items():
            history = [("arose", feedback)]
            for word, _, _ in entries:
                self.assertTrue(ws.is_hard_mode_legal(word, history), (feedback, word))


class SimulatorTests(unittest.TestCase):
    words = sorted(["arose", "crest", "wrest", "prest", "trest", "dress", "unity"])

    def test_play_solves_and_memo_is_consistent(self):
        strategy = lab.make_strategy("bucket", self.words, {}, {}, 0)
        memo = {}
        first = {a: lab.play(a, "arose", strategy, self.words, memo) for a in self.words}
        again = {a: lab.play(a, "arose", strategy, self.words, {}) for a in self.words}
        self.assertEqual(first, again)
        self.assertTrue(all(solved for _, solved in first.values()))
        self.assertEqual(first["arose"], (["arose"], True))

    def test_play_rejects_hard_mode_violation(self):
        def cheat(candidates, history):
            return "unity"

        with self.assertRaises(RuntimeError):
            lab.play("wrest", "arose", cheat, self.words, {})


if __name__ == "__main__":
    unittest.main()

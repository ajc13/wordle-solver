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
        # crest (can't be the answer, splits worse) is dropped.
        self.assertEqual([w for w, _, _ in ranked], ["prest", "trest", "wrest"])

    def test_keeps_only_probes_that_beat_best_answer(self):
        ranked = [
            ("probe1", 1.0, False),
            ("answer1", 2.0, True),
            ("probe2", 2.0, False),
            ("answer2", 3.0, True),
            ("probe3", 4.0, False),
            ("answer3", None, True),
        ]
        self.assertEqual(
            [w for w, _, _ in ws.drop_dominated_probes(ranked)],
            ["probe1", "answer1", "answer2", "answer3"],
        )

    def test_real_list_is_answers_plus_few_probes(self):
        words = set(ws.load_words()) if ws.WORD_LIST_FILE.exists() else None
        if not words:
            self.skipTest("word list not downloaded")
        history = [("arose", "?????"), ("linty", "?Y???")]
        candidates = sorted(words)
        for g, r in history:
            candidates = ws.filter_word_list(candidates, g, r)
        _, ranked = ws.suggest(candidates, history, words, {}, work_limit=0)
        self.assertEqual({w for w, _, c in ranked if c}, set(candidates))
        self.assertLess(len(ranked), 2 * len(candidates))

    def test_list_position(self):
        ranked = [("a", 1.0, False)] + [(f"w{i}", 2.0, True) for i in range(12)]
        self.assertEqual(
            ws.list_position(ranked, 0, 10),
            "Showing 1-10 of 13: 12 possible answers, 1 other guess (·)",
        )
        self.assertEqual(
            ws.list_position(ranked[1:2], 0, 10), "Showing 1-1 of 1: 1 possible answer"
        )
        self.assertEqual(ws.list_position([], 0, 10), "No suggestions.")

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


class WeightTests(unittest.TestCase):
    def test_curve(self):
        self.assertEqual(ws.zipf_to_weight(0.0), ws.WEIGHT_FLOOR)
        self.assertAlmostEqual(ws.zipf_to_weight(ws.WEIGHT_CENTER), 0.5)
        self.assertGreater(ws.zipf_to_weight(6.0), 0.99)
        self.assertLess(ws.zipf_to_weight(2.5), ws.zipf_to_weight(3.0))

    def test_weighted_expected_remaining(self):
        # 2026-11-08: after arose and crush, birsy (obscure) or first (common).
        candidates, weights = ["birsy", "first"], [0.01, 1.0]
        self.assertAlmostEqual(
            ws.expected_remaining("first", candidates, weights)[0], 0.01 ** 2 / 1.01
        )
        self.assertAlmostEqual(
            ws.expected_remaining("birsy", candidates, weights)[0], 1 / 1.01
        )

    def test_rank_puts_common_word_first(self):
        candidates = ["birsy", "first"]
        unweighted = ws.rank_guesses(candidates, candidates)
        self.assertEqual(unweighted[0][0], "birsy")  # alphabetical tie
        weighted = ws.rank_guesses(candidates, candidates, {"first": 1.0})
        self.assertEqual(weighted[0][0], "first")

    def test_likelier_candidate_first(self):
        candidates = ["aaaaa", "bbbbb"]
        weights = {"aaaaa": 0.5, "bbbbb": 0.6}
        ranked = ws.rank_guesses(candidates, candidates, weights)
        # Guessing bbbbb leaves 0.5²/1.1; guessing aaaaa leaves 0.6²/1.1.
        self.assertEqual(ranked[0][0], "bbbbb")
        weights = {"aaaaa": 0.5, "bbbbb": 0.5}
        ranked = ws.rank_guesses(["bbbbb", "aaaaa"], candidates, weights)
        self.assertEqual(ranked[0][0], "aaaaa")  # true tie: alphabetical

    def test_load_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.json"
            self.assertIsNone(ws.load_word_weights(path))  # missing
            path.write_text("{not json")
            with mock.patch("builtins.print"):
                self.assertIsNone(ws.load_word_weights(path))
            path.write_text(json.dumps({"zipf": {"first": 6.1}}))
            weights = ws.load_word_weights(path)
        self.assertGreater(ws.word_weight("first", weights), 0.99)
        self.assertEqual(ws.word_weight("birsy", weights), ws.WEIGHT_FLOOR)
        self.assertEqual(ws.word_weight("birsy", None), 1.0)

    def test_answers_left(self):
        self.assertEqual(ws.answers_left(["first", "birsy"]), "2 possible answers left")
        self.assertEqual(
            ws.answers_left(["first", "birsy"], {"first": 1.0}),
            "2 possible answers left (~1 likely)",
        )
        self.assertEqual(ws.answers_left(["birsy"], {}), "1 possible answer left (all rare)")

    def test_committed_weights_file(self):
        data = json.loads(ws.WORD_WEIGHTS_FILE.read_text())
        self.assertIn("CC BY-SA", data["license"])
        self.assertGreater(len(data["zipf"]), 5000)
        self.assertTrue(all(z > 0 for z in data["zipf"].values()))


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

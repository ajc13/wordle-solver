"""Offline tools for wordle_solver — run these on a desktop, not on the phone.

  python3 wordle_lab.py simulate [--strategy bucket|frequency] [--opener arose]
                                 [--limit N] [--no-tables] [--work-limit N]
  python3 wordle_lab.py build-table [--opener arose] [--top 20]
  python3 wordle_lab.py build-weights    # needs: pip install wordfreq
  python3 wordle_lab.py bench            # the one command meant for the phone

simulate     Plays every past NYT answer (data/used_word_list.txt) in Hard Mode
             and reports average guesses, the distribution, failures and the
             hardest words. Results are saved to data/sim/.
build-table  Precomputes the best second guesses after an opener for every
             feedback pattern, into precomputed/second_guess_<opener>.json.
             The solver uses it so turn 2 is instant on slow devices.
build-weights
             Looks up each word's frequency (wordfreq package) and writes
             precomputed/word_weights.json, used to weight answer likelihood.
             Rebuild the second-guess table afterwards.

Weighting options (simulate, build-table): --no-weights, --center, --scale.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from collections import Counter
from datetime import datetime
from itertools import chain
from multiprocessing import Pool

import wordle_solver as ws

MAX_TURNS = 12  # stop runaway games; anything over 6 counts as a fail


def load_lists():
    words = sorted(ws.load_words())
    answers = sorted(ws.load_used_words() & set(words))
    counter = Counter(chain.from_iterable(words))
    total = sum(counter.values())
    letter_freq = {c: n / total for c, n in counter.items()}
    return words, answers, letter_freq


################################################################################
# Strategies: (candidates, history) -> next guess


def load_weights(args):
    if args.no_weights:
        return None
    weights = ws.load_word_weights(center=args.center, scale=args.scale)
    if weights is None:
        print("(no precomputed/word_weights.json: unweighted)")
    return weights


def make_strategy(name, words, letter_freq, tables, work_limit, weights=None):
    word_set = set(words)

    def frequency(candidates, history):
        return ws.sort_by_word_commonality(candidates, letter_freq)[0][0]

    def bucket(candidates, history):
        _, ranked = ws.suggest(
            candidates, history, word_set, letter_freq, tables, work_limit, weights
        )
        return ranked[0][0]

    return {"frequency": frequency, "bucket": bucket}[name]


def play(answer, opener, strategy, words, memo):
    """Play one Hard Mode game. Returns (guesses list, solved?)."""
    history = []
    candidates = words
    guess = opener
    for _ in range(MAX_TURNS):
        violation = ws.hard_mode_violation(guess, history)
        if violation:
            raise RuntimeError(f"{guess} breaks Hard Mode after {history}: {violation}")
        feedback = ws.score_guess(answer, guess)
        history.append((guess, feedback))
        if feedback == "G" * ws.WORD_LENGTH:
            return [g for g, _ in history], True
        candidates = ws.filter_word_list(candidates, guess, feedback)
        key = tuple(history)
        if key not in memo:
            memo[key] = strategy(candidates, history)
        guess = memo[key]
    return [g for g, _ in history], False


def cmd_simulate(args):
    words, answers, letter_freq = load_lists()
    if args.answers == "odd":
        answers = answers[1::2]
    elif args.answers == "even":
        answers = answers[::2]
    if args.limit:
        answers = answers[: args.limit]
    tables = {} if args.no_tables else ws.load_second_guess_tables(args.table_dir)
    weights = load_weights(args) if args.strategy == "bucket" else None
    strategy = make_strategy(
        args.strategy, words, letter_freq, tables, args.work_limit, weights
    )

    weighting = f"center={args.center} scale={args.scale}" if weights else "off"
    print(
        f"Simulating {len(answers)} answers ({args.answers}) · strategy={args.strategy} "
        f"opener={args.opener} tables={'off' if args.no_tables else sorted(tables) or 'none'} "
        f"weights={weighting} work_limit={args.work_limit or 'unlimited'}"
    )
    memo, results = {}, {}
    start = time.time()
    for i, answer in enumerate(answers, 1):
        guesses, solved = play(answer, args.opener, strategy, words, memo)
        results[answer] = {"guesses": guesses, "solved": solved}
        if i % 200 == 0:
            print(f"  {i}/{len(answers)} ({time.time() - start:.0f}s)")
    elapsed = time.time() - start

    counts = [len(r["guesses"]) for r in results.values() if r["solved"]]
    fails = sorted(a for a, r in results.items() if not r["solved"] or len(r["guesses"]) > 6)
    dist = Counter(min(n, 7) for n in counts)
    hardest = sorted(results.items(), key=lambda kv: (-len(kv[1]["guesses"]), kv[0]))[:10]

    print(f"\nAverage guesses: {sum(counts) / len(counts):.3f}  ({len(answers)} games, {elapsed:.0f}s)")
    for n in range(1, 8):
        label = f"{n}" if n < 7 else "7+"
        bar = "#" * round(60 * dist[n] / len(answers))
        print(f"  {label:>2}: {dist[n]:>5}  {bar}")
    print(f"Fails (>6 guesses): {len(fails)}" + (f"  {', '.join(fails[:15])}" if fails else ""))
    print("Hardest:")
    for answer, r in hardest:
        print(f"  {answer}: {' → '.join(r['guesses'])}")

    out_dir = ws.DATA_DIR / "sim"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = "" if weights is None else f"-w{args.center}-{args.scale}"
    out = out_dir / (
        f"{args.strategy}-{args.opener}{tag}{'-notables' if args.no_tables else ''}"
        f"-{args.answers}.json"
    )
    out.write_text(json.dumps({
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "strategy": args.strategy,
        "opener": args.opener,
        "answers": args.answers,
        "weights": None if weights is None else {"center": args.center, "scale": args.scale},
        "tables": not args.no_tables,
        "work_limit": args.work_limit,
        "games": len(answers),
        "average": sum(counts) / len(counts),
        "distribution": {str(k): dist[k] for k in sorted(dist)},
        "fails": fails,
        "elapsed_s": round(elapsed, 1),
        "results": results,
    }, indent=1))
    print(f"Saved {out}")


################################################################################
# Second-guess table

_WORDS = None
_WEIGHTS = None


def _init_worker(words, weights):
    global _WORDS, _WEIGHTS
    _WORDS, _WEIGHTS = words, weights


def _rank_pattern(job):
    opener, feedback, top = job
    history = [(opener, feedback)]
    candidates = ws.filter_word_list(_WORDS, opener, feedback)
    pool = [w for w in _WORDS if ws.is_hard_mode_legal(w, history)]
    ranked = ws.rank_guesses(candidates, pool, _WEIGHTS)[:top]
    return feedback, len(candidates), [[w, round(e, 3), c] for w, e, c in ranked]


def cmd_build_table(args):
    words, _, _ = load_lists()
    opener = args.opener.lower()
    if opener not in words:
        sys.exit(f"{opener} is not in the word list")
    patterns = sorted({ws.score_guess(answer, opener) for answer in words} - {"GGGGG"})
    weights = load_weights(args)
    print(f"Building second-guess table for {opener}: {len(patterns)} patterns, "
          f"weights={'off' if weights is None else f'center={args.center} scale={args.scale}'}")

    start = time.time()
    jobs = [(opener, p, args.top) for p in patterns]
    table, sizes = {}, {}
    with Pool(initializer=_init_worker, initargs=(words, weights)) as pool:
        for i, (feedback, n, ranked) in enumerate(pool.imap_unordered(_rank_pattern, jobs), 1):
            table[feedback], sizes[feedback] = ranked, n
            if i % 20 == 0:
                print(f"  {i}/{len(patterns)} ({time.time() - start:.0f}s)")

    out_dir = Path(args.out_dir) if args.out_dir else ws.SECOND_GUESS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"second_guess_{opener}.json"
    lines = [
        f'  {json.dumps(p)}: {json.dumps(table[p])}' for p in sorted(table)
    ]
    out.write_text(
        "{\n"
        f'"opener": {json.dumps(opener)},\n'
        f'"word_count": {len(words)},\n'
        f'"top": {args.top},\n'
        f'"weights": {json.dumps(None if weights is None else {"center": args.center, "scale": args.scale})},\n'
        f'"built_at": {json.dumps(datetime.now().isoformat(timespec="seconds"))},\n'
        '"patterns": {\n' + ",\n".join(lines) + "\n}\n}\n"
    )
    print(f"Saved {out} ({out.stat().st_size // 1024} KB, {time.time() - start:.0f}s)")


################################################################################
# Word weights


def cmd_build_weights(args):
    try:
        import wordfreq
    except ImportError:
        sys.exit("needs the wordfreq package (desktop only): pip install wordfreq")
    words = sorted(ws.load_words())
    zipf = {w: wordfreq.zipf_frequency(w, "en") for w in words}
    zipf = {w: z for w, z in zipf.items() if z > 0}  # missing = unknown = lowest weight
    try:
        from importlib.metadata import version
        wf_version = version("wordfreq")
    except Exception:
        wf_version = "unknown"
    ws.SECOND_GUESS_DIR.mkdir(parents=True, exist_ok=True)
    out = ws.WORD_WEIGHTS_FILE
    body = ",\n".join(f"  {json.dumps(w)}: {z}" for w, z in zipf.items())
    out.write_text(
        "{\n"
        '"source": "wordfreq (https://github.com/rspeer/wordfreq), English zipf frequency",\n'
        '"license": "Derived from wordfreq data, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)",\n'
        f'"wordfreq_version": {json.dumps(wf_version)},\n'
        f'"built_at": {json.dumps(datetime.now().isoformat(timespec="seconds"))},\n'
        '"zipf": {\n' + body + "\n}\n}\n"
    )
    print(f"Saved {out} ({len(zipf)} of {len(words)} words known, {out.stat().st_size // 1024} KB)")


################################################################################
# Benchmark (run this one on the phone)


def cmd_bench(args):
    words, answers, letter_freq = load_lists()
    word_set = set(words)
    tables = ws.load_second_guess_tables()
    weights = ws.load_word_weights()

    start = time.time()
    n = 20_000
    for i in range(n):
        ws.score_guess(words[i % len(words)], "arose")
    per_scoring = (time.time() - start) / n

    # Typical turn-3 positions: arose, then the table's pick, for a few answers.
    times = []
    for answer in answers[:: max(1, len(answers) // args.games)][: args.games]:
        history = [("arose", ws.score_guess(answer, "arose"))]
        candidates = ws.filter_word_list(words, "arose", history[0][1])
        _, ranked = ws.suggest(
            candidates, history, word_set, letter_freq, tables, weights=weights
        )
        second = ranked[0][0]
        fb = ws.score_guess(answer, second)
        if fb == "GGGGG":
            continue
        history.append((second, fb))
        candidates = ws.filter_word_list(candidates, second, fb)
        t = time.time()
        ws.suggest(candidates, history, word_set, letter_freq, tables, weights=weights)
        times.append(time.time() - t)

    times.sort()
    print(f"score_guess: {per_scoring * 1e6:.1f} µs each")
    print(f"turn-3 ranking over {len(times)} games (limit {ws.RANK_WORK_LIMIT}): "
          f"median {times[len(times) // 2]:.2f}s, max {times[-1]:.2f}s")
    target = 3.0  # seconds you're willing to wait, worst case
    suggested = int(target / per_scoring / 1.5 / 1000) * 1000
    print(f"For ~{target:.0f}s worst case, try: WORDLE_RANK_LIMIT={max(5000, suggested)}")


def add_weight_args(parser):
    parser.add_argument("--no-weights", action="store_true", help="every word equally likely")
    parser.add_argument("--center", type=float, default=ws.WEIGHT_CENTER)
    parser.add_argument("--scale", type=float, default=ws.WEIGHT_SCALE)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="play all past answers and report")
    sim.add_argument("--strategy", choices=["bucket", "frequency"], default="bucket")
    sim.add_argument("--opener", default="arose")
    sim.add_argument("--limit", type=int, default=0, help="only the first N answers")
    sim.add_argument("--no-tables", action="store_true", help="ignore precomputed tables")
    sim.add_argument(
        "--work-limit", type=int, default=ws.RANK_WORK_LIMIT,
        help="live ranking cap, as on the phone (0 = unlimited)",
    )
    sim.add_argument("--answers", choices=["all", "odd", "even"], default="all",
                     help="odd/even halves: tune on one, report on the other")
    sim.add_argument("--table-dir", default=None, help="read tables from here")
    add_weight_args(sim)
    sim.set_defaults(func=cmd_simulate)

    build = sub.add_parser("build-table", help="precompute second guesses for an opener")
    build.add_argument("--opener", default="arose")
    build.add_argument("--top", type=int, default=20)
    build.add_argument("--out-dir", default=None, help="write here instead of precomputed/")
    add_weight_args(build)
    build.set_defaults(func=cmd_build_table)

    weights = sub.add_parser("build-weights", help="word frequencies (needs wordfreq)")
    weights.set_defaults(func=cmd_build_weights)

    bench = sub.add_parser("bench", help="time ranking on this device (run on the phone)")
    bench.add_argument("--games", type=int, default=15)
    bench.set_defaults(func=cmd_bench)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

"""Offline tools for wordle_solver — run these on a desktop, not on the phone.

  python3 wordle_lab.py simulate [--strategy bucket|frequency] [--opener arose]
                                 [--limit N] [--no-tables] [--work-limit N]
  python3 wordle_lab.py build-table [--opener arose] [--top 20]
  python3 wordle_lab.py bench            # the one command meant for the phone

simulate     Plays every past NYT answer (data/used_word_list.txt) in Hard Mode
             and reports average guesses, the distribution, failures and the
             hardest words. Results are saved to data/sim/.
build-table  Precomputes the best second guesses after an opener for every
             feedback pattern, into precomputed/second_guess_<opener>.json.
             The solver uses it so turn 2 is instant on slow devices.
"""

import argparse
import json
import sys
import time
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


def make_strategy(name, words, letter_freq, tables, work_limit):
    word_set = set(words)

    def frequency(candidates, history):
        return ws.sort_by_word_commonality(candidates, letter_freq)[0][0]

    def bucket(candidates, history):
        _, ranked = ws.suggest(
            candidates, history, word_set, letter_freq, tables, work_limit
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
    if args.limit:
        answers = answers[: args.limit]
    tables = {} if args.no_tables else ws.load_second_guess_tables()
    strategy = make_strategy(args.strategy, words, letter_freq, tables, args.work_limit)

    print(
        f"Simulating {len(answers)} answers · strategy={args.strategy} "
        f"opener={args.opener} tables={'off' if args.no_tables else sorted(tables) or 'none'} "
        f"work_limit={args.work_limit or 'unlimited'}"
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
    out = out_dir / f"{args.strategy}-{args.opener}{'-notables' if args.no_tables else ''}.json"
    out.write_text(json.dumps({
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "strategy": args.strategy,
        "opener": args.opener,
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


def _init_worker(words):
    global _WORDS
    _WORDS = words


def _rank_pattern(job):
    opener, feedback, top = job
    history = [(opener, feedback)]
    candidates = ws.filter_word_list(_WORDS, opener, feedback)
    pool = [w for w in _WORDS if ws.is_hard_mode_legal(w, history)]
    ranked = ws.rank_guesses(candidates, pool)[:top]
    return feedback, len(candidates), [[w, round(e, 3), c] for w, e, c in ranked]


def cmd_build_table(args):
    words, _, _ = load_lists()
    opener = args.opener.lower()
    if opener not in words:
        sys.exit(f"{opener} is not in the word list")
    patterns = sorted({ws.score_guess(answer, opener) for answer in words} - {"GGGGG"})
    print(f"Building second-guess table for {opener}: {len(patterns)} patterns")

    start = time.time()
    jobs = [(opener, p, args.top) for p in patterns]
    table, sizes = {}, {}
    with Pool(initializer=_init_worker, initargs=(words,)) as pool:
        for i, (feedback, n, ranked) in enumerate(pool.imap_unordered(_rank_pattern, jobs), 1):
            table[feedback], sizes[feedback] = ranked, n
            if i % 20 == 0:
                print(f"  {i}/{len(patterns)} ({time.time() - start:.0f}s)")

    ws.SECOND_GUESS_DIR.mkdir(parents=True, exist_ok=True)
    out = ws.SECOND_GUESS_DIR / f"second_guess_{opener}.json"
    lines = [
        f'  {json.dumps(p)}: {json.dumps(table[p])}' for p in sorted(table)
    ]
    out.write_text(
        "{\n"
        f'"opener": {json.dumps(opener)},\n'
        f'"word_count": {len(words)},\n'
        f'"top": {args.top},\n'
        f'"built_at": {json.dumps(datetime.now().isoformat(timespec="seconds"))},\n'
        '"patterns": {\n' + ",\n".join(lines) + "\n}\n}\n"
    )
    print(f"Saved {out} ({out.stat().st_size // 1024} KB, {time.time() - start:.0f}s)")


################################################################################
# Benchmark (run this one on the phone)


def cmd_bench(args):
    words, answers, letter_freq = load_lists()
    word_set = set(words)
    tables = ws.load_second_guess_tables()

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
        _, ranked = ws.suggest(candidates, history, word_set, letter_freq, tables)
        second = ranked[0][0]
        fb = ws.score_guess(answer, second)
        if fb == "GGGGG":
            continue
        history.append((second, fb))
        candidates = ws.filter_word_list(candidates, second, fb)
        t = time.time()
        ws.suggest(candidates, history, word_set, letter_freq, tables)
        times.append(time.time() - t)

    times.sort()
    print(f"score_guess: {per_scoring * 1e6:.1f} µs each")
    print(f"turn-3 ranking over {len(times)} games (limit {ws.RANK_WORK_LIMIT}): "
          f"median {times[len(times) // 2]:.2f}s, max {times[-1]:.2f}s")
    target = 3.0  # seconds you're willing to wait, worst case
    suggested = int(target / per_scoring / 1.5 / 1000) * 1000
    print(f"For ~{target:.0f}s worst case, try: WORDLE_RANK_LIMIT={max(5000, suggested)}")


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
    sim.set_defaults(func=cmd_simulate)

    build = sub.add_parser("build-table", help="precompute second guesses for an opener")
    build.add_argument("--opener", default="arose")
    build.add_argument("--top", type=int, default=20)
    build.set_defaults(func=cmd_build_table)

    bench = sub.add_parser("bench", help="time ranking on this device (run on the phone)")
    bench.add_argument("--games", type=int, default=15)
    bench.set_defaults(func=cmd_bench)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

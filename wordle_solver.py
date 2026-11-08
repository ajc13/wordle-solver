# wordle_solver.py

################################################################################
# This script is a Wordle solver that uses a list of valid words and past answers
# to suggest the best guesses based on letter frequency and user input.
# It scrapes the past answers from a website and flags them in the suggestion list.
# The script also allows the user to input their guesses and the corresponding feedback
# (green, yellow, gray) to narrow down the possible words.
################################################################################

################################################################################
# Imports
################################################################################
import requests
import certifi
from bs4 import BeautifulSoup
import re
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta

import json
import math
import os
import shutil
import string
import operator
import urllib.request
from itertools import chain

################################################################################
# Configuration
WORD_LIST_URL = "https://raw.githubusercontent.com/tabatkins/wordle-list/main/words"

FIVEFORKS_URL = "https://www.fiveforks.com/wordle/"

# Identify honestly when scraping; fiveforks.com's robots.txt allows /wordle/.
SCRAPER_USER_AGENT = "wordle-solver (+https://github.com/ajc13/wordle-solver)"

SCRIPT_DIR = Path(__file__).resolve().parent

# Downloaded lists live in data/ next to this script, not the current directory.
DATA_DIR = SCRIPT_DIR / "data"
WORD_LIST_FILE = DATA_DIR / "valid_word_list.txt"
USED_LIST_FILE = DATA_DIR / "used_word_list.txt"

MAX_AGE_DAYS = 7

ALLOWABLE_CHARACTERS = set(string.ascii_letters)

ALLOWED_ATTEMPTS = 6
WORD_LENGTH = 5

# Weekly logs: logs/YYYY/MM/wordle_solver_<monday>.log, next to this script.
# The folder is chosen by the week's Monday so a week never splits across files.
LOG_DIR = SCRIPT_DIR / "logs"

GUESS_RESPONSE_SEPARATOR = re.compile(r"[/\s]+")

# A solved guess in the logs, current or older format:
#   "[2026-10-20 08:12:03] 4,wrest,GGGGG (1 left)"   or   "4,wrest,GGGGG"
# Summary lines ("#   4. wrest → GGGGG") intentionally do not match.
SOLVE_LINE = re.compile(r"(?:^|\] )\d+,([a-z]{5}),GGGGG\b", re.MULTILINE)

OWN_SOLVE_MARK = " ✅"
PAST_ANSWER_MARK = " 🔁"


################################################################################
def format_history_line(entry):
    attempt, word, response, before, after = entry
    return f"{attempt}. {word:<10} → {response:<5} ({before} → {after} left, {before - after} cut)"


def log_game_summary(guess_history):
    log_event("# Game Summary:")
    for entry in guess_history:
        log_event(f"#   {format_history_line(entry)}")
    log_event(f"# Total guesses: {len(guess_history)}")
    log_event("")  # Blank line to separate sessions


def print_game_summary(guess_history):
    print("\n🧾 Game Summary")
    print("-" * 40)
    for entry in guess_history:
        print(f" {format_history_line(entry)}")
    print("-" * 40)
    print(f" Total guesses: {len(guess_history)}")


def log_path_for(when: datetime) -> Path:
    monday = (when - timedelta(days=when.weekday())).date()
    return (
        LOG_DIR
        / f"{monday:%Y}"
        / f"{monday:%m}"
        / f"wordle_solver_{monday:%Y-%m-%d}.log"
    )


def log_event(message: str):
    now = datetime.now()
    path = log_path_for(now)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as log:
        log.write(f"[{now:%Y-%m-%d %H:%M:%S}] {message}\n")


def fetch_used_words_from_fiveforks(file_path=USED_LIST_FILE):
    def _attempt_scrape(verify_ssl=True):
        verify_path = certifi.where() if verify_ssl else False
        headers = {
            "User-Agent": SCRAPER_USER_AGENT,
            "Accept": "text/html",
        }
        resp = requests.get(
            FIVEFORKS_URL, headers=headers, verify=verify_path, timeout=10
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        alphalist_div = soup.find("div", id="alphalist")
        if not alphalist_div:
            raise ValueError("Could not find #alphalist block in HTML.")

        # Extract all 5-letter uppercase words (ignore counts)
        matches = re.findall(r"\b([A-Z]{5})\b", alphalist_div.get_text())
        return [word.lower() for word in sorted(set(matches))]

    print(f"Scraping past answers from {FIVEFORKS_URL}...")
    try:
        try:
            words = _attempt_scrape(verify_ssl=True)
        except requests.exceptions.SSLError:
            print("⚠️  SSL verification failed — retrying with verification disabled...")
            words = _attempt_scrape(verify_ssl=False)
    except Exception as e:
        print(f"⚠️  Failed to scrape answers: {e}")
        print(f"⚠️  Proceeding without refreshing {file_path}")
        return

    with open(file_path, "w") as f:
        f.write("\n".join(words) + "\n")
    print(f"✅ Saved {len(words)} used answers to {file_path}")

    log_event("Fetched used word list.")


def file_older_than(path: str, days: int) -> bool:
    p = Path(path)
    if not p.exists():
        return True
    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    return datetime.now() - mtime > timedelta(days=days)


def download_file(url: str, destination: str):
    print(f"Downloading {url} → {destination}")
    try:
        urllib.request.urlretrieve(url, destination)
        log_event("Word list retreived.")
    except Exception as e:
        print(f"⚠️  Failed to download {url}: {e}")
        print(f"⚠️  Proceeding without refreshing {destination}")


def refresh_file_if_needed(file_path: str, url: str, force: bool = False):
    if force or file_older_than(file_path, MAX_AGE_DAYS):
        download_file(url, file_path)


def migrate_legacy_data_files(old_dir=None):
    """
    Move word lists left in the current directory by older versions into
    data/, so they are reused instead of downloaded again.
    """
    old_dir = Path.cwd() if old_dir is None else Path(old_dir)
    for target in (WORD_LIST_FILE, USED_LIST_FILE):
        legacy = old_dir / target.name
        if legacy.resolve() == target.resolve():
            continue
        if legacy.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy), str(target))
            print(f"Moved {legacy} → {target}")
            log_event(f"Moved legacy {legacy.name} into {target.parent}")


def refresh_word_lists(force_wordlist=False, force_used=False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    migrate_legacy_data_files()

    refresh_file_if_needed(WORD_LIST_FILE, WORD_LIST_URL, force_wordlist)

    if force_used or file_older_than(USED_LIST_FILE, MAX_AGE_DAYS):
        fetch_used_words_from_fiveforks(USED_LIST_FILE)


def load_words():
    return {
        word.lower()
        for word in Path(WORD_LIST_FILE).read_text().splitlines()
        if len(word) == WORD_LENGTH and set(word) < ALLOWABLE_CHARACTERS
    }


def load_used_words():
    """Past NYT answers scraped from FiveForks (empty set if unavailable)."""
    if not Path(USED_LIST_FILE).exists():
        print("⚠️  No used word list found — continuing without NYT filter.")
        return set()
    return {
        word.strip().lower()
        for word in Path(USED_LIST_FILE).read_text().splitlines()
        if len(word.strip()) == WORD_LENGTH
    }


def load_own_solves(log_dir=None):
    """Words you have solved, read from GGGGG lines in the game logs."""
    log_dir = LOG_DIR if log_dir is None else Path(log_dir)
    solves = set()
    for path in sorted(log_dir.rglob("*.log")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        solves.update(SOLVE_LINE.findall(text))
    return solves


def calculate_word_commonality(word, letter_freq):
    score = 0.0
    for char in word:
        score += letter_freq[char]
    return score / (WORD_LENGTH - len(set(word)) + 1)


def sort_by_word_commonality(words, letter_freq):
    sort_by = operator.itemgetter(1)
    return sorted(
        [(word, calculate_word_commonality(word, letter_freq)) for word in words],
        key=sort_by,
        reverse=True,
    )


def past_answer_mark(word, used_words=None, own_solves=None):
    """✅ for words you solved, 🔁 for other known past answers, else ''."""
    if own_solves and word in own_solves:
        return OWN_SOLVE_MARK
    if used_words and word in used_words:
        return PAST_ANSWER_MARK
    return ""


RANKING_HEADERS = {
    "frequency": "Ranked by letter frequency (higher is better)",
    "bucket": "Ranked by expected words left (lower is better) · = can't be the answer",
    "table": "Ranked by expected words left (lower is better, precomputed) · = can't be the answer",
}


def answers_left(candidates, weights=None):
    """e.g. "12 possible answers left (~3 likely)"."""
    n = len(candidates)
    line = f"{n} possible answer{'s' * (n != 1)} left"
    if weights is not None and n:
        likely = sum(word_weight(w, weights) for w in candidates)
        line += f" (~{likely:.0f} likely)" if likely >= 1 else " (all rare)"
    return line


def display_word_table(
    ranked, used_words=None, start_index=0, own_solves=None, method="frequency",
    weights=None,
):
    """ranked: [(word, score, is_candidate), ...] slice to show."""
    for i, (word, score, is_candidate) in enumerate(ranked, start=start_index + 1):
        mark = past_answer_mark(word, used_words, own_solves)
        if score is None:
            shown = "-"
        elif method == "frequency":
            shown = f"{score:.2}"
        else:
            shown = f"{score:.1f}"
        probe = "" if is_candidate else " ·"
        rare = " rare" if is_candidate and weights is not None and word_weight(word, weights) < RARE_WEIGHT else ""
        print(f"{i:>3}. {word:<10} | {shown:<6}{probe}{rare}{mark}")


def list_position(ranked, start, window):
    """e.g. "Showing 1-10 of 14: 12 possible answers, 2 other guesses"."""
    total = len(ranked)
    if not total:
        return "No suggestions."
    end = min(start + window, total)
    answers = sum(1 for _, _, cand in ranked if cand)
    others = total - answers
    line = f"Showing {start + 1}-{end} of {total}: {answers} possible answer{'s' * (answers != 1)}"
    if others:
        line += f", {others} other guess{'es' * (others != 1)} (·)"
    return line


def parse_response(raw):
    """Normalize a response string; return None if it is not valid."""
    response = raw.strip().upper().replace(".", "?")
    if len(response) == WORD_LENGTH and set(response) <= {"G", "Y", "?"}:
        return response
    return None


def input_word(WORDS, letter_freq, used_words=None, own_solves=None):
    """
    Read a guess (or a command). Returns (word, response).
    response is set only when the guess was entered as "word/response" or
    "word response"; otherwise it is None and the caller prompts for it.
    """
    while True:
        raw = input("Input the word you entered> ").strip()
        word = raw.lower()
        response = None

        if word.startswith("+"):
            try:
                n = int(word[1:]) if word[1:] else 10
            except ValueError:
                n = 10
            return f"CMD_NEXT_{n}", None

        if word.startswith("-"):
            try:
                n = int(word[1:]) if word[1:] else 10
            except ValueError:
                n = 10
            return f"CMD_PREV_{n}", None

        if word == "^":
            return "CMD_RESET", None

        if word in {"q", "quit"}:
            return "CMD_QUIT", None

        if word in {"r", "restart"}:
            return "CMD_RESTART", None

        if word in {"?", "help"}:
            return "CMD_HELP", None

        if word in {"!", "history"}:
            return "CMD_HISTORY", None

        parts = GUESS_RESPONSE_SEPARATOR.split(word)
        if len(parts) == 2:
            word = parts[0]
            response = parse_response(parts[1])
            if response is None:
                print(f"Error - invalid response {parts[1].upper()}")
                continue
        elif len(parts) > 2:
            print("Error - use 'word', 'word/response' or 'word response'")
            continue

        if len(word) != WORD_LENGTH or word not in WORDS:
            print(f"Error - '{word}' is not in the word list")
            continue

        if own_solves and word in own_solves:
            print("⚠️  Warning: You've solved this word before.")
        elif used_words and word in used_words:
            print("⚠️  Warning: This word is a known past NYT solution.")

        print(f"{word:<10} | {calculate_word_commonality(word, letter_freq):<5.2}")
        return word, response


def input_response():
    print("Color-coded reply:")
    print("G for Green | Y for Yellow | ? for Gray")

    while True:
        raw = input("Response> ")
        response = parse_response(raw)
        if response:
            return response
        print(f"Error - invalid answer {raw.strip().upper()}")


def word_matches_feedback(word, guess, feedback):
    """
    Check if a candidate word matches the feedback from a guess.
    G = correct letter, correct position
    Y = correct letter, wrong position
    ? = letter not in word (or overused)
    """
    if len(word) != len(guess) or len(guess) != len(feedback):
        return False

    word = word.lower()
    guess = guess.lower()

    # Step 1: Track correct letters for greens
    remaining_letters = Counter(word)

    # Green pass
    for i in range(len(guess)):
        if feedback[i] == "G":
            if word[i] != guess[i]:
                return False
            remaining_letters[guess[i]] -= 1

    # Yellow pass
    for i in range(len(guess)):
        if feedback[i] == "Y":
            if guess[i] == word[i]:
                return False
            if remaining_letters[guess[i]] <= 0:
                return False
            remaining_letters[guess[i]] -= 1

    # Gray pass
    for i in range(len(guess)):
        if feedback[i] == "?":
            # A gray tile means the letter is not at this position, and the
            # word has no copies beyond those already marked green/yellow.
            if word[i] == guess[i] or remaining_letters[guess[i]] > 0:
                return False

    return True


def filter_word_list(possible_words, guess, feedback):
    return [w for w in possible_words if word_matches_feedback(w, guess, feedback)]


################################################################################
# Ranking (Hard Mode)
#
# A guess is scored by how well it splits the remaining candidates: group the
# candidates by the feedback the guess would produce, and compute the expected
# number of words left afterwards (lower is better). Guesses are drawn from all
# words that are legal in Hard Mode, not just the candidates.
#
# With word weights (precomputed/word_weights.json), each candidate counts by how
# likely it is to be an answer: common words near 1, obscure words near 0.01.
# "Expected words left" then means expected *likely* words left.
#
# Live ranking is capped at RANK_WORK_LIMIT guess×candidate scorings so it stays
# responsive on slow devices (e.g. iSH on iPhone). Turn 2 after a known opener
# uses a table precomputed on a desktop (see wordle_lab.py build-table).

def score_guess(answer, guess):
    """NYT Wordle feedback for guess against answer, e.g. "?G?GY"."""
    result = ["?"] * WORD_LENGTH
    unmatched = Counter()
    for i in range(WORD_LENGTH):
        if guess[i] == answer[i]:
            result[i] = "G"
        else:
            unmatched[answer[i]] += 1
    for i in range(WORD_LENGTH):
        if result[i] != "G" and unmatched[guess[i]] > 0:
            result[i] = "Y"
            unmatched[guess[i]] -= 1
    return "".join(result)


def hard_mode_violation(guess, history):
    """
    Return why guess breaks Hard Mode given history [(guess, feedback), ...],
    or None if it is legal. Greens must stay in place; letters shown green or
    yellow must be reused (at least as many times as revealed).
    """
    required = Counter()
    for prev, feedback in history:
        revealed = Counter()
        for i, (letter, mark) in enumerate(zip(prev, feedback)):
            if mark == "G" and guess[i] != letter:
                return f"{letter.upper()} must be in position {i + 1}"
            if mark in "GY":
                revealed[letter] += 1
        for letter, count in revealed.items():
            required[letter] = max(required[letter], count)

    have = Counter(guess)
    for letter in sorted(required):
        if have[letter] < required[letter]:
            times = f" {required[letter]} times" if required[letter] > 1 else ""
            return f"must use {letter.upper()}{times}"
    return None


def is_hard_mode_legal(guess, history):
    return hard_mode_violation(guess, history) is None


def expected_remaining(guess, candidates, weights=None):
    """
    (expected words left, worst-case words left) after playing guess.
    weights, if given, is a list of answer likelihoods aligned with candidates.
    """
    solved = "G" * WORD_LENGTH
    if weights is None:
        buckets = Counter(score_guess(answer, guess) for answer in candidates)
        buckets.pop(solved, None)  # solved: nothing left
        expected = sum(n * n for n in buckets.values()) / len(candidates)
        return expected, max(buckets.values(), default=0)

    counts, mass = Counter(), {}
    for answer, w in zip(candidates, weights):
        feedback = score_guess(answer, guess)
        counts[feedback] += 1
        mass[feedback] = mass.get(feedback, 0.0) + w
    total = sum(weights)
    counts.pop(solved, None)
    mass.pop(solved, None)
    expected = sum(m * m for m in mass.values()) / total
    return expected, max(counts.values(), default=0)


def rank_guesses(candidates, pool, weights=None):
    """
    Rank pool by expected words left. Ties prefer possible answers, then
    likelier words, then a smaller worst case.
    weights: optional {word: likelihood}. Returns [(word, expected, is_candidate), ...].

    Every possible answer is kept. A guess that can't be the answer is kept
    only if it beats the best possible answer; otherwise playing that answer
    splits at least as well and might win outright.
    """
    candidate_set = set(candidates)
    aligned = None if weights is None else [word_weight(w, weights) for w in candidates]
    scored = []
    for guess in pool:
        expected, worst = expected_remaining(guess, candidates, aligned)
        likelihood = word_weight(guess, weights) if guess in candidate_set else 0.0
        scored.append((round(expected, 9), guess not in candidate_set, -likelihood, worst, guess))
    scored.sort()
    return drop_dominated_probes(
        [(guess, expected, not probe) for expected, probe, _, _, guess in scored]
    )


def drop_dominated_probes(ranked):
    """Drop non-answers that don't beat the best-scored possible answer."""
    best = min((s for _, s, cand in ranked if cand and s is not None), default=None)
    if best is None:
        return ranked
    return [r for r in ranked if r[2] or (r[1] is not None and r[1] < best)]


SECOND_GUESS_DIR = SCRIPT_DIR / "precomputed"
WORD_WEIGHTS_FILE = SECOND_GUESS_DIR / "word_weights.json"
# Answer likelihood from word frequency (zipf: ~0 unknown, 3 uncommon, 6 very
# common): an S-curve centred on WEIGHT_CENTER, never below WEIGHT_FLOOR so
# obscure words stay possible. Past NYT answers are almost all zipf 2 or more.
WEIGHT_CENTER = 2.0
WEIGHT_SCALE = 0.3
WEIGHT_FLOOR = 0.01
RARE_WEIGHT = 0.1  # below this a candidate is shown as "rare"


def zipf_to_weight(zipf, center=WEIGHT_CENTER, scale=WEIGHT_SCALE):
    return max(WEIGHT_FLOOR, 1 / (1 + math.exp(-(zipf - center) / scale)))


def word_weight(word, weights):
    """Likelihood of word being an answer (1.0 when no weights are loaded)."""
    if weights is None:
        return 1.0
    return weights.get(word, WEIGHT_FLOOR)


def load_word_weights(path=None, center=WEIGHT_CENTER, scale=WEIGHT_SCALE):
    """{word: likelihood} from word_weights.json, or None if unavailable."""
    path = WORD_WEIGHTS_FILE if path is None else Path(path)
    if not path.exists():
        return None
    try:
        zipf = json.loads(path.read_text())["zipf"]
    except (OSError, ValueError, KeyError) as e:
        print(f"⚠️  Ignoring {path.name}: {e}")
        return None
    return {w: zipf_to_weight(z, center, scale) for w, z in zipf.items()}
# Lower this on slow devices (python3 wordle_lab.py bench suggests a value):
#   WORDLE_RANK_LIMIT=30000 python3 wordle_solver.py
RANK_WORK_LIMIT = int(os.environ.get("WORDLE_RANK_LIMIT", "100000"))


def load_second_guess_tables(table_dir=None):
    """{opener: {feedback: [[word, expected, is_candidate], ...]}} from table files."""
    table_dir = SECOND_GUESS_DIR if table_dir is None else Path(table_dir)
    tables = {}
    for path in sorted(table_dir.glob("second_guess_*.json")):
        try:
            data = json.loads(path.read_text())
            tables[data["opener"]] = data["patterns"]
        except (OSError, ValueError, KeyError) as e:
            print(f"⚠️  Ignoring {path.name}: {e}")
    return tables


def suggest(
    candidates, history, words, letter_freq, tables=None, work_limit=RANK_WORK_LIMIT,
    weights=None,
):
    """
    Rank next guesses. Returns (method, [(word, score, is_candidate), ...]).
    method is "table" or "bucket" (score = expected words left, lower is
    better) or "frequency" (score = letter frequency, higher is better).
    """
    if not candidates:
        return "bucket", []

    if tables and len(history) == 1:
        opener, feedback = history[0]
        entries = tables.get(opener, {}).get(feedback)
        if entries:
            ranked = drop_dominated_probes([
                (w, score, is_cand)
                for w, score, is_cand in entries
                if w in words and is_hard_mode_legal(w, history)
            ])
            listed = {w for w, _, _ in ranked}
            rest = [w for w, _ in sort_by_word_commonality(candidates, letter_freq)]
            if weights is not None:  # likeliest first; stable sort keeps ties
                rest.sort(key=lambda w: -word_weight(w, weights))
            ranked += [(w, None, True) for w in rest if w not in listed]
            return "table", ranked

    unlimited = not work_limit
    if history and (unlimited or len(candidates) ** 2 <= work_limit):
        pool = [w for w in words if is_hard_mode_legal(w, history)]
        if unlimited or len(candidates) * len(pool) <= work_limit:
            return "bucket", rank_guesses(candidates, pool, weights)
        return "bucket", rank_guesses(candidates, candidates, weights)

    return "frequency", [
        (w, score, True) for w, score in sort_by_word_commonality(candidates, letter_freq)
    ]


def solve():
    """Load word lists once, then play games until the user stops restarting."""
    import sys

    force_refresh = "--refresh" in sys.argv
    force_used = "--refresh-used" in sys.argv

    refresh_word_lists(force_refresh, force_used)
    WORDS = load_words()

    LETTER_COUNTER = Counter(chain.from_iterable(WORDS))

    LETTER_FREQUENCY = {
        character: value / sum(LETTER_COUNTER.values())
        for character, value in LETTER_COUNTER.items()
    }

    USED_WORDS = load_used_words()
    tables = load_second_guess_tables()
    weights = load_word_weights()

    args = " ".join(sys.argv[1:])

    while True:
        # Re-read each game so a solve from the previous game is included.
        own_solves = load_own_solves()
        result = play_game(
            WORDS, LETTER_FREQUENCY, USED_WORDS, args, own_solves, tables, weights
        )
        if result != "restart":
            break
        print("Restarting...")


def play_game(
    WORDS, LETTER_FREQUENCY, USED_WORDS, args="", own_solves=None, tables=None,
    weights=None,
):
    """Play one game. Returns "restart" if the user asked to restart."""
    own_solves = own_solves or set()
    guess_history = []
    ranking = None  # (method, ranked) for the current candidates

    possible_words = WORDS.copy()

    offset_start = 0
    window_size = 10

    attempt = 1
    override_attempts = 0

    log_event("# Session started")
    log_event(f"# Args: {args or 'none'}")

    while True:
        print(f"Attempt {attempt}: {answers_left(possible_words, weights)}")

        history = [(g, r) for _, g, r, _, _ in guess_history]
        if ranking is None:  # only re-rank after a new guess, not when paging
            ranking = suggest(
                possible_words, history, WORDS, LETTER_FREQUENCY, tables,
                weights=weights,
            )
        method, ranked_words = ranking

        print("+ / +n more | - / -n back | ^ reset ")
        print(RANKING_HEADERS[method])

        display_word_table(
            ranked_words[offset_start : offset_start + window_size],
            USED_WORDS,
            start_index=offset_start,
            own_solves=own_solves,
            method=method,
            weights=weights,
        )
        print(list_position(ranked_words, offset_start, window_size))

        words_before = len(possible_words)

        word, response = input_word(WORDS, LETTER_FREQUENCY, USED_WORDS, own_solves)

        if not word.startswith("CMD_"):
            # NYT rejects these guesses in Hard Mode, so they can't have been played.
            violation = hard_mode_violation(word, history)
            if violation:
                print(f"❌ Not allowed in Hard Mode: {violation}. Enter another word.")
                continue

        if word.startswith("CMD_NEXT_"):
            step = int(word.split("_")[-1])
            last_page = max(len(ranked_words) - window_size, 0)
            if offset_start >= last_page:
                print("(end of list)")
            offset_start = min(offset_start + step, last_page)
            continue

        if word.startswith("CMD_PREV_"):
            step = int(word.split("_")[-1])
            if offset_start == 0:
                print("(top of list)")
            offset_start = max(0, offset_start - step)
            continue

        if word == "CMD_RESET":
            offset_start = 0
            continue

        if word == "CMD_QUIT":
            print("Exiting.")

            log_event("# Session ended (user quit)")
            log_game_summary(guess_history)
            print_game_summary(guess_history)
            return

        if word == "CMD_RESTART":
            log_event("# Session ended (user restarted)")
            log_game_summary(guess_history)
            print_game_summary(guess_history)
            return "restart"

        if word == "CMD_HISTORY":
            if guess_history:
                print("Guess history:")
                for entry in guess_history:
                    print(f" {format_history_line(entry)}")
            else:
                print("No guesses yet.")
            continue

        if word == "CMD_HELP":
            print("Help:")
            print("  + / +n         Show next suggestions")
            print("  - / -n         Show previous suggestions")
            print("  ^              Reset to top of suggestion list")
            print("  q / quit       Quit the solver")
            print("  r / restart    Restart the session")
            print(
                "  ! / history    Show past guesses and how many words remained after each"
            )
            print("  ? / help       Show this help screen")
            print("  word/GY?.. or 'word GY?..'  Enter guess and response at once")
            print(f" {OWN_SOLVE_MARK} you solved this before  {PAST_ANSWER_MARK} past NYT answer")
            print(
                f"After {ALLOWED_ATTEMPTS} guesses, you will be asked if you'd like to continue."
            )
            continue

        if response is None:
            response = input_response()

        possible_words = filter_word_list(possible_words, word, response)

        offset_start = 0  # Reset suggestion list window after filtering
        ranking = None  # Re-rank for the new candidates

        log_event(f"{attempt},{word},{response} ({len(possible_words)} left)")

        words_after = len(possible_words)
        guess_history.append((attempt, word, response, words_before, words_after))

        if response == "GGGGG":
            log_event("# Session ended (solved)")
            log_game_summary(guess_history)
            print_game_summary(guess_history)
            print("🎉 Word solved!")
            return
        attempt += 1

        if attempt > ALLOWED_ATTEMPTS + override_attempts:
            print(f"\n❌ You've reached the {attempt - 1}-guess limit.")
            choice = input("Continue anyway? (y/N)> ").strip().lower()
            if choice in {"y", "yes"}:
                print("Continuing...")
                override_attempts += 1
            else:
                log_event("# Session ended (max guesses)")
                log_game_summary(guess_history)
                print_game_summary(guess_history)
                print("Exiting.")
                return

        if not possible_words:
            print("\n❌ No possible words remaining based on given feedback.")
            print("❌ Double-check your inputs ('!' shows history). Restart with 'r'.\n")
            # Session stays open: the summary is logged once, when the user
            # quits or restarts.
            log_event("# No words remaining")


def debug_filter(word, guesses):
    for guess, feedback in guesses:
        print(
            f"{word} vs {guess} → {feedback} →",
            word_matches_feedback(word, guess, feedback),
        )


if __name__ == "__main__":
    solve()

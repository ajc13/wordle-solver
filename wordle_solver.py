# wordle_solver.py

################################################################################
# This script is a Wordle solver that uses a list of valid words and past answers
# to suggest the best guesses based on letter frequency and user input.
# It scrapes the past answers from a website and uses them to filter out known solutions.
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

import string
import operator
import urllib.request
from itertools import chain

################################################################################
# Configuration
WORD_LIST_URL = "https://raw.githubusercontent.com/tabatkins/wordle-list/main/words"

FIVEFORKS_URL = "https://www.fiveforks.com/wordle/"

WORD_LIST_FILE = "valid_word_list.txt"
USED_LIST_FILE = "used_word_list.txt"

MAX_AGE_DAYS = 7

ALLOWABLE_CHARACTERS = set(string.ascii_letters)

ALLOWED_ATTEMPTS = 6
WORD_LENGTH = 5

# Weekly logs: logs/YYYY/MM/wordle_solver_<monday>.log, next to this script.
# The folder is chosen by the week's Monday so a week never splits across files.
LOG_DIR = Path(__file__).resolve().parent / "logs"

GUESS_RESPONSE_SEPARATOR = re.compile(r"[/\s]+")


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
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
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
        words = _attempt_scrape(verify_ssl=True)
    except requests.exceptions.SSLError:
        print("⚠️  SSL verification failed — retrying with verification disabled...")
        words = _attempt_scrape(verify_ssl=False)
    except Exception as e:
        print(f"⚠️  Failed to scrape answers: {e}")
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


def refresh_word_lists(force_wordlist=False, force_used=False):
    refresh_file_if_needed(WORD_LIST_FILE, WORD_LIST_URL, force_wordlist)

    if force_used or file_older_than(USED_LIST_FILE, MAX_AGE_DAYS):
        fetch_used_words_from_fiveforks(USED_LIST_FILE)


def load_words():
    return {
        word.lower()
        for word in Path(WORD_LIST_FILE).read_text().splitlines()
        if len(word) == WORD_LENGTH and set(word) < ALLOWABLE_CHARACTERS
    }


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


def display_word_table(word_commonalities, used_words=None, start_index=0):
    for i, (word, freq) in enumerate(word_commonalities, start=start_index + 1):
        mark = " 🔁" if used_words and word in used_words else ""
        print(f"{i:>3}. {word:<10} | {freq:<5.2}{mark}")


def parse_response(raw):
    """Normalize a response string; return None if it is not valid."""
    response = raw.strip().upper().replace(".", "?")
    if len(response) == WORD_LENGTH and set(response) <= {"G", "Y", "?"}:
        return response
    return None


def input_word(WORDS, letter_freq, used_words=None):
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

        if used_words and word in used_words:
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


def solve():
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

    if Path(USED_LIST_FILE).exists():
        USED_WORDS = set(
            word.strip().lower()
            for word in Path(USED_LIST_FILE).read_text().splitlines()
            if len(word.strip()) == WORD_LENGTH
        )
    else:
        print("⚠️  No used word list found — continuing without NYT filter.")
        USED_WORDS = set()

    guess_history = []

    possible_words = WORDS.copy()

    offset_start = 0
    window_size = 10

    attempt = 1
    override_attempts = 0

    args = " ".join(sys.argv[1:])

    log_event("# Session started")
    log_event(f"# Args: {args or 'none'}")

    while True:
        print(f"Attempt {attempt} with {len(possible_words)} possible words")

        ranked_words = sort_by_word_commonality(possible_words, LETTER_FREQUENCY)

        print("+ / +n more | - / -n back | ^ reset ")

        display_word_table(
            ranked_words[offset_start : offset_start + window_size],
            USED_WORDS,
            start_index=offset_start,
        )

        words_before = len(possible_words)

        word, response = input_word(WORDS, LETTER_FREQUENCY, USED_WORDS)

        if word.startswith("CMD_NEXT_"):
            step = int(word.split("_")[-1])
            offset_start = min(
                offset_start + step, max(len(ranked_words) - window_size, 0)
            )
            continue

        if word.startswith("CMD_PREV_"):
            step = int(word.split("_")[-1])
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
            print("Restarting...")

            log_event("# Session ended (user restarted)")
            log_game_summary(guess_history)
            print_game_summary(guess_history)
            return solve()

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
            print(
                f"After {ALLOWED_ATTEMPTS} guesses, you will be asked if you'd like to continue."
            )
            continue

        if response is None:
            response = input_response()

        possible_words = filter_word_list(possible_words, word, response)

        offset_start = 0  # Reset suggestion list window after filtering

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
            print("❌ Double-check your inputs. Restart with 'r'.\n")

            log_event("# Session ended (no words remaining)")
            log_game_summary(guess_history)
            print_game_summary(guess_history)

            continue


def debug_filter(word, guesses):
    for guess, feedback in guesses:
        print(
            f"{word} vs {guess} → {feedback} →",
            word_matches_feedback(word, guess, feedback),
        )


if __name__ == "__main__":
    solve()

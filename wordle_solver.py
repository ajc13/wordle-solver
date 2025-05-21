# wordl_solver.py

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

from datetime import datetime
from pathlib import Path

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

LOG_FILE = "wordle_solver.log"


################################################################################
def log_game_summary(guess_history):
    log_event("# Game Summary:")
    for attempt, word, response, before, after in guess_history:
        log_event(
            f"#   {attempt}. {word:<10} → {response:<5} ({before} → {after} left, {before - after} cut)"
        )
    log_event(f"# Total guesses: {len(guess_history)}")
    log_event("")  # Blank line to separate sessions


def print_game_summary(guess_history):
    print("\n🧾 Game Summary")
    print("-" * 40)
    for attempt, word, response, before, after in guess_history:
        print(
            f" {attempt}. {word:<10} → {response:<5} ({before} → {after} left, {before - after} cut)"
        )
    print("-" * 40)
    print(f" Total guesses: {len(guess_history)}")


def rotate_log_if_monday():
    today = datetime.now()
    log_path = Path(LOG_FILE)
    if today.weekday() == 0 and log_path.exists():  # Monday = 0
        rotated_name = f"wordle_solver_{today.strftime('%Y-%m-%d')}.log"
        log_path.rename(rotated_name)
        log_event(f"Log rotated to {rotated_name}")


def log_event(message: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log:
        log.write(f"[{now}] {message}\n")


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


def input_word(WORDS, letter_freq, used_words=None):
    while True:
        word = input("Input the word you entered> ").lower()

        if used_words and word in used_words:
            print("⚠️  Warning: This word is a known past NYT solution.")

        if word.startswith("+"):
            try:
                n = int(word[1:]) if word[1:] else 10
            except ValueError:
                n = 10
            return f"CMD_NEXT_{n}"

        if word.startswith("-"):
            try:
                n = int(word[1:]) if word[1:] else 10
            except ValueError:
                n = 10
            return f"CMD_PREV_{n}"

        if word == "^":
            return "CMD_RESET"

        if word in {"q", "quit"}:
            return "CMD_QUIT"

        if word in {"r", "restart"}:
            return "CMD_RESTART"

        if word in {"?", "help"}:
            return "CMD_HELP"

        if word == "!":
            return "CMD_HISTORY"

        if len(word) == WORD_LENGTH and word in WORDS:
            print(f"{word:<10} | {calculate_word_commonality(word, letter_freq):<5.2}")
            break

    return word


def input_response():
    print("Color-coded reply:")
    print("G for Green | Y for Yellow | ? for Gray")

    while True:
        raw = input("Response> ")
        response = raw.strip().upper().replace(".", "?")

        if len(response) == WORD_LENGTH and set(response) <= {"G", "Y", "?"}:
            return response
        else:
            print(f"Error - invalid answer {response}")


def match_word_vector(word, word_vector):
    assert len(word) == len(word_vector)
    for letter, v_letter in zip(word, word_vector):
        if letter not in v_letter:
            return False
    return True


def match(word_vector, possible_words):
    return [word for word in possible_words if match_word_vector(word, word_vector)]


def solve():
    import sys

    rotate_log_if_monday()

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

    word_vector = [set(string.ascii_lowercase) for _ in range(WORD_LENGTH)]

    offset_start = 0
    window_size = 10

    attempt = 1
    override_attempts = 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    args = " ".join(sys.argv[1:])

    log_event("# Session started")
    log_event(f"# Args: {args or 'none'}")

    while attempt <= (ALLOWED_ATTEMPTS + override_attempts):
        print(f"Attempt {attempt} with {len(possible_words)} possible words")

        ranked_words = sort_by_word_commonality(possible_words, LETTER_FREQUENCY)

        print("+ / +n more | - / -n back | ^ reset ")

        display_word_table(
            ranked_words[offset_start : offset_start + window_size],
            USED_WORDS,
            start_index=offset_start,
        )

        words_before = len(possible_words)

        word = input_word(WORDS, LETTER_FREQUENCY, USED_WORDS)

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
                for attempt, word, response, before, after in guess_history:
                    print(
                        f" {attempt}. {word:<10} → {response:<5} ({before} → {after} left, {before - after} cut)"
                    )
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
            print("  ? / help  Show this help screen")
            print("After 6 guesses, you will be asked if you'd like to continue.")
            continue

        response = input_response()

        if attempt > ALLOWED_ATTEMPTS:
            print(f"\n❌ You've reached the {ALLOWED_ATTEMPTS}-guess limit.")
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

        for idx, letter in enumerate(response):
            if letter == "G":
                word_vector[idx] = {word[idx]}
            elif letter == "Y":
                # Filter down to words that contain the letter but not at this position
                possible_words = [
                    w for w in possible_words if word[idx] in w and w[idx] != word[idx]
                ]
                try:
                    word_vector[idx].remove(word[idx])
                except KeyError:
                    pass

            elif letter == "?":
                # TODO: Improve logic to handle duplicate letters correctly.
                # This removes all instances of a gray letter, which is wrong if that letter also got a green/yellow elsewhere in the same guess.

                for vector in word_vector:
                    try:
                        vector.remove(word[idx])
                    except KeyError:
                        pass

        possible_words = match(word_vector, possible_words)

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

        if not possible_words:
            print("\n❌ No possible words remaining based on given feedback.")
            print("❌ Double-check your inputs. Restart with 'r'.\n")

            log_event("# Session ended (no words remaining)")
            log_game_summary(guess_history)
            print_game_summary(guess_history)

            continue

        print(word_vector)


if __name__ == "__main__":
    solve()

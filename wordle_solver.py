# solver


import string

from pathlib import Path

from collections import Counter
from itertools import chain

import operator

from pathlib import Path

from datetime import datetime, timedelta

import urllib.request

# Configuration
WORD_LIST_URL = "https://raw.githubusercontent.com/tabatkins/wordle-list/main/words"
USED_LIST_URL = (
    "https://raw.githubusercontent.com/tabatkins/wordle-list/main/solutions.txt"
)

WORD_LIST_FILE = "5_letter_words.txt"
USED_LIST_FILE = "nyt_used_words.txt"

MAX_AGE_DAYS = 7

ALLOWABLE_CHARACTERS = set(string.ascii_letters)
ALLOWED_ATTEMPTS = 6
WORD_LENGTH = 5


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
    except Exception as e:
        print(f"⚠️  Failed to download {url}: {e}")
        print(f"⚠️  Proceeding without refreshing {destination}")


def refresh_file_if_needed(file_path: str, url: str, force: bool = False):
    if force or file_older_than(file_path, MAX_AGE_DAYS):
        download_file(url, file_path)


def refresh_word_lists(force_wordlist=False, force_used=False):
    refresh_file_if_needed(WORD_LIST_FILE, WORD_LIST_URL, force_wordlist)
    refresh_file_if_needed(USED_LIST_FILE, USED_LIST_URL, force_used)


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


def display_word_table(word_commonalities, used_words=None):
    for word, freq in word_commonalities:
        mark = " 🔁" if used_words and word in used_words else ""
        print(f"{word:<10} | {freq:<5.2}{mark}")


def input_word(WORDS, letter_freq, used_words=None):
    while True:
        word = input("Input the word you entered> ").lower()

        if used_words and word in used_words:
            print("⚠️  Warning: This word is a known past NYT solution.")

        print(word, len(word), word in WORDS)

        if len(word) == WORD_LENGTH and word in WORDS:
            print(f"{word:<10} | {calculate_word_commonality(word, letter_freq):<5.2}")
            break
    return word


def input_response():
    print("Type the color-coded reply from Wordle:")
    print("  G for Green")
    print("  Y for Yellow")
    print("  ? for Gray")
    while True:
        response = input("Response from Wordle> ")
        response = response.upper()
        if len(response) == WORD_LENGTH and set(response) <= {"G", "Y", "?"}:
            if response == "GGGGG":
                print("Seems you are done!")
                exit()
            else:
                break
        else:
            print(f"Error - invalid answer {response}")
    return response


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

    force_refresh = "--refresh" in sys.argv
    force_used = "--refresh-used" in sys.argv

    refresh_word_lists(force_refresh, force_used)
    WORDS = load_words()

    LETTER_COUNTER = Counter(chain.from_iterable(WORDS))

    LETTER_FREQUENCY = {
        character: value / LETTER_COUNTER.total()
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

    possible_words = WORDS.copy()

    word_vector = [set(string.ascii_lowercase) for _ in range(WORD_LENGTH)]

    for attempt in range(1, ALLOWED_ATTEMPTS + 1):
        print(f"Attempt {attempt} with {len(possible_words)} possible words")

        ranked_words = sort_by_word_commonality(possible_words, LETTER_FREQUENCY)
        top_guess = ranked_words[0]
        print(f"Suggested guess: {top_guess[0]}  (score: {top_guess[1]:.2f})")

        display_word_table(ranked_words[:10])

        word = input_word(WORDS, LETTER_FREQUENCY, USED_WORDS)

        response = input_response()
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
        print(word_vector)


if __name__ == "__main__":
    solve()

# Wordle Solver

## Overview

This terminal-based Wordle solver:
- Plays NYT Hard Mode: suggests only Hard Mode legal guesses, ranked by how
  well they split the remaining words, and rejects guesses Hard Mode wouldn't allow
- Flags past NYT answers (scraped from FiveForks) and your own past solves
- Light enough for slow devices (e.g. iSH on iPhone): heavy work is precomputed
  on a desktop with `wordle_lab.py` and committed as small table files
- Runs cleanly under WSL with dynamic word list fetching

## Requirements

- Python 3.9+
- Internet access (for list fetching)
- Virtual environment recommended

## Installation

To set up the project locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This creates a local virtual environment named .venv and installs all required dependencies.

Note: .venv/ is excluded from version control (see .gitignore).

## Run the Solver

```bash
python3 wordle_solver.py
```

- Logs are written next to the script, one file per week (Monday start):
  `logs/YYYY/MM/wordle_solver_YYYY-MM-DD.log`. The folder follows the
  Monday's month, so a week that crosses into a new month stays in one file.

### Entering Guesses

At the "Input the word you entered" prompt, either:

- Enter the word, then the response at the `Response>` prompt, or
- Enter both at once, separated by `/` or a space: `dress/?GGG?` or `dress ?GGG?`

Guesses that break Hard Mode (e.g. dropping a green letter) are rejected with
the reason, since the NYT game wouldn't accept them either.

### Runtime Controls

At the "Input the word you entered" prompt:

- `+` or `+n`     : Show next suggestions (in batches)
- `-` or `-n`     : Show previous suggestions
- `^`             : Reset to top of suggestion list
- `q` / `quit`    : Quit the game
- `r` / `restart` : Start a new game (word lists are not re-fetched)
- `!` / `history` : Show past guesses and how many words remained after each
- `?` / `help`    : Show commands

- You may enter '.' instead of '?' when entering gray feedback (e.g., G.Y??)

- If no words remain, you'll be told to check your inputs (`!`) or restart (`r`);
  the game stays open until you quit or restart

- After 6 guesses, you'll be prompted to continue manually

### Optional CLI Flags

- `--refresh` : Force-refresh the valid word list
- `--refresh-used` : Force-refresh the list of past NYT answers

### Environment

- `WORDLE_RANK_LIMIT` : Cap on live ranking work (default 100000). Lower it if
  turns feel slow on your device; `python3 wordle_lab.py bench` suggests a value.

## Project Structure

- `wordle_solver.py`     — Main solver logic
- `wordle_lab.py`        — Offline tools: simulate strategies, build tables, bench
- `precomputed/`         — Second-guess tables (committed; e.g. `second_guess_arose.json`)
- `.gitignore`           — Ignores dynamic lists and logs
- `README.md`            — This file
- `TODO.md`              — Feature roadmap
- `LICENSE`              — MIT license
- `tests/`               — Unit tests (`python3 -m unittest discover -s tests`)

### Generated on First Run

Created next to the script (ignored by Git), no matter which folder you run from:

- `data/valid_word_list.txt` — Fetched valid guess list (from tabatkins)
- `data/used_word_list.txt`  — Scraped list of past NYT answers (from FiveForks)
- `logs/`                    — Weekly game logs

Lists left in the current folder by older versions are moved into `data/` on first run.

## Word List Handling

- Word lists are fetched automatically if missing or stale (every 7 days)
- If a fetch fails, the solver continues with the existing local copy
  (the past-answers scrape retries once without SSL verification first)
- Lists are ignored by Git
- Past answers are flagged in suggestions (not removed):
  - ✅ — you solved it (any `GGGGG` guess in your `logs/`)
  - 🔁 — other past NYT answer (from FiveForks)
- Your own solves fill the gap between weekly scrapes, and are re-read at each restart
- The scraper identifies itself as `wordle-solver` with a link to this repo
  (fiveforks.com's robots.txt allows `/wordle/`)

## Solver Features

- Filters candidates with feedback-aware matching:
  - Green: letter in correct position
  - Yellow: letter in word but in a different position
  - Gray: letter not in word or used too many times
  - Supports duplicate letter disambiguation correctly (e.g., `undid`, `error`)
- Ranks next guesses by **expected words left**: each Hard Mode legal guess
  groups the candidates by the feedback it would produce; smaller groups are
  better. Ties prefer words that could be the answer. `·` marks guesses that
  can't be the answer; they're listed only when they split better than every
  possible answer, so the list is the remaining answers plus a few such guesses.
- Below the table: `Showing 1-10 of 14: 12 possible answers, 2 other guesses (·)`
- Turn 1 (no feedback yet) ranks by letter frequency (e.g., AEROS, AROSE, SOARE)
- Turn 2 after a known opener uses a precomputed table (instant on slow devices)
- Later turns rank live, capped by `WORDLE_RANK_LIMIT`; over the cap it falls
  back to letter frequency

## Offline Tools (`wordle_lab.py`)

Run on a desktop; only `bench` is meant for the phone.

```bash
python3 wordle_lab.py simulate --strategy bucket      # play all past answers
python3 wordle_lab.py simulate --strategy frequency   # old ranking, for comparison
python3 wordle_lab.py build-table --opener arose      # ~2 min; commit the result
python3 wordle_lab.py bench                           # time ranking on this device
```

Simulation over 1942 past answers, opener `arose`, Hard Mode:

| Ranking              | Avg guesses | Over 6 guesses |
|----------------------|-------------|----------------|
| Letter frequency     | 4.69        | 182            |
| Expected words left  | 4.39        | 98             |

Most remaining failures are "trap" patterns like `_ATER` or `_ITCH` where Hard
Mode forces one guess per word, made worse by obscure words in the guess list.

## Roadmap

See [`TODO.md`](./TODO.md) for planned enhancements and ideas.

## Credits

- Valid word list: [tabatkins/wordle-list](https://github.com/tabatkins/wordle-list) (MIT)
- Past answers: [FiveForks](https://www.fiveforks.com/wordle/)
- Wordle is a trademark of The New York Times Company. This project is not
  affiliated with or endorsed by the NYT.

## License

MIT — see [`LICENSE`](./LICENSE).
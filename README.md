# Wordle Solver

## Overview

This terminal-based Wordle solver:
- Suggests only words consistent with all feedback so far (Hard Mode compatible)
- Flags past NYT answers (scraped from FiveForks)
- Prioritizes statistical optimization to lower average solve count
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

## Project Structure

- `wordle_solver.py`     — Main solver logic
- `.gitignore`           — Ignores dynamic lists and logs
- `README.md`            — This file
- `TODO.md`              — Feature roadmap
- `tests/`               — Unit tests (`python3 -m unittest discover -s tests`)

### Generated on First Run

- `valid_word_list.txt`  — Fetched valid guess list (from tabatkins)
- `used_word_list.txt`   — Scraped list of past NYT answers (from FiveForks)

## Word List Handling

- Word lists are fetched automatically if missing or stale (every 7 days)
- If a fetch fails, the solver continues with the existing local copy
  (the past-answers scrape retries once without SSL verification first)
- Lists are ignored by Git
- Past NYT answers are marked with 🔁 in suggestions (not removed)

## Solver Features

- Suggests high-frequency eliminators (e.g., AEROS, AROSE, SOARE)
- Applies hard mode logic using feedback-aware filtering:
  - Green: letter in correct position
  - Yellow: letter in word but in a different position
  - Gray: letter not in word or used too many times
  - Supports duplicate letter disambiguation correctly (e.g., `undid`, `error`)
- Suggests next guess based on frequency analysis

## Roadmap

See [`TODO.md`](./TODO.md) for planned enhancements and ideas.
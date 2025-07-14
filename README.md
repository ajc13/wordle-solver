# Wordle Solver

## Overview

This terminal-based Wordle solver:
- Operates in Hard Mode
- Avoids past NYT answers (scraped from FiveForks)
- Prioritizes statistical optimization to lower average solve count
- Runs cleanly under WSL with dynamic word list fetching

## Requirements

- Python 3.x
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

- A new log file is started each Monday (previous logs archived)

### Runtime Controls

At the "Input the word you entered" prompt:

- `+` or `+n`     : Show next suggestions (in batches)
- `-` or `-n`     : Show previous suggestions
- `^`             : Reset to top of suggestion list
- `q` / `quit`    : Quit the game
- `r` / `restart` : Restart the current solver session
- `!` / `history` : Show past guesses and how many words remained after each
- `?` / `help`    : Show commands

- You may enter '.' instead of '?' when entering gray feedback (e.g., G.Y??)

- If no words remain due to feedback, you'll be prompted to restart

- After 6 guesses, you'll be prompted to continue manually

### Optional CLI Flags

- `--refresh` : Force-refresh the valid word list
- `--refresh-used` : Force-refresh the list of past NYT answers

## Project Structure

- `wordle_solver.py`     — Main solver logic
- `.gitignore`           — Ignores dynamic lists and logs
- `README.md`            — This file
- `TODO.md`              — Feature roadmap

### Generated on First Run

- `valid_word_list.txt`  — Fetched valid guess list (from tabatkins)
- `used_word_list.txt`   — Scraped list of past NYT answers (from FiveForks)

## Word List Handling

- Word lists are fetched automatically if missing or stale (evry 7 days)
- Lists are ignored by Git
- Used answers are excluded from suggestions when available

## Solver Features

- Suggests high-frequency eliminators (e.g., SOARE, AUDIO)
- Applies hard mode logic using feedback-aware filtering:
  - Green: letter in correct position
  - Yellow: letter in word but in a different position
  - Gray: letter not in word or used too many times
  - Supports duplicate letter disambiguation correctly (e.g., `undid`, `error`)
- Suggests next guess based on frequency analysis

## Roadmap

See [`TODO.md`](./TODO.md) for planned enhancements and ideas.
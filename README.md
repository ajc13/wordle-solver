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

```bash
pip install -r requirements.txt
```

## Run the Solver

```bash
python3 wordle_solver.py
```

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

- Word lists are fetched automatically if missing or stale
- Lists are ignored by Git
- Used answers are excluded from suggestions when available

## Solver Features

- Suggests high-frequency eliminators (e.g., SOARE, AUDIO)
- Applies hard mode logic:
  - Green: letter in correct position (must be reused)
  - Yellow: letter in word but new position (must be used elsewhere)
  - Grey: letter excluded (unless known duplicate)
- Suggests next guess based on frequency analysis

## Roadmap

See [`TODO.md`](./TODO.md) for planned enhancements and ideas.
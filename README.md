# Wordle Solver (WSL-Optimized)

## This project provides a terminal-based Wordle solver that:
- Works in Hard Mode
- Avoids past NYT answers
- Prioritizes statistical optimization to reduce average solve count
- Runs cleanly in a WSL environment with dynamic word list fetching

## Requirements:
- Python 3.x
- Internet access (for word list download)

## Install dependencies (if needed):
pip install -r requirements.txt

## Project Structure:
- wordle_solver.py     : Main solver logic
- nyt-answers.txt      : Fetched answer list (auto-created)
- .gitignore           : Ignores word lists and logs
- README.md            : This file
- TODO.md              : Task and planning list

## Word List Management:
- Static word lists are not tracked in Git
- nyt-answers.txt is pulled from FiveForks.com and used to filter past solutions
- If not present, it will be auto-fetched

## Run solver:
python3 wordle_solver.py

## Features:
- First guess uses optimized eliminators (SOARE, AUDIO, etc.)
- Solver respects Hard Mode logic (green locks, yellow repositions, grey eliminates)
- Answers are filtered against official NYT list, if retrieved  (no repeats)

## Roadmap

See [`TODO`](./TODO.md) for planned features and enhancements.

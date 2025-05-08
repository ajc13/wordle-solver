# Wordle Solver

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
- 5_letter_words.txt   : Fetched valid word list (tabatkins)
- nyt-answers.txt      : Fetched past answer list (fiveforks)
- .gitignore           : Ignores word lists and logs
- README.md            : This file
- TODO.md              : Task and planning list

## Word List Management:
- Static word lists are not tracked in Git
- Lists are pulled/updated weekely
- If not present, they will be auto-fetched

## Run solver:
python3 wordle_solver.py

## Features:
- First guess offers optimized eliminators (SOARE, AUDIO, etc.)
- Solver respects Hard Mode logic (green locks, yellow repositions, grey eliminates)
- Answers are filtered against past answer list, if retrieved  (no repeats)

## Roadmap

See [\`TODO\`](./TODO.md) for planned features and enhancements.
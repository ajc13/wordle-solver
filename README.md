# Wordle Solver

A terminal-based Wordle solver written in Python. Uses letter frequency analysis and interactive feedback to narrow down guesses and help solve puzzles efficiently.

## Features

- Supports interactive input (`G`, `Y`, `?` for feedback)
- Scores guesses by letter frequency
- Loads from a curated 5-letter word list
- Compatible with Python 3 (Linux, macOS, Pythonista on iOS)

## Requirements

- Python 3.6+
- `5_letter_words` file in the same directory

## Usage

```bash
python3 wordle_solver_02.py
```

You will be prompted to:

1. Enter your guessed word  
2. Enter Wordle's feedback using:  
   - `G` for green  
   - `Y` for yellow  
   - `?` for gray  

## Refreshing Word List

To fetch the latest word list from a reliable source:

```bash
curl -o 5_letter_words https://raw.githubusercontent.com/tabatkins/wordle-list/main/words
```

## Roadmap

See [`TODO`](./TODO.md) for planned features and enhancements.

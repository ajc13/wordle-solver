# Changelog

## [1.0.0] – 2025-05-20
### Added
- Structured logging to `wordle_solver.log`
- Weekly log rotation on Mondays
- In-game `!` / `history` command
- End-of-game summary (printed + logged)
- Paging, restart, quit, help commands
- Graceful handling of empty guess pool

### Changed
- Replaced for-loop with while-loop for attempt control
- Switched to centralized logging function

## [1.0.1] – 2025-05-21
### Added
- Per-guess elimination tracking (before → after word count)
- Improved log format with cut counts
- Summary block now shows how many words were removed by each guess

## [1.0.2] – 2025-05-21
### Fix
- Fix: replace Counter.total() with sum(...) for Python 3.9 compatibility

## [1.0.3] – 2025-07-14
### Fix
- Corrected core filtering logic to fix elimination of valid words (e.g., `undid`)
- Replaced position-set filtering (`word_vector`) with full feedback-aware letter count matching
- Added `word_matches_feedback()` and `filter_word_list()` functions
- Removed legacy `match()` and `word_vector` logic

## [1.1.0] – 2026-11-07
### Added
- Enter guess and response in one line: `dress/?GGG?` or `dress ?GGG?`
- Weekly log files at `logs/YYYY/MM/wordle_solver_<monday>.log` (next to the script)
- Unit tests in `tests/` (filter fuzzed against a reference Wordle scorer, 2026-10-20 regression)
- Error message when a guess is not in the word list
- `history` accepted as an alias for `!`

### Fix
- Gray feedback now rejects candidates with that letter in the same position
- Viewing history no longer resets the attempt counter
- 6-guess "continue anyway?" prompt now actually appears (previously exited silently)

### Removed
- Monday log rotation (could overwrite the previous week's archive)

## [1.1.1] – 2026-11-07
### Fix
- Scraper no longer crashes at startup if the SSL-disabled retry also fails
- "No words remaining" no longer logs a session end and summary while the game continues
- `restart` starts a new game in a loop instead of recursing into `solve()`; word lists are no longer re-fetched

### Added
- Session flow tests (`tests/test_session.py`)

### Docs
- README: corrected Hard Mode and past-answer claims, Python 3.9+, restart and fetch-failure behavior, example openers

## [Unreleased]
### Changed
- Scraper sends an honest `wordle-solver` User-Agent (with repo link) instead of impersonating Chrome; verified against fiveforks.com

### Added
- MIT `LICENSE`
- README credits (word list, past answers, Wordle trademark notice) and license section
- Test that the scraper sends `SCRAPER_USER_AGENT`

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

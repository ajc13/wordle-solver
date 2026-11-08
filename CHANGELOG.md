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

## [1.1.2] – 2026-11-07
### Changed
- Scraper sends an honest `wordle-solver` User-Agent (with repo link) instead of impersonating Chrome; verified against fiveforks.com

### Added
- MIT `LICENSE`
- README credits (word list, past answers, Wordle trademark notice) and license section
- Test that the scraper sends `SCRAPER_USER_AGENT`

## [1.2.0] – 2026-11-07
### Added
- Your own solves (`GGGGG` lines in `logs/`) are flagged ✅ in suggestions, with a "You've solved this word before" warning; scraped past answers keep 🔁
- Own solves are re-read at each restart, so a just-finished game counts immediately
- Tests for data dir, legacy migration and own-solve parsing (`tests/test_data.py`)

### Changed
- Word lists now live in `data/` next to the script instead of the current directory; lists left in the current directory by older versions are moved there on first run

## [Unreleased]
### Added
- Hard Mode ranking by expected words left: each legal guess groups the candidates by the feedback it would produce; ties prefer possible answers. `·` marks guesses that can't be the answer
- `wordle_lab.py` offline tools: `simulate` (play all past answers, report averages and failures), `build-table`, and `bench` (time ranking on the phone)
- Precomputed second-guess table for opener `arose` (`precomputed/second_guess_arose.json`, 166 patterns); turn 2 is a lookup
- `WORDLE_RANK_LIMIT` caps live ranking work for slow devices; over the cap, ranking falls back to letter frequency
- Answer likelihood weighting from English word frequency (`precomputed/word_weights.json`, from wordfreq, CC BY-SA 4.0): obscure words count 0.01, common words ~1. Prompt shows `(~N likely)`; obscure candidates are marked `rare`
- `wordle_lab.py build-weights`; `simulate --answers odd|even`, `--center/--scale/--no-weights`, `--table-dir`; `build-table --out-dir`
- Tests for scoring, Hard Mode rules, ranking, weights, tables and the simulator (`tests/test_ranking.py`)

### Changed
- Guesses that break Hard Mode are rejected with the reason (the NYT game wouldn't accept them)
- Ranking is computed once per turn instead of on every paging command
- Suggestion list holds the possible answers plus only those other guesses that split better than every answer (was every Hard Mode legal word, e.g. 4159 entries for 31 answers)
- Prompt shows `N possible answers left`; a line under the table shows the page position and the answer / other-guess counts
- Paging past either end says `(end of list)` / `(top of list)`

### Results
- Simulated over 1942 past answers (opener `arose`, Hard Mode): average 4.69 → 4.39 guesses (bucket ranking) → 3.82 (weighted); games over 6 guesses 182 → 98 → 19
- Weighting tuned on the odd-numbered answers; held-out even half: 4.40 → 3.84 avg, 52 → 11 over 6

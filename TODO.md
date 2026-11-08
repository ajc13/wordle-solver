# TODO

## Core
- [x] Static word lists removed from version control
- [x] .gitignore updated for dynamic lists and logs
- [x] Answer + valid word list fetch logic integrated into solver
- [x] SSL fallback for scraping
- [x] FiveForks parser adjusted for new layout (#alphalist div)
- [x] Word lists stored in `data/` next to the script (legacy files migrated)
- [x] Own solves (`GGGGG` in logs) flagged ✅ alongside scraped past answers 🔁

## Optimization (Hard Mode: revealed hints must be reused)
- [x] Strategy shift to improve average solve count
- [x] Rank by feedback-bucket size (expected remaining words) over hard-mode-legal guesses (4.69 → 4.39 avg)
- [x] Precomputed second-guess table for `arose` (`precomputed/`); turn 2 instant on iSH
- [x] Reject entered guesses that break Hard Mode, with the reason
- [x] Simulation harness over past answers (`wordle_lab.py simulate`)
- [ ] Run `wordle_lab.py bench` on iSH; tune default `WORDLE_RANK_LIMIT` if turns are slow
- [x] Weight by answer likelihood from word frequency (wordfreq); 4.39 → 3.82 avg,
      tuned on odd past answers, checked on even
- [ ] Names count as common in wordfreq (danny, jerry, tania); down-weight words
      mostly seen capitalized, or filter against a dictionary
- [ ] Turn-1 ranking still by letter frequency
- [ ] Cache opener ranking for turn 1 (full scoring ~19 min) if a non-arose opener is wanted

## Testing
- [x] Add unit test coverage for filtering logic (`tests/test_filter.py`)
- [x] Validate green/yellow/grey parsing logic and edge cases (fuzzed against reference scorer)
- [x] Session flow tests: quit, restart, no words remaining, scrape failure (`tests/test_session.py`)
- [x] Data dir, legacy migration, own-solve parsing tests (`tests/test_data.py`)
- [x] Ranking, Hard Mode, table and simulator tests (`tests/test_ranking.py`)
- [x] Test harness for simulated Wordle rounds (`wordle_lab.py simulate`)
- [ ] CI: run tests on Python 3.9 and latest (GitHub Actions)

## Docs
- [x] Add virtualenv setup instructions to README under "Installation"
- [x] Rewrite README for current structure
- [x] Add CLI flag documentation to README

## CLI / UX
- [x] Add runtime paging with `+n`, `-n`, and `^`
- [x] Add interactive quit (`q`) and restart (`r`) commands
- [x] Support `.` as alias for gray (`?`) in response input
- [x] Add `?` or `help` in input prompt to print runtime command help
- [x] Add `+ / -` commands to README examples for paging navigation
- [x] Handle edge case: no possible words remaining — advise restart
- [x] Weekly log files under `logs/YYYY/MM/` (replaces Monday rotation)
- [x] Accept `word/response` or `word response` in one entry
- [x] Add structured logging for guesses, responses, and metadata
- [x] After 6 guesses, ask user if they want to continue instead of hard exit
- [x] Log timestamp on each entry
- [x] Log number of words remaining on each guess
- [x] Use helper function for logging to centralize logic
- [x] Show how many words were eliminated by each guess in history and summary

## Nice-to-Have
- [x] Quit and restart options
- [x] Add `!` for history, status so far
- [x] Display word count remaining in history output
- [x] End of game summary

## Known Issues
- [x] SSL-disabled retry in scraper is unguarded; a second failure crashes startup
- [x] "No words remaining" logs a session end but the session continues (double summary)
- [x] `restart` recurses into `solve()` and re-runs list refresh

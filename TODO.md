# TODO

## Core
- [x] Static word lists removed from version control
- [x] .gitignore updated for dynamic lists and logs
- [x] Answer + valid word list fetch logic integrated into solver
- [x] SSL fallback for scraping
- [x] FiveForks parser adjusted for new layout (#alphalist div)

## Optimization
- [x] Strategy shift to improve average solve count
- [ ] Score candidates by entropy or coverage value
- [ ] Support wordlist weighting or adaptive filtering

## Testing
- [x] Add unit test coverage for filtering logic (`tests/test_filter.py`)
- [x] Validate green/yellow/grey parsing logic and edge cases (fuzzed against reference scorer)
- [ ] Add test harness for simulated Wordle rounds or regression

## Docs
- [x] Add virtualenv setup instructions to README under "Getting Started"
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
- [ ] SSL-disabled retry in scraper is unguarded; a second failure crashes startup
- [ ] "No words remaining" logs a session end but the session continues (double summary)
- [ ] `restart` recurses into `solve()` and re-runs list refresh

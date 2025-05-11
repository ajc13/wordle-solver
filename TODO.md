# TODO

## Core
- [x] Static word lists removed from version control
- [x] .gitignore updated for dynamic lists and logs
- [x] Answer + valid word list fetch logic integrated into solver
- [x] SSL fallback for scraping
- [x] FiveForks parser adjusted for new layout (#alphalist div)

## Optimization
- [x] Strategy shift to improve average solve count
- [ ] Implement second-guess fallback suggestions
- [ ] Score candidates by entropy or coverage value
- [ ] Support wordlist weighting or adaptive filtering

## Testing
- [ ] Add unit test coverage for filtering logic
- [ ] Validate green/yellow/grey parsing logic and edge cases
- [ ] Add test harness for simulated Wordle rounds or regression

## Docs
- [x] Add virtualenv setup instructions to README under "Getting Started"
- [x] Rewrite README for current structure
- [x] Add CLI flag documentation to README
- [ ] Add example walkthrough (screenshots or sample log)
- [ ] Add FAQ or strategy notes

## CLI / UX
- [x] Add runtime paging with `+n`, `-n`, and `^`
- [x] Add interactive quit (`q`) and restart (`r`) commands
- [x] Support `.` as alias for gray (`?`) in response input
- [ ] Add log rotation weekly (e.g., Mondays)
- [ ] Add structured logging for guesses, responses, and metadata

## Nice-to-Have
- [ ] Solve summary output for each run
- [ ] Replay past puzzles or simulate old answers
- [ ] Interactive mode (Y/n prompts, hint reveal)
- [ ] Quit and restart options
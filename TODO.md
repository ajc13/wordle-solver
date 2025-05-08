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
- [x] Rewrite README for current structure
- [x] Add CLI flag documentation to README
- [ ] Add example walkthrough (screenshots or sample log)
- [ ] Add FAQ or strategy notes

## CLI / UX
- [ ] Add `--easy` flag to bypass hard mode logic
- [ ] Add `--log` option to persist guess history
- [ ] Add `--color` output (e.g., termcolor or rich)

## Nice-to-Have
- [ ] Solve summary output for each run
- [ ] Replay past puzzles or simulate old answers
- [ ] Interactive mode (Y/n prompts, hint reveal)
- [ ] Quit and restart options
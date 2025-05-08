# TODO

## Core:
- [x] Static word lists removed from version control
- [x] .gitignore updated for dynamic lists and logs
- [x] Answer fetch logic integrated into `wordle_solver.py`
- [ ] Add "solved.log" to track completed games
- [ ] Prevent resubmitting known past solutions
- [ ] Option to override or bypass past-answer check

## Optimization:
- [x] Strategy shift to improve average solve count
- [ ] Implement second-guess fallback suggestions
- [ ] Score candidates by entropy or coverage value
- [ ] Support wordlist weighting or adaptive filtering

## Testing:
- [ ] Add unit test coverage for filtering logic
- [ ] Validate green/yellow/grey parsing edge cases
- [ ] Add test harness for example puzzles or regression cases

## Docs:
- [x] Rewrite README for current architecture
- [ ] Add CLI usage help to `wordle_solver.py`
- [ ] Add example walkthrough with screenshots or game logs
- [ ] Add FAQ with strategy notes

## CLI / UX:
- [ ] Add `--easy` flag to disable hard mode logic
- [ ] Add `--log` option to persist guess history
- [ ] Add `--color` output support (via termcolor or rich)
- [ ] Add `--day` or `--streak` flag to seed context
- [ ] Export guess history to `CSV`

## Nice-to-Have:
- [ ] Daily streak and average tracker
- [ ] Solve summary output for each run
- [ ] Option to replay past puzzles locally
- [ ] Interactive mode (Y/n prompts, hint reveal)
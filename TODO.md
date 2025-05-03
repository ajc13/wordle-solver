# TODO

## Word List Management

- [ ] Script to refresh `5_letter_words` from tabatkins source
- [ ] Auto-backup previous word list before overwriting
- [ ] Parse and extract previously used NYT solutions into `nyt_used_words.txt`
- [ ] Optionally exclude or de-rank used solutions

## Solver Improvements

- [ ] Fix yellow logic to ensure letters aren't at the same index
- [ ] Handle duplicate letters more accurately
- [ ] Support non-interactive mode (preloaded guesses and responses)
- [ ] Add score weight tuning based on letter position frequency

## CLI Features

- [ ] Add `--exclude-used` flag
- [ ] Add `--max-guesses` limit override
- [ ] Add `--wordlist <file>` option

## Cross-Platform

- [ ] Validate clean usage in Pythonista
- [ ] Document setup for GitHub-to-iOS flow

### Improve Scoring Strategy: Prioritize Information Gain

- [ ] Refactor `calculate_word_commonality()` to use **information gain** logic
  - Estimate how much each guess would **partition** the remaining word pool
  - Score higher if a guess would eliminate more words *on average*, even if it's not a valid answer
- [ ] Optionally use **per-letter position frequency**
  - Some letters are more common at the start or end
- [ ] Consider **dual-mode scoring**:
  - Phase 1: Elimination — high-entropy guesses (e.g. `slate`, `roate`)
  - Phase 2: Precision — guess from narrowed pool
- [ ] Keep current scoring as fallback/simple mode

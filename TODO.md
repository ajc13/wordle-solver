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


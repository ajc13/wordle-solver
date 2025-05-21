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

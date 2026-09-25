# Changelog

All notable changes to Stopwatch Plus are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-09-25

### Added

- Sensor *Last session* per stopwatch (e.g. `sensor.gaming_last_session`): the running time of the last session, kept when the stopwatch goes back to zero by Stop, Reset or auto-stop. Attributes `elapsed_formatted` and `ended_at`; survives restarts.

### Changed

- **Breaking:** the option *Reset automatically for a new session* is now **Stop automatically after inactivity**. When the source stays inactive for the delay, the stopwatch is stopped right away (event `stopped` with source `auto_stop`) instead of being reset at the next start of the source. The next start fires `started`. With a delay of 0, the stopwatch stops as soon as the source becomes inactive. The option keys are now `auto_stop` and `auto_stop_delay`: stopwatches set up with 0.2.0 need the option switched on again.
- The events `stopped` and `reset` report the time and interval count the session reached, instead of 0.

## [0.2.0] - 2026-09-25

### Added

- Device triggers for every event type (*Stopwatch started*, *paused*, *resumed*, *stopped*, *reset* and *Interval reached*), selectable in the automation editor without typing the event name. `trigger.event.data` holds the same values as the event.
- Event entity per stopwatch (e.g. `event.gaming_events`) that reports every stopwatch event with its data as attributes. It makes the events available in Home Assistant's entity-based trigger *Event received* (with the stopwatch as target) and shows them in the logbook.
- Button *Start/Pause* per stopwatch (e.g. `button.gaming_start_pause`): pauses a running stopwatch, otherwise starts or resumes it. Handy for a single dashboard button.
- Button *Stop* and action `stopwatch_plus.stop`: stops the stopwatch and sets it back to zero (status `idle`), with the new event type `stopped`.
- Icons for all buttons, sensors, the event entity and the actions.

### Changed

- **Breaking:** *Reset* (button and action `stopwatch_plus.reset`) no longer stops a running stopwatch: it sets the time back to zero and keeps counting. A paused stopwatch is still stopped. Use the new *Stop* to stop and reset in one step.

## [0.1.0] - 2026-09-24

First pre-release.

### Added

- Any number of stopwatches, each set up as its own device via **Add integration → Stopwatch Plus**.
- Elapsed time sensor (duration in whole seconds) with the attribute `elapsed_formatted` (`HH:MM:SS`, from 24 hours on `d.HH:MM:SS`) and the attributes a dashboard card needs to count live.
- Status sensor: `idle`, `running`, `paused`.
- Buttons start, pause and reset, and the actions `stopwatch_plus.start`, `pause`, `reset` and `toggle` (target: entity or device; each stopwatch acts once).
- Event `stopwatch_plus_event` with the types `started`, `paused`, `resumed`, `reset` and `interval`, including elapsed time, interval count and source of the change.
- Interval events based on running time only, configurable with second precision.
- Configurable update interval of the elapsed time sensor (default 60 seconds) to keep the database small.
- Optional source entity: the stopwatch runs in the chosen states, with a grace period for `unavailable` (backdated pause) and an optional auto-reset for new sessions.
- The state survives restarts of Home Assistant; a running stopwatch counts the downtime.
- English and German translations.
- Icon and logo, light and dark (shown from Home Assistant 2026.3 on).

[Unreleased]: https://github.com/bornste/hacs-stopwatch/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/bornste/hacs-stopwatch/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bornste/hacs-stopwatch/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bornste/hacs-stopwatch/releases/tag/v0.1.0

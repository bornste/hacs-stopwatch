# Stopwatch Plus for Home Assistant

> **Status:** in development – not yet ready for use.

A stopwatch integration for [Home Assistant](https://www.home-assistant.io/) that counts **up**, can be paused and resumed, and fires events at configurable intervals of running time. Home Assistant's built-in `timer` only counts down; Stopwatch Plus fills that gap.

## Planned features

- Any number of stopwatches, each set up as its own device (e.g. "Gaming", "Work time").
- Actions `stopwatch_plus.start` (also resumes), `stopwatch_plus.pause`, `stopwatch_plus.reset` and `stopwatch_plus.toggle`, plus buttons for each stopwatch.
- A duration sensor with the elapsed time, and a status sensor (`idle`, `running`, `paused`).
- Optional binding to a source entity: the stopwatch runs while that entity is in one of the chosen states (e.g. `media_player.xbox` is `playing`) and pauses otherwise.
- Interval events based on running time only (pauses do not count), available as a device trigger in the automation editor – for example to announce "You have been playing for 60 minutes".
- State survives Home Assistant restarts.
- Configurable sensor update interval to keep the database small, with a bundled dashboard card that counts live in the browser.
- English and German translations.

## Why the domain is `stopwatch_plus`

Every integration in Home Assistant has a unique internal name, the *domain*. It appears in action names such as `stopwatch_plus.start` and cannot easily be changed later without breaking users' automations.

The obvious domain would be `stopwatch`. It is deliberately **not** used: if Home Assistant ever ships a built-in stopwatch, it would almost certainly use the domain `stopwatch`. A custom integration with the same domain would then override the built-in one, and users could not run both side by side. Using `stopwatch_plus` rules out that collision from the start, while the "plus" reflects the extra features beyond a plain stopwatch.

## Installation

Coming soon via [HACS](https://hacs.xyz/).

## License

[MIT](LICENSE)

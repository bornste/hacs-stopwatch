<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/custom_components/stopwatch_plus/brand/dark_logo@2x.png">
    <img alt="Stopwatch Plus" src="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/custom_components/stopwatch_plus/brand/logo@2x.png" width="420">
  </picture>
</p>

# Stopwatch Plus for Home Assistant

The stopwatch with the plus – in case Home Assistant adds its own one day.

[![Tests](https://img.shields.io/github/actions/workflow/status/bornste/hacs-stopwatch/tests.yml?branch=main&label=Tests&logo=github&style=for-the-badge)](https://github.com/bornste/hacs-stopwatch/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/bornste/hacs-stopwatch/validate.yml?branch=main&label=Validate&logo=github&style=for-the-badge)](https://github.com/bornste/hacs-stopwatch/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/bornste/hacs-stopwatch?include_prereleases&sort=semver&style=for-the-badge)](https://github.com/bornste/hacs-stopwatch/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange?style=for-the-badge)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fbornste%2Fhacs-stopwatch%2Fmain%2Fhacs.json&query=%24.homeassistant&label=Home%20Assistant&suffix=%2B&color=41BDF5&logo=homeassistant&logoColor=white&style=for-the-badge)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/bornste/hacs-stopwatch?style=for-the-badge)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20me-FF5E5B?logo=ko-fi&logoColor=white&style=for-the-badge)](https://ko-fi.com/bornste)

> [!WARNING]
> In development – not yet ready for use.

A stopwatch integration for [Home Assistant](https://www.home-assistant.io/) that counts **up**, can be paused and resumed, and fires events at configurable intervals of running time. Home Assistant's built-in `timer` only counts down; Stopwatch Plus fills that gap.

## Planned features

- Any number of stopwatches, each set up as its own device (e.g. "Gaming", "Work time", "TV on").
- Actions `stopwatch_plus.start` (also resumes), `stopwatch_plus.pause`, `stopwatch_plus.reset` and `stopwatch_plus.toggle`, plus buttons for each stopwatch (Start, Pause, Reset and a combined Start/Pause).
- A duration sensor with the elapsed time, and a status sensor (`idle`, `running`, `paused`).
- Optional binding to a source entity: the stopwatch runs while that entity is in one of the chosen states (e.g. `media_player.xbox` is `playing`) and pauses otherwise.
- Interval events based on running time only (pauses do not count), available as a device trigger in the automation editor – for example to announce "You have been playing for 60 minutes".
- State survives Home Assistant restarts.
- Configurable sensor update interval to keep the database small, with a bundled dashboard card that counts live in the browser.
- English and German translations.

## How it works

A stopwatch is always in one of three states: `idle` (at zero), `running` or `paused`. Every change fires a `stopwatch_plus_event`:

| What happens | From | To | Event `type` |
|---|---|---|---|
| Start | `idle` | `running` | `started` |
| Start (resume) | `paused` | `running` | `resumed` |
| Pause | `running` | `paused` | `paused` |
| Reset | `running` or `paused` | `idle` | `reset` |
| An interval of running time is reached | `running` | `running` | `interval` |

Commands without effect, such as pausing a stopwatch that is not running, do nothing and fire no event. Only running time counts: pauses are not added to the elapsed time, and interval events fire after every full interval of running time.

In the automation editor, the events can be used without typing anything, in two ways:

- **Event received** (entity-based trigger): every stopwatch has an event entity, e.g. `event.gaming_events`. Add a trigger, choose the stopwatch as target and pick *Event received* with the event types you need. The values are in `trigger.to_state.attributes`, e.g. `{{ trigger.to_state.attributes.elapsed_formatted }}`. The events also show up in the logbook and history of that entity.
- **Device trigger** (classic): add a trigger *Device*, choose the stopwatch and pick *Stopwatch started*, *Interval reached* and so on. The values are in `trigger.event.data`, e.g. `{{ trigger.event.data.elapsed_formatted }}`.

### Following a source entity

Optionally, a stopwatch can follow any entity, for example `media_player.xbox`. Set it up in the section **Source entity** when creating the stopwatch or later via **Configure**:

- **Running states:** the stopwatch runs while the entity is in one of these states (e.g. `playing`) and pauses in any other state.
- **Grace period:** some devices briefly report `unavailable`. Within the grace period nothing happens; if the dropout lasts longer, the stopwatch pauses, backdated to the start of the dropout. Set it to 0 to turn it off: `unavailable` then pauses right away, like any other state that is not a running state.
- **Auto-reset:** if the entity was inactive for longer than the configured delay, its next start begins a new session – the stopwatch is reset and started again. Until then, the time of the last session stays visible. With a delay of 0, every new start of the entity begins a new session.

Buttons and actions keep working while a source is set.

### Resetting at a fixed time

Without auto-reset, a stopwatch is only reset by its reset button, the action `stopwatch_plus.reset` or an automation – a restart of Home Assistant keeps the time. To start from zero every day, for example, reset it with a time trigger (this can be combined with auto-reset):

```yaml
alias: Reset the gaming stopwatch every morning
triggers:
  - trigger: time
    at: "04:00:00"
actions:
  - action: stopwatch_plus.reset
    target:
      entity_id: sensor.gaming_elapsed_time
```

## Why the domain is `stopwatch_plus`

Every integration in Home Assistant has a unique internal name, the *domain*. It appears in action names such as `stopwatch_plus.start` and cannot easily be changed later without breaking users' automations.

The obvious domain would be `stopwatch`. It is deliberately **not** used: if Home Assistant ever ships a built-in stopwatch, it would almost certainly use the domain `stopwatch`. A custom integration with the same domain would then override the built-in one, and users could not run both side by side. Using `stopwatch_plus` rules out that collision from the start, while the "plus" reflects the extra features beyond a plain stopwatch.

## Installation

### With HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bornste&repository=hacs-stopwatch&category=integration)

Stopwatch Plus is not in the default HACS store yet. Until then, add it as a custom repository:

1. In Home Assistant, open **HACS**, then the menu (three dots, top right) → **Custom repositories**.
2. Enter `https://github.com/bornste/hacs-stopwatch`, choose the type **Integration** and select **Add**.
3. Search for **Stopwatch Plus** in HACS, open it and select **Download**.
4. Restart Home Assistant.

The button above does steps 1 and 2 for you.

### Manually

Copy the folder `custom_components/stopwatch_plus` of this repository into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.

### Set up a stopwatch

[![Open your Home Assistant instance and start setting up Stopwatch Plus.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=stopwatch_plus)

Go to **Settings → Devices & services → Add integration**, search for **Stopwatch Plus** and enter a name (e.g. "Gaming"). Repeat for every stopwatch you need; each one becomes its own device. Interval and update interval can be changed later via **Configure**.

## Displaying the elapsed time

The elapsed time sensor reports whole seconds, e.g. `163 s`. Some options for a nicer display:

- **Display unit:** open the sensor, then the settings (gear icon), and set the display unit to *minutes*. Home Assistant then shows the time as a duration, e.g. `2 min 43 s`. This only changes the display; automations still see seconds.
- **Formatted attribute:** the attribute `elapsed_formatted` contains the time as `HH:MM:SS`, from 24 hours on as `d.HH:MM:SS` (e.g. `00:02:43`, `1.02:03:04`). Cards that can show an attribute can use it directly. It is updated together with the sensor (see the update interval) and is not stored in the database.
- **Notifications:** every event carries the same formatted value, calculated at the moment of the event, so it can be passed on without a template filter. With the device trigger *Interval reached* the automation is set up in the editor without YAML; written by hand with an event trigger it looks like this:

```yaml
triggers:
  - trigger: event
    event_type: stopwatch_plus_event
    event_data:
      type: interval
      entity_id: sensor.gaming_elapsed_time
actions:
  - action: notify.notify
    data:
      message: "Playing for {{ trigger.event.data.elapsed_formatted }}"
```

## Development

See [docs/development.md](docs/development.md) for the local development instance.

## Support

If Stopwatch Plus is useful to you, you can buy me a coffee on Ko-fi. Thank you!

[![Support me on Ko-fi](https://img.shields.io/badge/Buy%20me%20a%20coffee-Ko--fi-FF5E5B?logo=ko-fi&logoColor=white&style=for-the-badge)](https://ko-fi.com/bornste)

## License

[MIT](LICENSE)

---

Made with ❤️ by [@bornste](https://github.com/bornste) and Claude

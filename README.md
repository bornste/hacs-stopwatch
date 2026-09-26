<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/custom_components/stopwatch_plus/brand/dark_logo@2x.png">
    <img alt="Stopwatch Plus" src="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/custom_components/stopwatch_plus/brand/logo@2x.png" width="420">
  </picture>
</p>

# Stopwatch Plus for Home Assistant

***The stopwatch with the plus – in case Home Assistant adds its own one day.***<br><br>

[![Tests](https://img.shields.io/github/actions/workflow/status/bornste/hacs-stopwatch/tests.yml?branch=main&label=Tests&logo=github&style=flat-square)](https://github.com/bornste/hacs-stopwatch/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/bornste/hacs-stopwatch/validate.yml?branch=main&label=Validate&logo=github&style=flat-square)](https://github.com/bornste/hacs-stopwatch/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/bornste/hacs-stopwatch?sort=semver&style=flat-square)](https://github.com/bornste/hacs-stopwatch/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange?style=flat-square)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fbornste%2Fhacs-stopwatch%2Fmain%2Fhacs.json&query=%24.homeassistant&label=Home%20Assistant&suffix=%2B&color=41BDF5&logo=homeassistant&logoColor=white&style=flat-square)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/bornste/hacs-stopwatch?style=flat-square)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20me-FF5E5B?logo=ko-fi&logoColor=white&style=flat-square)](https://ko-fi.com/bornste)

A stopwatch integration for [Home Assistant](https://www.home-assistant.io/) that counts **up**, can be paused and resumed, and fires events at configurable intervals of running time. Home Assistant's built-in `timer` only counts down; Stopwatch Plus fills that gap.

## Features

- **Any number of stopwatches**, each stopwatch can be started/stopped manual or can be bound to its own device (e.g. "Gaming", "Work time", "TV on").
- **Buttons** for each stopwatch: Start, Pause, Stop, Reset and a combined Start/Pause – ready for dashboards.
- **Actions** `stopwatch_plus.start` (also resumes), `stopwatch_plus.pause`, `stopwatch_plus.stop`, `stopwatch_plus.reset` and `stopwatch_plus.toggle`, with a stopwatch entity or device as target.
- **Sensors:** the elapsed time as a duration sensor (with an `HH:MM:SS` attribute), the status (`idle`, `running`, `paused`) and the time of the last session.
- **Follow a source entity** (optional): the stopwatch runs while an entity is in one of the chosen states (e.g. `media_player.xbox` is `playing`) and pauses otherwise – with a grace period for short dropouts and an optional auto-stop that ends the session after a while of inactivity.
- **Interval events** based on running time only (pauses do not count) – for example to announce "You have been playing for 60 minutes".
- **Automation triggers without typing:** every event is available as a device trigger and via the event entity in the trigger *Event received*.
- **Survives restarts:** the state is kept when Home Assistant restarts; a running stopwatch keeps counting.
- **Dashboard card and tile feature** that count live in the browser, every second, with the controls – included, no extra installation.
- **Database-friendly:** the sensor update interval is configurable (default 60 seconds); the card counts live anyway.
- **Translations:** English and German. Contributions are welcome: copy [`en.json`](custom_components/stopwatch_plus/translations/en.json), translate it, save it as `<language code>.json` (e.g. `fr.json`) and open a pull request.
- Icon and logo in light and dark.

## How it works

A stopwatch is always in one of three states: `idle` (at zero), `running` or `paused`. Every change fires a `stopwatch_plus_event`:

| What happens | From | To | Event `type` |
|---|---|---|---|
| Start | `idle` | `running` | `started` |
| Start (resume) | `paused` | `running` | `resumed` |
| Pause | `running` | `paused` | `paused` |
| Stop | `running` or `paused` | `idle` | `stopped` |
| Reset | `running` | `running`, again from zero | `reset` |
| Reset | `paused` | `idle` | `reset` |
| An interval of running time is reached | `running` | `running` | `interval` |

*Stop* ends the session: back to zero and idle. *Reset* only sets the time back to zero – a running stopwatch keeps counting from there; a paused one is stopped, as a pause at zero would make no sense.

Commands without effect, such as pausing a stopwatch that is not running, do nothing and fire no event. Only running time counts: pauses are not added to the elapsed time, and interval events fire after every full interval of running time.

In the automation editor, the events can be used without typing anything, in two ways:

- **Event received** (entity-based trigger): every stopwatch has an event entity, e.g. `event.gaming_events`. Add a trigger, choose the stopwatch as target and pick *Event received* with the event types you need. The values are in `trigger.to_state.attributes`, e.g. `{{ trigger.to_state.attributes.elapsed_formatted }}`. The events also show up in the logbook and history of that entity.
- **Device trigger** (classic): add a trigger *Device*, choose the stopwatch and pick *Stopwatch started*, *Interval reached* and so on. The values are in `trigger.event.data`, e.g. `{{ trigger.event.data.elapsed_formatted }}`.

### Following a source entity

Optionally, a stopwatch can follow any entity, for example `media_player.xbox`. Set it up in the section **Source entity** when creating the stopwatch or later via **Configure**:

- **Running states:** the stopwatch runs while the entity is in one of these states (e.g. `playing`) and pauses in any other state.
- **Grace period:** some devices briefly report `unavailable`. Within the grace period nothing happens; if the dropout lasts longer, the stopwatch pauses, backdated to the start of the dropout. Set it to 0 to turn it off: `unavailable` then pauses right away, like any other state that is not a running state.
- **Stop automatically after inactivity:** if the entity stays inactive for the configured delay (e.g. 30 minutes), the session ends: the stopwatch is stopped and set back to zero, and its next start begins a new session. The time of the session stays in the sensor *Last session* and in the `stopped` event. Coming back within the delay simply resumes the session. With a delay of 0, the stopwatch stops as soon as the entity becomes inactive.

Buttons and actions keep working while a source is set.

### Resetting at a fixed time

Without auto-stop, a stopwatch is only set back to zero by its Stop or Reset button, the actions `stopwatch_plus.stop` and `stopwatch_plus.reset` or an automation – a restart of Home Assistant keeps the time. To start from zero every day, for example, reset it with a time trigger (this can be combined with auto-stop). If it happens to be running at that moment, it keeps running from zero; use `stopwatch_plus.stop` instead to stop it:

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

## Dashboard card

![Stopwatch Plus card in the standard and compact layout, and the tile card feature](https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/docs/images/card-preview.png)

Stopwatch Plus brings its own dashboard card. It is loaded automatically – no resource has to be added. It counts live in the browser every second, whatever the sensor update interval, and has buttons for Start/Pause, Stop and Reset.

In the dashboard editor, choose **Add card** and either pick a stopwatch entity under **By entity** – the suggestions offer the card in both layouts and a tile card with the controls – or choose **By card → Stopwatch Plus** and select a stopwatch. Everything can be set in the visual editor; in YAML:

```yaml
type: custom:stopwatch-plus-card
entity: sensor.gaming_elapsed_time  # any entity of the stopwatch
name: Gaming                        # optional, default: the name of the stopwatch
layout: standard                    # standard (default) or compact
buttons: [toggle, stop, reset]      # any of them; [] for none
hide_status: false
hide_last_session: false
```

- **Standard:** name and status, the running time in large digits, the buttons and the last session.
- **Compact:** one row with name, status, time and the buttons – e.g. for a list of stopwatches.
- **Buttons:** without `buttons`, the standard layout shows Start/Pause, Stop and Reset, the compact layout Start/Pause and Stop. Stop and Reset are greyed out while the stopwatch is idle.
- **Narrow cards:** the card adapts to its width – the time gets smaller, and on very narrow cards the status badge and the icon are left out. The compact layout needs about half a section; for narrower cards, the standard layout works better.

**Tile card feature:** a [tile card](https://www.home-assistant.io/dashboards/tile/) of any stopwatch entity can show the live time and the buttons as a feature. In the tile card editor, choose **Features → Add feature → Stopwatch Plus controls**; in YAML:

```yaml
type: tile
entity: sensor.gaming_status
features:
  - type: custom:stopwatch-plus-controls
    hide_time: false
    buttons: [toggle, stop, reset]  # any of them, in this order
```

Tapping the name or the time opens the details of the elapsed time sensor. After an update of Stopwatch Plus, reload the dashboard once (or clear the browser cache) if the card still looks like the old version.

## Displaying the elapsed time

Besides the card, the elapsed time sensor can be shown like any other sensor. It reports whole seconds, e.g. `163 s`. Some options for a nicer display:

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

- **Last session:** the sensor `sensor.<name>_last_session` keeps the time of the last session after the stopwatch went back to zero, e.g. to show "Last session 02:15:30" below the running time. Its history shows the length of every session.
- **Total per day or week:** Home Assistant's built-in [History stats](https://www.home-assistant.io/integrations/history_stats/) integration can add up how long `sensor.<name>_status` was `running`, e.g. the playing time today – no extra setup in Stopwatch Plus needed.

## Development

See [docs/development.md](docs/development.md) for the local development instance.

## Support

If Stopwatch Plus is useful to you, you can buy me a coffee on Ko-fi. Thank you!

[![Support me on Ko-fi](https://img.shields.io/badge/Buy%20me%20a%20coffee-Ko--fi-FF5E5B?logo=ko-fi&logoColor=white&style=flat-square)](https://ko-fi.com/bornste)

## License

[MIT](LICENSE)

---

Made with ❤️ by [@bornste](https://github.com/bornste) and Claude

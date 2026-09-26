<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/custom_components/stopwatch_plus/brand/dark_logo@2x.png">
    <img alt="Stopwatch Plus" src="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/custom_components/stopwatch_plus/brand/logo@2x.png" width="420">
  </picture>
</p>

# Stopwatch Plus for Home Assistant

***A stopwatch that counts up – by hand, or on its own while your TV, a window or any other device is on.***<br><br>

[![Tests](https://img.shields.io/github/actions/workflow/status/bornste/hacs-stopwatch/tests.yml?branch=main&label=Tests&logo=github&style=flat-square)](https://github.com/bornste/hacs-stopwatch/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/bornste/hacs-stopwatch/validate.yml?branch=main&label=Validate&logo=github&style=flat-square)](https://github.com/bornste/hacs-stopwatch/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/bornste/hacs-stopwatch?sort=semver&style=flat-square)](https://github.com/bornste/hacs-stopwatch/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange?style=flat-square)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fbornste%2Fhacs-stopwatch%2Fmain%2Fhacs.json&query=%24.homeassistant&label=Home%20Assistant&suffix=%2B&color=41BDF5&logo=homeassistant&logoColor=white&style=flat-square)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/bornste/hacs-stopwatch?style=flat-square)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20me-FF5E5B?logo=ko-fi&logoColor=white&style=flat-square)](https://ko-fi.com/bornste)

Home Assistant's built-in `timer` counts down. Stopwatch Plus counts **up**: start, pause and resume it from the dashboard, or let it follow an entity – for example, it runs while the TV is playing and pauses when it is off. Interval events announce "one hour of screen time" or "the window has been open for 10 minutes", and a dashboard card shows the time live, second by second.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/docs/images/card-hero-dark.png">
  <img alt="Stopwatch Plus card of a running stopwatch" src="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/docs/images/card-hero.png" width="420">
</picture>

## Contents

- [Features](#features)
- [Use cases](#use-cases)
- [Installation](#installation)
- [Configuration](#configuration)
- [Dashboard card](#dashboard-card)
- [Automations](#automations)
- [Following a source entity](#following-a-source-entity)
- [Reference](#reference)
- [Tips](#tips)
- [FAQ](#faq)
- [Development](#development) · [Support](#support) · [License](#license)

## Features

- **Any number of stopwatches**, each one its own device with sensors, buttons and an event entity.
- **Dashboard card and tile card feature** that count live in the browser – included and loaded automatically. [More](#dashboard-card)
- **Follows a source entity** if you like: runs while the TV, a window sensor or a switch is in a "running" state, pauses otherwise, and ends the session after a while of inactivity. [More](#following-a-source-entity)
- **Interval events** after every full interval of running time; pauses do not count. [More](#automations)
- **Triggers in the automation editor** for every event, without typing event names. [More](#automations)
- **Last session** kept in its own sensor after the stopwatch went back to zero.
- **Survives restarts** of Home Assistant; a running stopwatch keeps counting.
- **Database-friendly:** the sensors update once a minute by default; the card counts every second anyway.
- **English and German.** More languages are welcome, see [FAQ](#faq).

## Use cases

- **Screen time** for the TV or a game console, with an announcement every hour.
- **Window open:** a reminder every 10 minutes while a window is open.
- **Sauna or workout**, with an announcement every 15 minutes.
- **Running time of devices** such as a pump, a dehumidifier or an air purifier – for example for maintenance.
- **Working time**, started by hand or following the computer.
- **By hand**, without a source: cooking, a board game, a phone call.

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

Stopwatch Plus needs Home Assistant 2026.1 or newer.

## Configuration

[![Open your Home Assistant instance and start setting up Stopwatch Plus.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=stopwatch_plus)

Go to **Settings → Devices & services → Add integration**, search for **Stopwatch Plus** and enter a name, e.g. "Screen time". Repeat this for every stopwatch; each one becomes its own device. Everything except the name can be changed later via **Configure**.

| Option | Default | Meaning |
|---|---|---|
| Name | – | Name of the device and its entities, e.g. "Screen time" → `sensor.screen_time_elapsed_time`. |
| Interval | 0 (off) | Fires an interval event every time this much running time has passed, at most 24 hours. |
| Sensor update interval | 60 s | How often the sensors update while running, from 1 second to 1 hour. Every update is written to the database, so short intervals fill it up ([FAQ](#faq)). Interval events and the card are not affected: they are always on time. |

In the collapsible section **Source entity** (optional, see [Following a source entity](#following-a-source-entity)):

| Option | Default | Meaning |
|---|---|---|
| Source entity | – | The entity to follow, e.g. `media_player.living_room_tv`. Empty: control the stopwatch only by hand and with automations. |
| Running states | `playing`, `on` | The stopwatch runs in these states and pauses in all others. Own states can be typed in. |
| Grace period when unavailable | 2 min | Short dropouts to `unavailable` are ignored for this long, at most 1 hour. 0: pause right away. |
| Stop automatically after inactivity | off | Ends the session when the source stays inactive for the delay below. |
| Inactivity before stopping | 30 min | At most 7 days. 0: stop as soon as the source becomes inactive. |

## Dashboard card

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/docs/images/card-preview-dark.png">
  <img alt="Stopwatch Plus card in the standard and compact layout, and the tile card feature" src="https://raw.githubusercontent.com/bornste/hacs-stopwatch/main/docs/images/card-preview.png">
</picture>

Stopwatch Plus brings its own dashboard card. It is loaded automatically – no resource has to be added. It counts live in the browser every second, whatever the sensor update interval, and has buttons for Start/Pause, Stop and Reset.

In the dashboard editor, choose **Add card** and either pick a stopwatch entity under **By entity** – the suggestions offer the card in both layouts and a tile card with the controls – or choose **By card → Stopwatch Plus** and select a stopwatch. Everything can be set in the visual editor; in YAML:

```yaml
type: custom:stopwatch-plus-card
entity: sensor.screen_time_elapsed_time  # any entity of the stopwatch
name: Screen time                        # optional, default: the name of the stopwatch
layout: standard                         # standard (default) or compact
buttons: [toggle, stop, reset]           # any of them; [] for none
hide_status: false
hide_last_session: false
```

- **Standard:** name and status, the running time in large digits, the buttons and the last session.
- **Compact:** one row with name, status, time and the buttons – e.g. for a list of stopwatches.
- **Buttons:** without `buttons`, the standard layout shows Start/Pause, Stop and Reset, the compact layout Start/Pause and Stop. Stop and Reset are greyed out while the stopwatch is idle.
- **Narrow cards:** the card adapts to its width – the time gets smaller, and on very narrow cards the icon is left out. The compact layout needs about half a section; for narrower cards, the standard layout works better.

Tapping the name or the time opens the details of the elapsed time sensor.

**Tile card feature:** a [tile card](https://www.home-assistant.io/dashboards/tile/) of any stopwatch entity can show the live time and the buttons as a feature. In the tile card editor, choose **Features → Add feature → Stopwatch Plus controls**; in YAML:

```yaml
type: tile
entity: sensor.screen_time_elapsed_time
hide_state: true  # the feature shows the live time
features:
  - type: custom:stopwatch-plus-controls
    hide_time: false
    buttons: [toggle, stop, reset]  # any of them, in this order
```

## Automations

Every change of a stopwatch – started, paused, resumed, stopped, reset, interval reached – is an event. In the automation editor, there are two ways to use them without typing event names:

- **Event received** (entity-based trigger): choose the stopwatch as target and pick *Event received* with the event types you need. The values are in `trigger.to_state.attributes`, e.g. `{{ trigger.to_state.attributes.elapsed_formatted }}`.
- **Device trigger**: add a trigger *Device*, choose the stopwatch and pick *Stopwatch started*, *Interval reached* and so on. The values are in `trigger.event.data`, e.g. `{{ trigger.event.data.elapsed_formatted }}`.

Every event carries the elapsed time, already formatted as `HH:MM:SS` and calculated at the moment of the event – ready for a message. The [Reference](#reference) lists all event types and values.

**Screen time: announce every hour.** Stopwatch "Screen time", source `media_player.living_room_tv`, interval 1 hour:

```yaml
alias: Announce screen time
triggers:
  - trigger: event
    event_type: stopwatch_plus_event
    event_data:
      type: interval
      entity_id: sensor.screen_time_elapsed_time
actions:
  - action: notify.notify
    data:
      message: "The TV has been on for {{ trigger.event.data.elapsed_formatted }}."
```

**Screen time: report the session.** With *Stop automatically after inactivity*, the `stopped` event reports the time the session reached:

```yaml
alias: Report the screen time session
triggers:
  - trigger: event
    event_type: stopwatch_plus_event
    event_data:
      type: stopped
      entity_id: sensor.screen_time_elapsed_time
actions:
  - action: notify.notify
    data:
      message: "Screen time session: {{ trigger.event.data.elapsed_formatted }}."
```

**Window open: remind every 10 minutes.** Stopwatch "Bedroom window", source `binary_sensor.bedroom_window`, running state `on`, interval 10 minutes, *Stop automatically after inactivity* on with a delay of 0 – so every opening starts from zero:

```yaml
alias: Bedroom window reminder
triggers:
  - trigger: event
    event_type: stopwatch_plus_event
    event_data:
      type: interval
      entity_id: sensor.bedroom_window_elapsed_time
actions:
  - action: notify.notify
    data:
      message: "The bedroom window has been open for {{ trigger.event.data.elapsed_formatted }}."
```

The stopwatches can also be controlled from automations and scripts with the [actions](#actions), e.g. `stopwatch_plus.start`.

## Following a source entity

A stopwatch can follow any entity, for example `media_player.living_room_tv` or `binary_sensor.bedroom_window`. Set it up in the section **Source entity** when creating the stopwatch or later via **Configure**:

- **Running states:** the stopwatch runs while the entity is in one of these states (e.g. `playing`) and pauses in any other state.
- **Grace period:** some devices briefly report `unavailable`. Within the grace period nothing happens; if the dropout lasts longer, the stopwatch pauses, backdated to the start of the dropout. Set it to 0 to turn it off: `unavailable` then pauses right away, like any other state that is not a running state.
- **Stop automatically after inactivity:** if the entity stays inactive for the configured delay (e.g. 30 minutes), the session ends: the stopwatch is stopped and set back to zero, and its next start begins a new session. The time of the session stays in the sensor *Last session* and in the `stopped` event. Coming back within the delay simply resumes the session. With a delay of 0, the stopwatch stops as soon as the entity becomes inactive.

Buttons, the card and the actions keep working while a source is set; the next change of the source takes over again.

## Reference

### Entities

Each stopwatch is a device with these entities (IDs for a stopwatch named "Screen time"):

| Entity | Content |
|---|---|
| `sensor.screen_time_elapsed_time` | Running time in seconds. Attributes: `elapsed_formatted` (`HH:MM:SS`), `status`, `started_at`, `running_since`, `accumulated_seconds`, `interval_count`. |
| `sensor.screen_time_status` | `idle`, `running` or `paused`. |
| `sensor.screen_time_last_session` | Running time of the last session, set when the time goes back to zero. Attributes: `elapsed_formatted`, `ended_at`. |
| `event.screen_time_events` | Reports every event, for the trigger *Event received* and the logbook. |
| `button.screen_time_start`, `…_pause`, `…_stop`, `…_reset`, `…_start_pause` | The same as the actions below. |

### States and events

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

*Stop* ends the session: back to zero and idle. *Reset* only sets the time back to zero – a running stopwatch keeps counting from there; a paused one is stopped, as a pause at zero would make no sense. Commands without effect, such as pausing a stopwatch that is not running, do nothing and fire no event.

Event data:

| Key | Content |
|---|---|
| `type` | Event type, see above. |
| `entity_id`, `device_id`, `name` | The elapsed time sensor, the device and the name of the stopwatch. |
| `elapsed_seconds`, `elapsed_formatted` | Running time at the moment of the event. For `stopped` and `reset`: the time the session reached. For `interval`: the exact threshold, e.g. `3600`. |
| `interval_count` | Number of intervals reached in this session. |
| `source` | What caused the change: `action`, `button`, `source_entity` or `auto_stop`; empty for `interval`. |

`elapsed_formatted` uses `HH:MM:SS`, and from 24 hours on `d.HH:MM:SS` (e.g. `00:02:43`, `1.02:03:04`).

### Actions

| Action | Effect |
|---|---|
| `stopwatch_plus.start` | Starts the stopwatch, or resumes it when it is paused. |
| `stopwatch_plus.pause` | Pauses it. |
| `stopwatch_plus.stop` | Stops it and sets it back to zero. |
| `stopwatch_plus.reset` | Sets it back to zero; a running stopwatch keeps running. |
| `stopwatch_plus.toggle` | Pauses a running stopwatch, otherwise starts it. |

Target: any entity or the device of a stopwatch; each stopwatch acts once, even if several of its entities are targeted.

## Tips

**Start from zero every day.** Without auto-stop, a stopwatch keeps its time until it is stopped or reset – also across restarts. To start every day from zero, stop it with a time trigger (this can be combined with auto-stop):

```yaml
alias: Reset the screen time every morning
triggers:
  - trigger: time
    at: "04:00:00"
actions:
  - action: stopwatch_plus.stop
    target:
      entity_id: sensor.screen_time_elapsed_time
```

`stopwatch_plus.reset` instead would keep a running stopwatch running from zero.

**Total per day or week.** Home Assistant's built-in [History stats](https://www.home-assistant.io/integrations/history_stats/) integration adds up how long `sensor.screen_time_status` was `running`, e.g. the screen time today.

**Show the time without the card.** The elapsed time sensor reports whole seconds, e.g. `163 s`. In the settings of the sensor (gear icon), set the display unit to *minutes* to see `2 min 43 s`; automations still see seconds. Cards that can show an attribute can use `elapsed_formatted` (`HH:MM:SS`), which updates together with the sensor.

## FAQ

**The card still looks like the old version after an update.**
Reload the dashboard once, or clear the browser cache.

**Why do the sensors update only once a minute?**
Every update is written to the database. With one update per second, a running stopwatch would write about 3600 rows per hour. The card and the events do not depend on it: the card counts in the browser, and interval events fire at the exact moment, whatever the update interval. Each interval event also updates the sensors, so a short interval adds database rows as well. The update interval can be changed via **Configure**.

**Can I add a language?**
Gladly: copy [`en.json`](custom_components/stopwatch_plus/translations/en.json), translate it, save it as `<language code>.json` (e.g. `fr.json`) and open a pull request.

**Why is the domain `stopwatch_plus` and not `stopwatch`?**
Every integration has a unique internal name, the *domain*. It appears in action names such as `stopwatch_plus.start` and cannot easily be changed later without breaking automations. If Home Assistant ever ships a built-in stopwatch, it would almost certainly use the domain `stopwatch`, and a custom integration with the same domain would override it. `stopwatch_plus` rules out that collision from the start – and the "plus" stands for the features beyond a plain stopwatch.

## Development

See [docs/development.md](docs/development.md) for the local development instance and the tests.

## Support

If Stopwatch Plus is useful to you, you can buy me a coffee on Ko-fi. Thank you!

[![Support me on Ko-fi](https://img.shields.io/badge/Buy%20me%20a%20coffee-Ko--fi-FF5E5B?logo=ko-fi&logoColor=white&style=flat-square)](https://ko-fi.com/bornste)

## License

[MIT](LICENSE)

---

Made with ❤️ by [@bornste](https://github.com/bornste) and Claude

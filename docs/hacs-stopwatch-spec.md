# Stopwatch Plus – Specification (draft)

Last updated: 2026-09-24. Repository: https://github.com/bornste/hacs-stopwatch (public).

## Decisions

| Topic | Decision |
|---|---|
| Domain | `stopwatch_plus` – deliberately not `stopwatch`, to rule out a collision with a possible future core integration (rationale in the README) |
| Display name | "Stopwatch Plus" |
| Elapsed state | Sensor, numeric in seconds, `device_class: duration` |
| Update interval | Configurable in the options; default **60 s** |
| Integration type | `service` – stopwatches are listed under Settings → Devices & services → Integrations, one device per stopwatch; not a helper, so they do not fill up the helper list |
| Live display | Attributes allow client-side counting; a dashboard card bundled with the integration (phase 2) |
| Home Assistant restart | State is restored; if the stopwatch was running, the downtime is counted |
| Source entity | Optional: an entity plus the states that count as "running" (e.g. `media_player.xbox` = `playing`) → start/resume and pause automatically |
| Auto-reset | Optional (on/off) with a configurable inactivity delay (see below) |
| Unavailable source | Grace period before the stopwatch reacts (see below) |
| Interval events | Configurable interval of running time (pauses do not count), with second precision |
| Triggers | One event type with a `type` field, exposed as separate device triggers (see below) |
| Code style | Python / Home Assistant standard snake_case; comments in English |
| Documentation | All documents in the repository are written in English |
| UI languages | English (base) + German |
| Minimum Home Assistant version | 2026.1 |
| License | MIT |

## Multiple stopwatches

Each stopwatch is its own config entry (Settings → Devices & services → Add integration → Stopwatch Plus), e.g. "Gaming", "Work time". Each entry creates a device with its own entities. Actions select the stopwatch via `target` (entity or device), for example:

```yaml
action: stopwatch_plus.start
target:
  entity_id: sensor.gaming_elapsed_time
```

## Entities per stopwatch (one device)

Entity IDs are derived from the English entity names, whatever the language of the Home Assistant instance.

- `sensor.<name>_elapsed_time` – elapsed running time (seconds, duration, display precision 0). Attributes: `elapsed_formatted`, `status`, `started_at`, `running_since`, `accumulated_seconds`, `interval_count`. `elapsed_formatted` is excluded from the recorder (it is derived from the state).
- `sensor.<name>_status` – enum: `idle` / `running` / `paused` (translated).
- `button.<name>_start` – starts or resumes.
- `button.<name>_pause`
- `button.<name>_reset`

## Actions

`stopwatch_plus.start` (also resumes), `stopwatch_plus.pause`, `stopwatch_plus.reset`, `stopwatch_plus.toggle` – target: stopwatch entity or device.

Each call acts once per stopwatch, even if the target resolves to several entities of the same stopwatch (e.g. when a device is targeted).

`reset` sets the elapsed time to 0 and the status to `idle`, regardless of the previous status.

Commands without effect (starting a running stopwatch, pausing a stopwatch that is not running, resetting an idle one) do nothing and fire no event. An action whose target contains no loaded stopwatch raises a validation error.

## Source entity

- Source enters one of the "running" states → start (from `idle`) or resume (from `paused`).
- Source enters any other valid state (e.g. `off`, `idle`) → pause.
- Manual actions and buttons keep working; the next source state change takes over again.
- Only changes of meaning count (running ↔ inactive ↔ unavailable). Attribute changes or a change between two running states (e.g. `playing` → `on`) are ignored, so they do not undo a manual pause.
- At setup (and after a restart) the stopwatch follows the current state of the source.
- Default running states: `playing`, `on`; own states can be typed in.

### Unavailable / unknown source

Some sources (e.g. Xbox) briefly report `unavailable` or `unknown` while still in use.

- On `unavailable` / `unknown` the stopwatch keeps its current status and remembers the moment.
- If the source returns to a "running" state within the grace period → nothing happened, the time keeps counting without a gap.
- If the grace period expires, or the source returns to a non-running state → pause, backdated to the moment the source became unavailable (the unavailable time is not counted).
- Grace period configurable, default 2 minutes, at most 1 hour. 0 turns it off: `unavailable` / `unknown` then pause immediately, like any other non-running state.

### Auto-reset

- Option on/off (default: off) and inactivity delay (default: 30 minutes, at most 7 days). A delay of 0 makes every new start of the source a new session.
- When the source becomes inactive (non-running, or unavailable beyond the grace period), the inactivity time starts.
- If the source becomes "running" again **after** the delay has passed, the stopwatch is reset and then started – a new session.
- If it becomes "running" again **before** the delay has passed, the stopwatch simply resumes – same session.
- The reset happens only at the start of the next session, so the time of the last session stays visible until then.
- Only applies when a source entity is configured.
- Only applies when the stopwatch is paused at that moment; a stopwatch started by hand in the meantime is not reset.
- The inactivity start and a running grace period are persisted, so both survive a restart of Home Assistant.

## Events and triggers

One event type on the Home Assistant event bus: `stopwatch_plus_event`.

| `type` | Fired when |
|---|---|
| `started` | Started from `idle` |
| `paused` | Paused |
| `resumed` | Resumed from `paused` |
| `reset` | Reset (manually or by auto-reset) |
| `interval` | An interval of running time has been reached |

Event data: `type`, `entity_id`, `device_id`, `name`, `elapsed_seconds`, `elapsed_formatted` (see below), `interval_count`, `source` (`action`, `button`, `source_entity`, `auto_reset`; `null` for `interval` events). For `interval` events, `elapsed_seconds` is the exact threshold (e.g. 3600), not the slightly later firing time.

Each `type` is also available as its own device trigger in the automation editor ("Stopwatch started", "Interval reached", …). Interval events fire at the exact moment, independent of the sensor update interval. A state trigger on the status sensor remains possible as a generic alternative.

An interval shorter than the sensor update interval is fine: interval events are scheduled independently and fire on time. Every interval event also refreshes the elapsed time sensor, so the sensor effectively updates at the shorter of both intervals (and writes to the database as often).

Restoring the state after a restart fires no events. Intervals that fell into the downtime of a running stopwatch are skipped (not fired in a burst); counting continues with the next threshold.

## Time format

`elapsed_formatted` (attribute and event data) uses `HH:MM:SS`, and `d.HH:MM:SS` from 24 hours on – the constant ("c") format of a .NET `TimeSpan`. Examples: `00:02:30`, `12:05:09`, `1.02:03:04`, `10.00:00:05`. Hours, minutes and seconds always have two digits; days have no leading zero and only appear when needed.

The attribute is updated together with the sensor state (update interval); event data is calculated at the moment of the event and is always exact.

## Setup (config flow / options)

Name; optional source entity and the states that count as "running"; grace period for unavailable source; auto-reset on/off and delay; interval (0 = off, max. 24 h); sensor update interval (1 s – 1 h). Both are entered with Home Assistant's duration field (hours, minutes, seconds) and stored in seconds. Everything except the name can be changed later via "Configure" (options flow); saving the options reloads the stopwatch. The state is stored per stopwatch in Home Assistant's `.storage` folder and deleted when the stopwatch is removed.

## Live display with infrequent sensor updates

Same principle as the core `timer`: the state changes rarely and the frontend does the counting. Attributes `accumulated_seconds` (total up to the last start) + `running_since` (time of the last start) → display = `accumulated_seconds + (now − running_since)`. A small dashboard card (JavaScript) reads these attributes and counts every second in the browser. The integration ships the card and registers it itself; no separate HACS installation required.

## Database note

An integration cannot exclude its own states from the recorder. With 1 s updates, Home Assistant would write about 3600 rows per hour of running time. Hence infrequent updates by default and the live display via the card; the README also documents `recorder: exclude:`.

## Repository structure (planned)

```
custom_components/stopwatch_plus/
  __init__.py, manifest.json, const.py, config_flow.py,
  stopwatch.py (state logic), entity.py, sensor.py, button.py,
  services.py, services.yaml, device_trigger.py,
  translations/en.json, translations/de.json,
  frontend/stopwatch-card.js (phase 2)
docs/hacs-stopwatch-spec.md, docs/development.md
scripts/setup, scripts/develop (local development instance in WSL)
dev/configuration.yaml (configuration of the development instance)
hacs.json, README.md, LICENSE, .gitignore, .gitattributes
.github/workflows/validate.yml (HACS action + hassfest)
tests/ (pytest-homeassistant-custom-component), scripts/test
pyproject.toml (pytest and Ruff settings), requirements_test*.txt
.github/workflows/tests.yml (pytest + Ruff)
.github/workflows/release.yml (checks tag, manifest version and changelog on release)
CHANGELOG.md
```

## Milestones

1. **Manual stopwatch** – done: state logic with restore, sensors, buttons, actions, events incl. intervals, config and options flow (name, interval, update interval), tests for the minimum and the latest Home Assistant. After the first test: intervals in seconds, integration instead of helper.
2. **Source entity** – done: binding with running states, grace period with backdated pause, auto-reset for new sessions, persisted across restarts; settings in a collapsible "Source entity" section of the config and options flow.
3. **Device triggers** – done: one device trigger per event type (`started`, `paused`, `resumed`, `reset`, `interval`), based on `stopwatch_plus_event` filtered by `device_id` and `type`; translated names in English and German.
4. Dashboard card with live counting.
5. Icon, first release v0.1.0, submission to HACS.

## Quality

Automated tests with `pytest-homeassistant-custom-component` run on every push against the minimum (2026.1) and the latest Home Assistant; Ruff checks linting and formatting.

## Brand images

Icon and logo are shipped with the integration in `custom_components/stopwatch_plus/brand/` (supported since Home Assistant 2026.3; older versions simply show no icon). Files: `icon.png` (256×256), `icon@2x.png` (512×512), `logo.png` (height 128), `logo@2x.png` (height 256), each with a `dark_` variant. Design: stopwatch with a plus on its face; indigo body, amber plus (`#4F46E5` / `#F59E0B`, dark theme `#818CF8` / `#FBBF24`), wordmark in Readex Pro SemiBold (600). Sources and generator: `docs/brand/` (`python docs/brand/generate.py <ReadexPro-SemiBold.ttf>`). The HACS validation finds the local `brand/icon.png`, so the brands check is no longer skipped.

## Translations

Custom integrations read their texts from `translations/<language>.json`; `translations/en.json` is the source of truth. There is no `strings.json` (that file is only used by core integrations).

## Open points

- Check at the first release whether HACS shows the bundled icon in its store view.

## Ideas (not planned yet)

- Sensor "last session duration" (`state_class: measurement`, duration in seconds), updated when a session ends, so the duration of every session goes into the long-term statistics without a template sensor. Use case: how long a window was open at a stretch.

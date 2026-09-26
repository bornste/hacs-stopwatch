# Stopwatch Plus – Specification (draft)

Last updated: 2026-09-26. Repository: https://github.com/bornste/hacs-stopwatch (public).

## Decisions

| Topic | Decision |
|---|---|
| Domain | `stopwatch_plus` – deliberately not `stopwatch`, to rule out a collision with a possible future core integration (rationale in the README) |
| Display name | "Stopwatch Plus" |
| Elapsed state | Sensor, numeric in seconds, `device_class: duration` |
| Update interval | Configurable in the options; default **60 s** |
| Integration type | `service` – stopwatches are listed under Settings → Devices & services → Integrations, one device per stopwatch; not a helper, so they do not fill up the helper list |
| Live display | Attributes allow client-side counting; a dashboard card and a tile card feature bundled with the integration (see below) |
| Home Assistant restart | State is restored; if the stopwatch was running, the downtime is counted |
| Source entity | Optional: an entity plus the states that count as "running" (e.g. `media_player.xbox` = `playing`) → start/resume and pause automatically |
| Auto-stop | Optional (on/off) with a configurable inactivity delay (see below) |
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
- `sensor.<name>_last_session` – running time of the last session (seconds, duration, display precision 0), `unknown` until a first session ended. Set whenever a time above 0 goes back to zero (stop, reset, auto-stop); pausing does not change it. Attributes: `elapsed_formatted` (not recorded), `ended_at`. Persisted with the state.
- `button.<name>_start` – starts or resumes.
- `button.<name>_pause`
- `button.<name>_stop` – stops and sets back to zero (`idle`).
- `button.<name>_reset` – sets back to zero; a running stopwatch keeps running.
- `button.<name>_start_pause` – pauses when running, otherwise starts or resumes (like `stopwatch_plus.toggle`).
- `event.<name>_events` – reports every stopwatch event (event types `started`, `paused`, `resumed`, `stopped`, `reset`, `interval`); attributes: `elapsed_seconds`, `elapsed_formatted`, `interval_count`, `source`.

## Actions

`stopwatch_plus.start` (also resumes), `stopwatch_plus.pause`, `stopwatch_plus.stop`, `stopwatch_plus.reset`, `stopwatch_plus.toggle` – target: stopwatch entity or device.

Each call acts once per stopwatch, even if the target resolves to several entities of the same stopwatch (e.g. when a device is targeted).

`stop` sets the elapsed time to 0 and the status to `idle`, whether running or paused.

`reset` sets the elapsed time to 0. A running stopwatch keeps running and counts again from zero (`started_at` and the interval count start anew); a paused one goes to `idle`, like `stop`.

Commands without effect (starting a running stopwatch, pausing a stopwatch that is not running, stopping or resetting an idle one) do nothing and fire no event. An action whose target contains no loaded stopwatch raises a validation error.

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

### Auto-stop

- Option on/off (default: off) and inactivity delay (default: 30 minutes, at most 7 days).
- When the source becomes inactive (non-running, or unavailable beyond the grace period), the inactivity time starts; for a dropout it counts from the start of the dropout, like the backdated pause. A source that turns off and then becomes unavailable stays inactive.
- If the source stays inactive for the delay, the session ends: the stopwatch is stopped (event `stopped`, source `auto_stop`), its time goes to the last session sensor, and the next start of the source fires `started`.
- If the source becomes "running" again **before** the delay has passed, the stopwatch simply resumes – same session.
- A delay of 0 stops the stopwatch as soon as the source becomes inactive (a `paused` event directly followed by `stopped`).
- Only applies when a source entity is configured.
- Only applies when the stopwatch is still paused at the deadline; a stopwatch started by hand in the meantime keeps running.
- The inactivity start and a running grace period are persisted, so both survive a restart of Home Assistant. A deadline that passed while Home Assistant was down stops the stopwatch right after the start.

## Events and triggers

One event type on the Home Assistant event bus: `stopwatch_plus_event`.

| `type` | Fired when |
|---|---|
| `started` | Started from `idle` |
| `paused` | Paused |
| `resumed` | Resumed from `paused` |
| `stopped` | Stopped and set back to zero (manually or by auto-stop) |
| `reset` | Set back to zero; a running stopwatch keeps running |
| `interval` | An interval of running time has been reached |

Event data: `type`, `entity_id`, `device_id`, `name`, `elapsed_seconds`, `elapsed_formatted` (see below), `interval_count`, `source` (`action`, `button`, `source_entity`, `auto_stop`; `null` for `interval` events). For `interval` events, `elapsed_seconds` is the exact threshold (e.g. 3600), not the slightly later firing time. For `stopped` and `reset` events, `elapsed_seconds`, `elapsed_formatted` and `interval_count` are the values the session reached before going back to zero.

Each `type` is also available as its own device trigger in the automation editor ("Stopwatch started", "Interval reached", …). Interval events fire at the exact moment, independent of the sensor update interval. A state trigger on the status sensor remains possible as a generic alternative.

In addition, the event entity makes the events usable with Home Assistant's entity-based trigger `event.received` ("Event received"), which the new trigger dialog offers for a target such as the stopwatch device. Entity-based triggers are a Labs preview up to about Home Assistant 2026.1 and standard in later versions; the classic device triggers work in all supported versions.

An interval shorter than the sensor update interval is fine: interval events are scheduled independently and fire on time. Every interval event also refreshes the elapsed time sensor, so the sensor effectively updates at the shorter of both intervals (and writes to the database as often).

Restoring the state after a restart fires no events. Intervals that fell into the downtime of a running stopwatch are skipped (not fired in a burst); counting continues with the next threshold.

## Time format

`elapsed_formatted` (attribute and event data) uses `HH:MM:SS`, and `d.HH:MM:SS` from 24 hours on – the constant ("c") format of a .NET `TimeSpan`. Examples: `00:02:30`, `12:05:09`, `1.02:03:04`, `10.00:00:05`. Hours, minutes and seconds always have two digits; days have no leading zero and only appear when needed.

The attribute is updated together with the sensor state (update interval); event data is calculated at the moment of the event and is always exact.

## Setup (config flow / options)

Name; optional source entity and the states that count as "running"; grace period for unavailable source; auto-stop on/off and delay; interval (0 = off, max. 24 h); sensor update interval (1 s – 1 h). Both are entered with Home Assistant's duration field (hours, minutes, seconds) and stored in seconds. Everything except the name can be changed later via "Configure" (options flow); saving the options reloads the stopwatch. The state is stored per stopwatch in Home Assistant's `.storage` folder and deleted when the stopwatch is removed.

## Live display with infrequent sensor updates

Same principle as the core `timer`: the state changes rarely and the frontend does the counting. Attributes `accumulated_seconds` (total up to the last start) + `running_since` (time of the last start) → display = `accumulated_seconds + (now − running_since)`. A small dashboard card (JavaScript) reads these attributes and counts every second in the browser. The integration ships the card and registers it itself; no separate HACS installation required.

### Dashboard card and tile feature

- One file, `custom_components/stopwatch_plus/www/stopwatch-plus-card.js`, plain JavaScript (web components, no build step, no dependencies besides the elements of the Home Assistant frontend such as `ha-card` and `ha-icon`).
- The integration serves the folder under `/stopwatch_plus_frontend/` and adds the file with `frontend.add_extra_js_url` (URL with `?v=<version>` so browsers load a new version). `frontend` and `http` are `after_dependencies`; without them (tests, minimal setups) nothing is registered.
- The elements are defined only after the frontend has started (`home-assistant` defined): the frontend replaces `window.customElements` with a scoped registry polyfill, and elements defined earlier would not be found ("Custom element doesn't exist").
- Card `custom:stopwatch-plus-card`: options `entity` (any entity of a stopwatch; the elapsed time and last session sensors are found via the device and the translation keys `elapsed` / `last_session`), `name`, `layout` (`standard` / `compact`), `buttons` (subset of `toggle`, `stop`, `reset`; default: all three in the standard layout, `toggle` and `stop` in the compact one), `hide_status`, `hide_last_session`. The time shrinks with the card width (container query units) and a bit more from one day on; container queries leave out the status badge (below 170 px), the icon (standard below 150 px, compact below 340 px) and the secondary line of the compact layout on narrow cards. The tile feature keeps the time fully visible and narrows the buttons instead. Visual editor via `getConfigForm`, card picker entry, stub config with the first stopwatch, and `getEntitySuggestion` for the "By entity" suggestions (standard, compact, tile card with the feature and `hide_state`). Buttons call the actions `stopwatch_plus.toggle`, `stop` and `reset`; Stop and Reset are disabled while idle.
- Tile card feature `custom:stopwatch-plus-controls` for any stopwatch entity: options `hide_time` and `buttons` (subset of `toggle`, `stop`, `reset`).
- Texts in English and German (from the user language), statuses via the entity translations.

## Database note

An integration cannot exclude its own states from the recorder. With 1 s updates, Home Assistant would write about 3600 rows per hour of running time. Hence infrequent updates by default and the live display via the card; the README also documents `recorder: exclude:`.

## Repository structure (planned)

```
custom_components/stopwatch_plus/
  __init__.py, manifest.json, const.py, config_flow.py,
  stopwatch.py (state logic), entity.py, sensor.py, button.py,
  services.py, services.yaml, device_trigger.py,
  translations/en.json, translations/de.json,
  frontend.py, www/stopwatch-plus-card.js (dashboard card and tile feature)
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
2. **Source entity** – done: binding with running states, grace period with backdated pause, auto-reset for new sessions (changed to auto-stop in 0.3.0), persisted across restarts; settings in a collapsible "Source entity" section of the config and options flow.
3. **Device triggers** – done: one device trigger per event type (`started`, `paused`, `resumed`, `stopped`, `reset`, `interval`), based on `stopwatch_plus_event` filtered by `device_id` and `type`; translated names in English and German.
4. **Dashboard card** – done: card with standard and compact layout, visual editor and tile card feature, counting live in the browser; shipped and registered by the integration.
5. **Release and HACS** – icon and first release v0.1.0 done; card tested with the frontends of 2026.1 and 2026.9; v1.0.0 prepared; submission to the HACS default list open.

## Quality

Automated tests with `pytest-homeassistant-custom-component` run on every push against the minimum (2026.1) and the latest Home Assistant; Ruff checks linting and formatting.

## Brand images

Icon and logo are shipped with the integration in `custom_components/stopwatch_plus/brand/` (supported since Home Assistant 2026.3; older versions simply show no icon). Files: `icon.png` (256×256), `icon@2x.png` (512×512), `logo.png` (height 128), `logo@2x.png` (height 256), each with a `dark_` variant. Design: stopwatch with a plus on its face; indigo body, amber plus (`#4F46E5` / `#F59E0B`, dark theme `#818CF8` / `#FBBF24`), wordmark in Readex Pro SemiBold (600). Sources and generator: `docs/brand/` (`python docs/brand/generate.py <ReadexPro-SemiBold.ttf>`). The same script writes the GitHub social preview `docs/brand/social-preview.png` (1280×640, content at least 80 px from the edges), uploaded by hand under Settings → General → Social preview. The HACS validation finds the local `brand/icon.png`, so the brands check is no longer skipped.

## Translations

Custom integrations read their texts from `translations/<language>.json`; `translations/en.json` is the source of truth. There is no `strings.json` (that file is only used by core integrations).

## Open points

- Check at the first release whether HACS shows the bundled icon in its store view.

## Ideas (not planned yet)

- Sensor "last session duration" (`state_class: measurement`, duration in seconds), updated when a session ends, so the duration of every session goes into the long-term statistics without a template sensor. Use case: how long a window was open at a stretch.

# Stopwatch Plus – Specification (draft)

Last updated: 2026-09-24. Repository: https://github.com/bornste/hacs-stopwatch (public).

## Decisions

| Topic | Decision |
|---|---|
| Domain | `stopwatch_plus` – deliberately not `stopwatch`, to rule out a collision with a possible future core integration (rationale in the README) |
| Display name | "Stopwatch Plus" |
| Elapsed state | Sensor, numeric in seconds, `device_class: duration` |
| Update interval | Configurable in the options; default **60 s** |
| Live display | Attributes allow client-side counting; a dashboard card bundled with the integration (phase 2) |
| Home Assistant restart | State is restored; if the stopwatch was running, the downtime is counted |
| Source entity | Optional: an entity plus the states that count as "running" (e.g. `media_player.xbox` = `playing`) → start/resume and pause automatically |
| Auto-reset | Optional (on/off) with a configurable inactivity delay (see below) |
| Unavailable source | Grace period before the stopwatch reacts (see below) |
| Interval events | Configurable interval of running time (pauses do not count) |
| Triggers | One event type with a `type` field, exposed as separate device triggers (see below) |
| Code style | Python / Home Assistant standard snake_case; comments in English |
| Documentation | All documents in the repository are written in English |
| UI languages | English (base) + German |
| Minimum Home Assistant version | 2026.1 |
| License | MIT |

## Multiple stopwatches

Each stopwatch is its own config entry (the manifest declares `integration_type: helper`, so it is created under Settings → Devices & services → Helpers → Create helper → Stopwatch Plus), e.g. "Gaming", "Work time". Each entry creates a device with its own entities. Actions select the stopwatch via `target` (entity or device), for example:

```yaml
action: stopwatch_plus.start
target:
  entity_id: sensor.gaming_elapsed
```

## Entities per stopwatch (one device)

- `sensor.<name>_elapsed` – elapsed running time (seconds, duration). Attributes: `status`, `started_at`, `running_since`, `accumulated_seconds`, `interval_count`.
- `sensor.<name>_status` – enum: `idle` / `running` / `paused` (translated).
- `button.<name>_start` – starts or resumes.
- `button.<name>_pause`
- `button.<name>_reset`

## Actions

`stopwatch_plus.start` (also resumes), `stopwatch_plus.pause`, `stopwatch_plus.reset`, `stopwatch_plus.toggle` – target: stopwatch entity or device.

Each call acts once per stopwatch, even if the target resolves to several entities of the same stopwatch (e.g. when a device is targeted).

`reset` sets the elapsed time to 0 and the status to `idle`, regardless of the previous status.

## Source entity

- Source enters one of the "running" states → start (from `idle`) or resume (from `paused`).
- Source enters any other valid state (e.g. `off`, `idle`) → pause.
- Manual actions and buttons keep working; the next source state change takes over again.

### Unavailable / unknown source

Some sources (e.g. Xbox) briefly report `unavailable` or `unknown` while still in use.

- On `unavailable` / `unknown` the stopwatch keeps its current status and remembers the moment.
- If the source returns to a "running" state within the grace period → nothing happened, the time keeps counting without a gap.
- If the grace period expires, or the source returns to a non-running state → pause, backdated to the moment the source became unavailable (the unavailable time is not counted).
- Grace period configurable, default 2 minutes.

### Auto-reset

- Option on/off (default: off) and inactivity delay in minutes (default: 30).
- When the source becomes inactive (non-running, or unavailable beyond the grace period), the inactivity time starts.
- If the source becomes "running" again **after** the delay has passed, the stopwatch is reset and then started – a new session.
- If it becomes "running" again **before** the delay has passed, the stopwatch simply resumes – same session.
- The reset happens only at the start of the next session, so the time of the last session stays visible until then.
- Only applies when a source entity is configured.

## Events and triggers

One event type on the Home Assistant event bus: `stopwatch_plus_event`.

| `type` | Fired when |
|---|---|
| `started` | Started from `idle` |
| `paused` | Paused |
| `resumed` | Resumed from `paused` |
| `reset` | Reset (manually or by auto-reset) |
| `interval` | An interval of running time has been reached |

Event data: `type`, `entity_id`, `device_id`, `name`, `elapsed_seconds`, `elapsed_formatted` (e.g. `1:05:00`), `interval_count`, `source` (`action`, `button`, `source_entity`, `auto_reset`, `restore`).

Each `type` is also available as its own device trigger in the automation editor ("Stopwatch started", "Interval reached", …). Interval events fire at the exact moment, independent of the sensor update interval. A state trigger on the status sensor remains possible as a generic alternative.

## Setup (config flow / options)

Name; optional source entity and the states that count as "running"; grace period for unavailable source; auto-reset on/off and delay; interval in minutes (0 = off); sensor update interval. Everything can be changed later via "Configure" (options flow).

## Live display with infrequent sensor updates

Same principle as the core `timer`: the state changes rarely and the frontend does the counting. Attributes `accumulated_seconds` (total up to the last start) + `running_since` (time of the last start) → display = `accumulated_seconds + (now − running_since)`. A small dashboard card (JavaScript) reads these attributes and counts every second in the browser. The integration ships the card and registers it itself; no separate HACS installation required.

## Database note

An integration cannot exclude its own states from the recorder. With 1 s updates, Home Assistant would write about 3600 rows per hour of running time. Hence infrequent updates by default and the live display via the card; the README also documents `recorder: exclude:`.

## Repository structure (planned)

```
custom_components/stopwatch_plus/
  __init__.py, manifest.json, const.py, config_flow.py,
  stopwatch.py (state logic), sensor.py, button.py,
  device_trigger.py, services.yaml,
  translations/en.json, translations/de.json,
  frontend/stopwatch-card.js (phase 2)
docs/hacs-stopwatch-spec.md, docs/development.md
scripts/setup, scripts/develop (local development instance in WSL)
dev/configuration.yaml (configuration of the development instance)
hacs.json, README.md, LICENSE, .gitignore, .gitattributes
.github/workflows/validate.yml (HACS action + hassfest)
tests/ (pytest-homeassistant-custom-component)
```

## Translations

Custom integrations read their texts from `translations/<language>.json`; `translations/en.json` is the source of truth. There is no `strings.json` (that file is only used by core integrations).

## Open points

- Icon / branding for the HACS store (at the first release).

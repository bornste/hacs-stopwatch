# Development

## Local Home Assistant instance (WSL)

A separate Home Assistant instance runs inside WSL (Windows Subsystem for Linux, Ubuntu or Debian) and is reachable from the Windows browser at http://localhost:8123. It does not touch a production Home Assistant.

The instance lives in `~/ha-dev` inside WSL (virtual environment and configuration). The integration folder and `dev/configuration.yaml` are symlinked from the repository, so changes made in VS Code on Windows are picked up without copying.

### First-time setup

Open a WSL terminal and run:

```bash
cd /mnt/c/Dev/GitHub/bornste/hacs-stopwatch
bash scripts/setup
```

The script installs a few system packages (asks for the WSL password), installs [uv](https://docs.astral.sh/uv/) and Python 3.14, creates the virtual environment and installs the latest Home Assistant. To test against a specific version, set `HA_VERSION` (older releases may also need an older Python): `HA_VERSION=2026.1.0 PYTHON_VERSION=3.13 bash scripts/setup`.

### Start

```bash
cd /mnt/c/Dev/GitHub/bornste/hacs-stopwatch
bash scripts/develop
```

The first start takes a few minutes. Open http://localhost:8123 and create a local test user.

### After code changes

Python and translation changes require a restart of Home Assistant: Settings → System → Restart (top right), or `Ctrl+C` in the terminal and `bash scripts/develop` again.

### Dashboard card

The card lives in `custom_components/stopwatch_plus/www/stopwatch-plus-card.js` (plain JavaScript, no build step). Changes to it need no restart: the file is served straight from disk, so a reload of the browser page (Ctrl+F5) is enough. Errors show up in the browser console (F12).

### Automated tests

```bash
cd /mnt/c/Dev/GitHub/bornste/hacs-stopwatch
bash scripts/test
```

The first run creates a separate test environment in `~/ha-dev/test-venv`. Arguments are passed to pytest, e.g. `bash scripts/test -k interval`. The same tests run on GitHub for every push, against the minimum (`requirements_test_min.txt`) and the latest supported Home Assistant (`requirements_test.txt`).

### Simulated game console

`dev/configuration.yaml` provides `sensor.fake_console`, controlled by `input_select.fake_console_state` (`playing`, `idle`, `off`) and `input_boolean.fake_console_unavailable` (simulates a dropout). Use it as the source entity of a test stopwatch (section *Source entity*, running state `playing`). A short grace period (e.g. 20 seconds) and a short auto-reset delay (1 minute) make the behaviour easy to try out.

### Logs

Debug logging is enabled for `custom_components.stopwatch_plus`. The log is shown in the terminal and under Settings → System → Logs.

Note: Home Assistant no longer supports the "Core" installation method for production use. Running it from a virtual environment is fine for development.

## Releasing

Versions follow [Semantic Versioning](https://semver.org/): `0.x.y` while in development, a new minor version (e.g. `0.2.0`) for new features, a new patch version (e.g. `0.1.1`) for fixes. Git tags are the version with a leading `v`, e.g. `v0.1.0`.

### Development versions

Between two releases, `manifest.json` carries the **next** version with a `.devN` suffix (PEP 440 format), e.g. `0.2.0.dev1`, `0.2.0.dev2`, … Home Assistant shows it under Settings → Devices & services, so it is always clear which build is running.

- After a release, the next change sets the version to the next planned version with `.dev1` (e.g. after `0.1.0` → `0.2.0.dev1`).
- **Every further change set increases `N` by one** (`.dev1` → `.dev2`), together with an entry under `## [Unreleased]` in `CHANGELOG.md`.
- If a change turns out to need a bigger step (e.g. from `0.1.1.dev2` to a feature release), change the base version and keep counting: `0.2.0.dev3`.
- Development versions sort before the release (`0.2.0.dev3` < `0.2.0`), so HACS treats the release as an update.

The *Version and changelog* check accepts a `.devN` version when `CHANGELOG.md` has a `## [Unreleased]` section, and a release version only when it has a `## [x.y.z]` section.

### Publishing a release

1. **During development:** note every user-facing change under `## [Unreleased]` in `CHANGELOG.md` and count up the development version (see above).
2. **Prepare the release:** rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD`, add a new empty `## [Unreleased]` above it, update the links at the bottom, and set `"version": "x.y.z"` in `custom_components/stopwatch_plus/manifest.json` – **without** the `.devN` suffix. Commit and push; the *Version and changelog* check of the Validate workflow must be green.
3. **Publish on GitHub:** *Releases → Draft a new release*, choose tag `vx.y.z` → *Create new tag on publish* (target `main`), title `vx.y.z`, paste the changelog entry as description. Tick *Set as a pre-release* for versions that are not stable yet, then *Publish release*.
4. **Check:** the Release workflow compares the tag with `manifest.json` and `CHANGELOG.md`. If it fails, fix the version, delete the release and its tag, and publish again.

HACS offers every published release as a version; pre-releases only appear for users who enabled beta versions for the repository.

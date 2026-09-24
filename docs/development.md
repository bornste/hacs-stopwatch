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

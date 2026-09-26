/**
 * Stopwatch Plus dashboard card and tile card feature.
 *
 * Served by the integration and loaded automatically on every dashboard, so no
 * dashboard resource has to be added by hand. Plain JavaScript without a build step.
 *
 * - Card "custom:stopwatch-plus-card": live running time, status, controls and the
 *   last session, in a standard or a compact layout.
 * - Tile card feature "custom:stopwatch-plus-controls": live time and controls
 *   below a tile card of a stopwatch entity.
 *
 * The time counts live in the browser from the attributes of the elapsed time
 * sensor (accumulated_seconds + time since running_since), independent of the
 * sensor update interval.
 */

const DOMAIN = "stopwatch_plus";
const CARD_TYPE = "stopwatch-plus-card";
const FEATURE_TYPE = "stopwatch-plus-controls";
const BUTTONS = ["toggle", "stop", "reset"];
// Buttons of the card when the configuration does not list any
const DEFAULT_BUTTONS = { standard: BUTTONS, compact: ["toggle", "stop"] };

const STRINGS = {
  en: {
    cardName: "Stopwatch Plus",
    cardDescription: "Live running time of a stopwatch with its controls.",
    featureName: "Stopwatch Plus controls",
    entity: "Stopwatch",
    name: "Name",
    layout: "Layout",
    layoutStandard: "Standard",
    layoutCompact: "Compact",
    hideStatus: "Hide status",
    hideLastSession: "Hide last session",
    hideTime: "Hide time",
    buttons: "Buttons",
    start: "Start",
    resume: "Resume",
    pause: "Pause",
    stop: "Stop",
    reset: "Reset",
    toggle: "Start/Pause",
    lastSession: "Last session",
    idle: "Idle",
    running: "Running",
    paused: "Paused",
    notFound: "Stopwatch not found",
  },
  de: {
    cardName: "Stopwatch Plus",
    cardDescription: "Laufende Zeit einer Stoppuhr mit ihren Bedienelementen.",
    featureName: "Stopwatch Plus Bedienelemente",
    entity: "Stoppuhr",
    name: "Name",
    layout: "Layout",
    layoutStandard: "Standard",
    layoutCompact: "Kompakt",
    hideStatus: "Status ausblenden",
    hideLastSession: "Letzte Session ausblenden",
    hideTime: "Zeit ausblenden",
    buttons: "Buttons",
    start: "Starten",
    resume: "Fortsetzen",
    pause: "Pausieren",
    stop: "Stoppen",
    reset: "Zurücksetzen",
    toggle: "Start/Pause",
    lastSession: "Letzte Session",
    idle: "Bereit",
    running: "Läuft",
    paused: "Pausiert",
    notFound: "Stoppuhr nicht gefunden",
  },
};

/** Return the language of the user, falling back to the page language. */
function language(hass) {
  const lang = hass?.locale?.language || hass?.language || document.documentElement.lang;
  return (lang || "en").split("-")[0];
}

/** Translate a key of STRINGS, falling back to English. */
function localize(hass, key) {
  return (STRINGS[language(hass)] || STRINGS.en)[key] ?? STRINGS.en[key] ?? key;
}

/** Format seconds as HH:MM:SS, with days as d.HH:MM:SS from 24 hours on (like the integration). */
function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (value) => String(value).padStart(2, "0");
  const formatted = `${pad(hours)}:${pad(minutes)}:${pad(secs)}`;
  return days ? `${days}.${formatted}` : formatted;
}

/** Return the running time of the stopwatch right now, counted in the browser. */
function liveSeconds(stateObj) {
  const attributes = stateObj?.attributes || {};
  const accumulated = Number(attributes.accumulated_seconds) || 0;
  if (attributes.status !== "running" || !attributes.running_since) {
    return accumulated;
  }
  const since = Date.parse(attributes.running_since);
  if (Number.isNaN(since)) {
    return accumulated;
  }
  return accumulated + Math.max(0, (Date.now() - since) / 1000);
}

/** Whether an entity belongs to Stopwatch Plus. */
function isStopwatchEntity(hass, entityId) {
  return Boolean(entityId) && hass?.entities?.[entityId]?.platform === DOMAIN;
}

/**
 * Find the entities of the stopwatch that the given entity belongs to.
 *
 * Any entity of a stopwatch can be configured; the elapsed time sensor and the
 * last session sensor are found via the device and their translation keys.
 */
function resolveStopwatch(hass, entityId) {
  const result = { elapsed: undefined, lastSession: undefined, deviceId: undefined };
  const entry = hass?.entities?.[entityId];
  if (entry?.device_id) {
    result.deviceId = entry.device_id;
    for (const sibling of Object.values(hass.entities)) {
      if (sibling.device_id !== entry.device_id || sibling.platform !== DOMAIN) {
        continue;
      }
      if (sibling.translation_key === "elapsed") result.elapsed = sibling.entity_id;
      if (sibling.translation_key === "last_session") result.lastSession = sibling.entity_id;
    }
  }
  // Without registry data, the configured entity must be the elapsed time sensor
  if (!result.elapsed && hass?.states?.[entityId]?.attributes?.accumulated_seconds !== undefined) {
    result.elapsed = entityId;
  }
  return result;
}

/** Return the name of the stopwatch: configured name, device name or entity name. */
function stopwatchName(hass, config, stopwatch) {
  if (config.name) return config.name;
  const device = stopwatch.deviceId ? hass.devices?.[stopwatch.deviceId] : undefined;
  if (device) return device.name_by_user || device.name;
  return hass.states[stopwatch.elapsed]?.attributes?.friendly_name || stopwatch.elapsed;
}

/** Return the translated status of a stopwatch. */
function statusLabel(hass, stateObj) {
  const status = stateObj?.attributes?.status;
  if (hass.formatEntityAttributeValue) {
    const formatted = hass.formatEntityAttributeValue(stateObj, "status");
    if (formatted && formatted !== status) return formatted;
  }
  return localize(hass, status);
}

/** Call an action of the integration for the stopwatch. */
function callAction(hass, action, entityId) {
  hass.callService(DOMAIN, action, { entity_id: entityId });
}

/** Open the more-info dialog of an entity. */
function openMoreInfo(element, entityId) {
  element.dispatchEvent(
    new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true })
  );
}

/** Label and icon of a control button for the current status. */
function buttonInfo(hass, button, status) {
  if (button === "toggle") {
    if (status === "running") return { label: localize(hass, "pause"), icon: "mdi:pause" };
    return {
      label: localize(hass, status === "paused" ? "resume" : "start"),
      icon: "mdi:play",
    };
  }
  if (button === "stop") return { label: localize(hass, "stop"), icon: "mdi:stop" };
  return { label: localize(hass, "reset"), icon: "mdi:restore" };
}

/** Render the control buttons into a container and wire up their actions. */
function renderButtons(container, hass, buttons, entityId, status, className) {
  container.replaceChildren();
  for (const button of buttons) {
    const { label, icon } = buttonInfo(hass, button, status);
    const element = document.createElement("button");
    element.className = `${className} ${button}`;
    element.title = label;
    element.setAttribute("aria-label", label);
    // Stop and reset have nothing to do on an idle stopwatch
    element.disabled = button !== "toggle" && status === "idle";
    const iconElement = document.createElement("ha-icon");
    iconElement.icon = icon;
    iconElement.setAttribute("icon", icon);
    element.append(iconElement);
    element.addEventListener("click", (event) => {
      event.stopPropagation();
      callAction(hass, button, entityId);
    });
    container.append(element);
  }
}

/** Update a text node only when its content changes. */
function setText(element, text) {
  if (element && element.textContent !== text) element.textContent = text;
}

/** Base class: keeps the time counting every second while the stopwatch runs. */
class LiveTimeElement extends HTMLElement {
  connectedCallback() {
    this._updateTicker();
  }

  disconnectedCallback() {
    this._stopTicker();
  }

  _updateTicker() {
    const running = this._elapsedState()?.attributes?.status === "running";
    if (running && this.isConnected && !this._ticker) {
      this._ticker = window.setInterval(() => this._tick(), 1000);
    } else if ((!running || !this.isConnected) && this._ticker) {
      this._stopTicker();
    }
  }

  _stopTicker() {
    if (this._ticker) {
      window.clearInterval(this._ticker);
      this._ticker = undefined;
    }
  }

  _elapsedState() {
    return undefined;
  }

  _tick() {}
}

const CARD_STYLES = `
  ha-card {
    container-type: inline-size;
    overflow: hidden;
    height: 100%;
    box-sizing: border-box;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 12px;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
    cursor: pointer;
  }
  .icon {
    flex: none;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--state-color);
    background: color-mix(in srgb, var(--state-color) 20%, transparent);
  }
  .info {
    flex: 1;
    min-width: 0;
  }
  .name {
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .secondary {
    color: var(--secondary-text-color);
    font-size: 14px;
    line-height: 20px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .status {
    flex: none;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    line-height: 20px;
    color: var(--state-color);
    background: color-mix(in srgb, var(--state-color) 15%, transparent);
  }
  .time {
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    letter-spacing: 0.02em;
    cursor: pointer;
  }
  .standard .time {
    text-align: center;
    /* Shrinks on narrow cards, and further from one day on (d.HH:MM:SS) */
    font-size: min(48px, 24cqi);
    line-height: 56px;
  }
  .standard .time.long {
    font-size: min(48px, 19cqi);
  }
  .compact .time {
    flex: none;
    font-size: 20px;
    line-height: 24px;
  }
  .controls {
    display: flex;
    gap: 12px;
  }
  .control {
    flex: 1;
    min-width: 0;
    padding: 0;
    height: 42px;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-text-color);
    background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
    transition: background 0.2s;
  }
  .control.toggle {
    color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 20%, transparent);
  }
  .control:hover:not(:disabled) {
    background: color-mix(in srgb, var(--primary-text-color) 14%, transparent);
  }
  .control.toggle:hover:not(:disabled) {
    background: color-mix(in srgb, var(--primary-color) 30%, transparent);
  }
  .control:disabled {
    cursor: default;
    opacity: 0.4;
  }
  .compact .controls {
    gap: 8px;
  }
  .compact .control {
    flex: none;
    width: 40px;
    height: 40px;
    border-radius: 50%;
  }
  .last {
    text-align: center;
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  .compact {
    padding: 8px 12px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .row .header {
    flex: 1;
    min-width: 48px;
  }
  .warning {
    color: var(--warning-color);
  }
  /* Narrow cards, e.g. half of a section in a dashboard with several columns */
  @container (max-width: 170px) {
    .standard .status {
      display: none;
    }
  }
  @container (max-width: 240px) {
    .controls {
      gap: 8px;
    }
    .compact .secondary {
      display: none;
    }
    .compact {
      padding: 8px;
    }
    /* The name gives way first, the time and the buttons stay usable */
    .row .header {
      min-width: 0;
    }
    .compact .time {
      font-size: 14px;
    }
    .compact .control {
      width: 32px;
      height: 32px;
    }
  }
  @container (max-width: 150px) {
    .standard .icon {
      display: none;
    }
  }
  @container (max-width: 340px) {
    .compact .icon {
      display: none;
    }
    .compact .time {
      font-size: 16px;
    }
    .compact .controls {
      gap: 4px;
    }
    .compact .control {
      width: 36px;
      height: 36px;
    }
    .row {
      gap: 8px;
    }
  }
  [hidden] {
    display: none !important;
  }
`;

/** Colors of the statuses, from the Home Assistant theme. */
const STATUS_COLORS = {
  running: "var(--success-color, #43a047)",
  paused: "var(--warning-color, #ffa600)",
  idle: "var(--disabled-color, #9e9e9e)",
};

class StopwatchPlusCard extends LiveTimeElement {
  static getStubConfig(hass) {
    const entry = Object.values(hass?.entities || {}).find(
      (entity) => entity.platform === DOMAIN && entity.translation_key === "elapsed"
    );
    return { entity: entry?.entity_id || "", layout: "standard", buttons: [...BUTTONS] };
  }

  static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          required: true,
          selector: { entity: { filter: { integration: DOMAIN, domain: "sensor" } } },
        },
        { name: "name", selector: { text: {} } },
        {
          name: "layout",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "standard", label: localize(undefined, "layoutStandard") },
                { value: "compact", label: localize(undefined, "layoutCompact") },
              ],
            },
          },
        },
        {
          name: "buttons",
          selector: {
            select: {
              multiple: true,
              mode: "list",
              options: BUTTONS.map((button) => ({ value: button, label: localize(undefined, button) })),
            },
          },
        },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "hide_status", selector: { boolean: {} } },
            { name: "hide_last_session", selector: { boolean: {} } },
          ],
        },
      ],
      computeLabel: (schema) =>
        ({
          entity: localize(undefined, "entity"),
          name: localize(undefined, "name"),
          layout: localize(undefined, "layout"),
          hide_status: localize(undefined, "hideStatus"),
          buttons: localize(undefined, "buttons"),
          hide_last_session: localize(undefined, "hideLastSession"),
        })[schema.name],
    };
  }

  setConfig(config) {
    if (!config?.entity) {
      throw new Error("Please select a stopwatch (entity)");
    }
    this._config = { layout: "standard", ...config };
    this._built = false;
    this._render();
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    if (!this._config) return;
    this._stopwatch = resolveStopwatch(hass, this._config.entity);
    const ids = [this._stopwatch.elapsed, this._stopwatch.lastSession];
    // Re-render only when one of the stopwatch entities changed
    if (!previous || !this._built || ids.some((id) => id && previous.states[id] !== hass.states[id])) {
      this._render();
    }
  }

  getCardSize() {
    return this._config?.layout === "compact" ? 1 : 3;
  }

  getGridOptions() {
    if (this._config?.layout === "compact") {
      return { columns: 12, rows: 1, min_columns: 6, min_rows: 1 };
    }
    return { columns: 6, min_columns: 4 };
  }

  _elapsedState() {
    return this._stopwatch?.elapsed ? this._hass?.states[this._stopwatch.elapsed] : undefined;
  }

  _build() {
    const compact = this._config.layout === "compact";
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const header = `
      <div class="header">
        <div class="icon"><ha-icon icon="mdi:timer-outline"></ha-icon></div>
        <div class="info">
          <div class="name"></div>
          ${compact ? '<div class="secondary"></div>' : ""}
        </div>
        ${compact ? "" : '<div class="status"></div>'}
      </div>`;
    const body = compact
      ? `<div class="row">${header}<div class="time"></div><div class="controls"></div></div>`
      : `${header}<div class="time"></div><div class="controls"></div><div class="last"></div>`;
    this.shadowRoot.innerHTML = `
      <style>${CARD_STYLES}</style>
      <ha-card class="${compact ? "compact" : "standard"}">
        <div class="warning" hidden></div>
        ${body}
      </ha-card>`;
    const root = this.shadowRoot;
    this._elements = {
      card: root.querySelector("ha-card"),
      warning: root.querySelector(".warning"),
      header: root.querySelector(".header"),
      name: root.querySelector(".name"),
      secondary: root.querySelector(".secondary"),
      status: root.querySelector(".status"),
      time: root.querySelector(".time"),
      controls: root.querySelector(".controls"),
      last: root.querySelector(".last"),
      icon: root.querySelector(".icon ha-icon"),
    };
    const openDetails = () => this._stopwatch?.elapsed && openMoreInfo(this, this._stopwatch.elapsed);
    this._elements.header.addEventListener("click", openDetails);
    this._elements.time.addEventListener("click", openDetails);
    this._built = true;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this._built) this._build();
    const hass = this._hass;
    const config = this._config;
    const elements = this._elements;
    const stateObj = this._elapsedState();

    const found = Boolean(stateObj);
    elements.warning.hidden = found;
    for (const key of ["header", "time", "controls", "last"]) {
      if (elements[key]) elements[key].hidden = !found;
    }
    if (!found) {
      setText(elements.warning, `${localize(hass, "notFound")}: ${config.entity}`);
      this._updateTicker();
      return;
    }

    const status = stateObj.attributes.status || "idle";
    const compact = config.layout === "compact";
    elements.card.style.setProperty("--state-color", STATUS_COLORS[status] || STATUS_COLORS.idle);
    const icon = { running: "mdi:timer-play-outline", paused: "mdi:timer-pause-outline" }[status];
    elements.icon.icon = icon || "mdi:timer-outline";
    setText(elements.name, stopwatchName(hass, config, this._stopwatch));

    const lastState = this._stopwatch.lastSession ? hass.states[this._stopwatch.lastSession] : undefined;
    const lastSeconds = Number(lastState?.state);
    const lastText =
      lastState && Number.isFinite(lastSeconds)
        ? `${localize(hass, "lastSession")}: ${formatDuration(lastSeconds)}`
        : "";

    // Configured buttons in a fixed order, or the default of the layout
    const buttons = Array.isArray(config.buttons)
      ? BUTTONS.filter((button) => config.buttons.includes(button))
      : DEFAULT_BUTTONS[compact ? "compact" : "standard"];
    renderButtons(elements.controls, hass, buttons, this._stopwatch.elapsed, status, "control");
    elements.controls.hidden = buttons.length === 0;

    if (compact) {
      const parts = [];
      if (!config.hide_status) parts.push(statusLabel(hass, stateObj));
      if (!config.hide_last_session && lastText) parts.push(lastText);
      setText(elements.secondary, parts.join(" · "));
      elements.secondary.hidden = parts.length === 0;
    } else {
      setText(elements.status, statusLabel(hass, stateObj));
      elements.status.hidden = Boolean(config.hide_status);
      setText(elements.last, lastText);
      elements.last.hidden = Boolean(config.hide_last_session) || !lastText;
    }
    this._tick();
    this._updateTicker();
  }

  _tick() {
    const stateObj = this._elapsedState();
    if (!stateObj || !this._elements) return;
    const text = formatDuration(liveSeconds(stateObj));
    setText(this._elements.time, text);
    this._elements.time.classList.toggle("long", text.length > 8);
  }
}

const FEATURE_STYLES = `
  :host {
    display: block;
    container-type: inline-size;
  }
  .container {
    display: flex;
    gap: var(--feature-button-spacing, 12px);
    height: var(--feature-height, 42px);
  }
  .time {
    flex: 1.5 1 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    /* The time is never cut off; the buttons get narrower instead */
    min-width: max-content;
    padding: 0 12px;
    white-space: nowrap;
    border-radius: var(--feature-border-radius, 12px);
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    font-size: 16px;
    color: var(--primary-text-color);
    background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .button {
    flex: 1;
    min-width: 0;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--feature-border-radius, 12px);
    color: var(--feature-color, var(--primary-color));
    background: color-mix(in srgb, var(--feature-color, var(--primary-color)) 20%, transparent);
    transition: background 0.2s;
  }
  .button:hover:not(:disabled) {
    background: color-mix(in srgb, var(--feature-color, var(--primary-color)) 30%, transparent);
  }
  .button:disabled {
    cursor: default;
    opacity: 0.4;
  }
  @container (max-width: 280px) {
    .container {
      gap: 6px;
    }
    .time {
      padding: 0 8px;
      font-size: 14px;
    }
  }
  @container (max-width: 200px) {
    .time {
      padding: 0 6px;
      font-size: 12px;
    }
    .button {
      min-width: 28px;
    }
  }
  [hidden] {
    display: none !important;
  }
`;

class StopwatchPlusControls extends LiveTimeElement {
  static getStubConfig() {
    return { type: `custom:${FEATURE_TYPE}`, buttons: [...BUTTONS] };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "hide_time", selector: { boolean: {} } },
        {
          name: "buttons",
          selector: {
            select: {
              multiple: true,
              mode: "list",
              options: BUTTONS.map((button) => ({ value: button, label: localize(undefined, button) })),
            },
          },
        },
      ],
      computeLabel: (schema) =>
        ({ hide_time: localize(undefined, "hideTime"), buttons: localize(undefined, "buttons") })[
          schema.name
        ],
    };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { buttons: [...BUTTONS], ...config };
    this._render();
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    const entityId = this._context?.entity_id;
    if (entityId) this._stopwatch = resolveStopwatch(hass, entityId);
    const id = this._stopwatch?.elapsed;
    if (!previous || !this._built || (id && previous.states[id] !== hass.states[id])) {
      this._render();
    }
  }

  set context(context) {
    this._context = context;
    if (this._hass && context?.entity_id) {
      this._stopwatch = resolveStopwatch(this._hass, context.entity_id);
      this._render();
    }
  }

  get context() {
    return this._context;
  }

  // Older frontends pass the entity state instead of a context
  set stateObj(stateObj) {
    if (!this._context && stateObj?.entity_id) this.context = { entity_id: stateObj.entity_id };
  }

  _elapsedState() {
    return this._stopwatch?.elapsed ? this._hass?.states[this._stopwatch.elapsed] : undefined;
  }

  _render() {
    if (!this._config || !this._hass) return;
    const stateObj = this._elapsedState();
    if (!this._built) {
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `
        <style>${FEATURE_STYLES}</style>
        <div class="container"><div class="time"></div><div class="buttons" style="display: contents"></div></div>`;
      this._time = this.shadowRoot.querySelector(".time");
      this._buttons = this.shadowRoot.querySelector(".buttons");
      this._time.addEventListener("click", (event) => {
        event.stopPropagation();
        if (this._stopwatch?.elapsed) openMoreInfo(this, this._stopwatch.elapsed);
      });
      this._built = true;
    }
    this.hidden = !stateObj;
    if (!stateObj) return;
    const status = stateObj.attributes.status || "idle";
    const buttons = BUTTONS.filter((button) => (this._config.buttons || []).includes(button));
    renderButtons(this._buttons, this._hass, buttons, this._stopwatch.elapsed, status, "button");
    this._time.hidden = Boolean(this._config.hide_time);
    this._tick();
    this._updateTicker();
  }

  _tick() {
    const stateObj = this._elapsedState();
    if (stateObj && this._time) setText(this._time, formatDuration(liveSeconds(stateObj)));
  }
}

/**
 * Suggest the card for a stopwatch entity in the card picker ("By entity").
 *
 * Offered for every entity of a stopwatch; the cards use its elapsed time sensor.
 * The card picker shows them below "Community" as "Stopwatch Plus - <label>".
 */
function entitySuggestions(hass, entityId) {
  if (!isStopwatchEntity(hass, entityId)) return null;
  const entity = resolveStopwatch(hass, entityId).elapsed || entityId;
  return [
    {
      label: localize(hass, "layoutStandard"),
      config: { type: `custom:${CARD_TYPE}`, entity, layout: "standard", buttons: [...BUTTONS] },
    },
    {
      label: localize(hass, "layoutCompact"),
      config: {
        type: `custom:${CARD_TYPE}`,
        entity,
        layout: "compact",
        buttons: [...DEFAULT_BUTTONS.compact],
      },
    },
    {
      label: localize(hass, "featureName"),
      // The feature shows the live time, so the (less often updated) state is hidden
      config: {
        type: "tile",
        entity,
        hide_state: true,
        features: [{ type: `custom:${FEATURE_TYPE}` }],
      },
    },
  ];
}

/**
 * Wait until the Home Assistant frontend has started.
 *
 * The frontend replaces window.customElements with a scoped registry polyfill when
 * it starts. This file can load before that; elements defined too early would end
 * up in the old registry, and dashboards would report "Custom element doesn't exist".
 */
function whenFrontendReady() {
  if (customElements.get("home-assistant") || customElements.get("hc-main")) {
    return Promise.resolve();
  }
  return Promise.race([
    customElements.whenDefined("home-assistant"),
    // Cast receiver
    customElements.whenDefined("hc-main"),
    new Promise((resolve) => window.setTimeout(resolve, 5000)),
  ]);
}

whenFrontendReady().then(() => {
  if (!customElements.get(CARD_TYPE)) {
    customElements.define(CARD_TYPE, StopwatchPlusCard);
    window.customCards = window.customCards || [];
    window.customCards.push({
      type: CARD_TYPE,
      name: localize(undefined, "cardName"),
      description: localize(undefined, "cardDescription"),
      preview: true,
      documentationURL: "https://github.com/bornste/hacs-stopwatch",
      getEntitySuggestion: entitySuggestions,
    });
  }
  
  if (!customElements.get(FEATURE_TYPE)) {
    customElements.define(FEATURE_TYPE, StopwatchPlusControls);
    window.customCardFeatures = window.customCardFeatures || [];
    window.customCardFeatures.push({
      type: FEATURE_TYPE,
      name: localize(undefined, "featureName"),
      configurable: true,
      isSupported: (hass, context) => isStopwatchEntity(hass, context?.entity_id),
      // Older frontends call supported() with the entity state: accept the sensors
      // of a stopwatch, recognized by their attributes
      supported: (stateObj) =>
        stateObj?.attributes?.accumulated_seconds !== undefined ||
        stateObj?.attributes?.ended_at !== undefined,
    });
  }
});

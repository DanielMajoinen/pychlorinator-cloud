// PoolSpa intentionally excluded — it's a mode select (Pool vs Spa), not a
// per-timer toggleable equipment. Existing slots with PoolSpa in their
// equipment bitmap still round-trip via equipment_enabled; users just can't
// add it as a new chip from the card (use the Pool/Spa mode select instead).
const EQUIPMENT = [
  ["FilterPump", "Filter", "mdi:pump", "filter"],
  ["Heater", "Heater", "mdi:radiator", "heater"],
  ["Outlet1", "Outlet 1", "mdi:power-socket-au", "outlet"],
  ["Outlet2", "Outlet 2", "mdi:power-socket-au", "outlet"],
  ["Outlet3", "Outlet 3", "mdi:power-socket-au", "outlet"],
  ["Outlet4", "Outlet 4", "mdi:power-socket-au", "outlet"],
  ["Valve1", "Valve 1", "mdi:pipe-valve", "valve"],
  ["Valve2", "Valve 2", "mdi:pipe-valve", "valve"],
  ["Valve3", "Valve 3", "mdi:pipe-valve", "valve"],
  ["Valve4", "Valve 4", "mdi:pipe-valve", "valve"],
  ["Relay1", "Relay 1", "mdi:electric-switch", "relay"],
  ["Relay2", "Relay 2", "mdi:electric-switch", "relay"],
];

function formatLastSeen(iso) {
  if (!iso) return "never";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return "unknown";
  const seconds = Math.max(0, Math.round((Date.now() - ts) / 1000));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const SPEEDS = ["Low", "Medium", "High", "AI"];
const SEASONS = ["Summer", "Winter"];
const MODES = [
  ["equipment", "Equipment", "mdi:pump"],
  ["lighting", "Lighting", "mdi:lightbulb-on"],
  ["heat", "Heat Demand", "mdi:radiator"],
];
const LIGHT_SLOT_COUNT = 2;
const LIGHT_ZONES = [0, 1, 2, 3];

function css() {
  return `
    :host, ha-card { display: block; }
    ha-card { overflow: hidden; }
    .wrap { padding: 16px; display: grid; gap: 12px; }
    .head { display: grid; grid-template-columns: 1fr auto auto; gap: 8px; align-items: start; }
    .title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
    .sub { margin-top: 2px; font-size: 13px; color: var(--secondary-text-color); }
    .restored-badge { color: var(--disabled-text-color); font-size: 12px; }
    .status { border-left: 4px solid var(--warning-color); background: var(--secondary-background-color); color: var(--secondary-text-color); padding: 10px 12px; border-radius: 8px; font-size: 13px; }
    .icon-button { border: 0; background: none; color: var(--secondary-text-color); width: 40px; height: 40px; cursor: pointer; border-radius: 999px; }
    .icon-button:hover { background: var(--secondary-background-color); color: var(--primary-text-color); }
    .icon-button.spinning ha-icon { animation: spin 1.1s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .segmented { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .segment { border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); min-height: 40px; border-radius: 8px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 8px; font: inherit; }
    .segment.active { background: var(--accent-color, var(--primary-color)); color: var(--mdc-theme-on-primary, #fff); border-color: transparent; }
    .slots { border-top: 1px solid var(--divider-color); }
    .slot { border-bottom: 1px solid var(--divider-color); }
    .slot-row { min-height: 56px; display: grid; grid-template-columns: 40px minmax(64px, auto) minmax(92px, auto) 1fr auto 40px; gap: 10px; align-items: center; cursor: pointer; padding-right: 4px; }
    .edit-btn { width: 36px; height: 36px; border: 1px solid var(--divider-color); border-radius: 999px; background: var(--card-background-color); color: var(--secondary-text-color); cursor: pointer; display: inline-flex; align-items: center; justify-content: center; padding: 0; }
    .edit-btn:hover { background: var(--secondary-background-color); color: var(--primary-text-color); border-color: var(--primary-color); }
    .edit-btn.active { background: var(--primary-color); color: var(--mdc-theme-on-primary, #fff); border-color: transparent; }
    .slot-title { min-width: 0; display: grid; gap: 2px; }
    .slot-name { color: var(--secondary-text-color); font-size: 12px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; white-space: nowrap; }
    .slot-descriptor { color: var(--secondary-text-color); font-size: 0.8em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .slot-descriptor.disabled { color: var(--disabled-text-color); text-decoration: line-through; }
    .toggle { width: 32px; height: 32px; border: 0; background: transparent; color: var(--disabled-text-color); cursor: pointer; }
    .toggle.on { color: var(--primary-color); }
    .time { color: var(--primary-text-color); font: 500 16px Roboto Mono, ui-monospace, monospace; white-space: nowrap; }
    .slot.disabled .time { color: var(--disabled-text-color); }
    .equipment-line { min-width: 0; color: var(--secondary-text-color); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .speed { border: 1px solid var(--divider-color); border-radius: 999px; padding: 2px 8px; font-size: 12px; color: var(--secondary-text-color); white-space: nowrap; }
    .speed.ai { background: var(--primary-color); color: var(--mdc-theme-on-primary, #fff); border-color: transparent; }
    .editor { background: var(--secondary-background-color); border-radius: 8px; padding: 12px; display: grid; gap: 14px; margin-bottom: 12px; }
    .field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    label { display: grid; gap: 6px; color: var(--secondary-text-color); font-size: 11px; font-weight: 600; letter-spacing: 0; text-transform: uppercase; }
    input[type="time"], select { box-sizing: border-box; width: 100%; min-height: 52px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); color: var(--primary-text-color); padding: 10px 14px; font: 500 18px Roboto Mono, ui-monospace, monospace; }
    input[type="time"]:focus, select:focus { outline: 2px solid var(--primary-color); outline-offset: -2px; }
    input[type="time"]::-webkit-calendar-picker-indicator { padding: 12px; cursor: pointer; }
    .enabled-row { display: flex; align-items: center; gap: 8px; color: var(--primary-text-color); font-size: 14px; }
    .duration { color: var(--secondary-text-color); font-size: 13px; }
    .duration.warn { color: var(--warning-color); }
    .section-label { color: var(--secondary-text-color); font-size: 11px; font-weight: 600; letter-spacing: 0; text-transform: uppercase; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .chip { min-height: 34px; border-radius: 8px; border: 1px solid var(--divider-color); background: transparent; color: var(--secondary-text-color); display: inline-flex; align-items: center; gap: 6px; padding: 0 10px; cursor: pointer; font: inherit; }
    .chip.selected { color: var(--primary-text-color); border-color: var(--halo-chip-color); background: color-mix(in srgb, var(--halo-chip-color) 18%, transparent); }
    .dot { width: 8px; height: 8px; border-radius: 999px; background: var(--halo-chip-color); flex: 0 0 auto; }
    .speed-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .radio { border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); border-radius: 999px; min-height: 36px; padding: 0 12px; cursor: pointer; font: inherit; }
    .radio.selected { border-color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 16%, transparent); }
    .actions { display: flex; justify-content: flex-end; gap: 8px; }
    .text-button, .primary-button { min-height: 40px; border-radius: 8px; padding: 0 14px; cursor: pointer; font: inherit; }
    .text-button { border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color); }
    .primary-button { border: 0; background: var(--primary-color); color: var(--mdc-theme-on-primary, #fff); }
    .save-bar { position: sticky; bottom: 0; display: grid; gap: 10px; padding: 12px; border-left: 4px solid var(--warning-color); background: var(--card-background-color); box-shadow: 0 -2px 8px rgba(0,0,0,.16); }
    .save-row { display: flex; justify-content: space-between; gap: 8px; align-items: center; color: var(--secondary-text-color); font-size: 13px; }
    .error { color: var(--error-color); font-size: 13px; }
    @media (max-width: 480px) {
      .wrap { padding: 12px; }
      .head { grid-template-columns: 1fr auto; }
      .slot-row { grid-template-columns: 36px 1fr auto 36px; gap: 8px; }
      .slot-name { display: none; }
      .equipment-line { grid-column: 2 / 5; padding-bottom: 8px; }
      .field-grid { grid-template-columns: 1fr; }
      .actions, .save-row { flex-direction: column; align-items: stretch; }
      .text-button, .primary-button { width: 100%; }
    }
  `;
}

function colorFor(key, name) {
  const lower = String(name || "").toLowerCase();
  if (lower.includes("light") || lower.includes("lamp")) return "var(--halo-equipment-light, #FDD835)";
  if (key === "FilterPump") return "var(--halo-equipment-filter, #1E88E5)";
  if (key === "Heater") return "var(--halo-equipment-heater, #E53935)";
  if (key.startsWith("Outlet")) return "var(--halo-equipment-outlet, #8E24AA)";
  if (key.startsWith("Valve")) return "var(--halo-equipment-valve, #00897B)";
  if (key.startsWith("Relay")) return "var(--halo-equipment-relay, #6D4C41)";
  return "var(--primary-color)";
}

function timeString(hour, minute) {
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return "--:--";
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function durationLabel(startHour, startMinute, stopHour, stopMinute) {
  const start = startHour * 60 + startMinute;
  let stop = stopHour * 60 + stopMinute;
  let overnight = false;
  if (stop < start) {
    stop += 1440;
    overnight = true;
  }
  const mins = Math.max(0, stop - start);
  const hours = Math.floor(mins / 60);
  const minutes = mins % 60;
  return { text: `Duration: ${hours}h ${minutes}m${overnight ? " overnight" : ""}`, overnight };
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

class HaloTimerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = undefined;
    this._season = undefined;
    this._mode = "equipment";
    this._expanded = undefined;
    this._drafts = {};
    this._staged = {};
    this._heatDraft = undefined;
    this._saving = false;
    this._error = "";
  }

  _currentMode() {
    return this._mode || "equipment";
  }

  _changeMode(mode) {
    if (mode === this._currentMode()) return;
    if (Object.keys(this._staged).length && !confirm("Discard unsaved changes?")) {
      return;
    }
    this._mode = mode;
    this._expanded = undefined;
    this._drafts = {};
    this._staged = {};
    this._heatDraft = undefined;
    this._error = "";
    this._render();
  }

  setConfig(config) {
    this._config = config || {};
    this._season = this._config.default_season;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 8;
  }

  _entityId() {
    if (this._config.entity) return this._config.entity;
    const states = this._hass?.states || {};
    return Object.keys(states).find((entityId) => (
      entityId.startsWith("sensor.") && entityId.includes("equipment_timer_summary")
    ));
  }

  _attrs() {
    const entityId = this._entityId();
    return entityId ? this._hass?.states?.[entityId]?.attributes || {} : {};
  }

  _summaryState() {
    const entityId = this._entityId();
    return entityId ? this._hass?.states?.[entityId]?.state : undefined;
  }

  _connectedEntityId() {
    if (this._config.connected_entity) return this._config.connected_entity;
    const states = this._hass?.states || {};
    const entityId = this._entityId();
    if (entityId?.startsWith("sensor.")) {
      const derived = `binary_sensor.${entityId.slice("sensor.".length).replace(/_(equipment_|lighting_)?timer_summary$/, "_connected")}`;
      if (states[derived]) return derived;
    }
    return Object.keys(states).find((id) => (
      id.startsWith("binary_sensor.") && id.endsWith("_connected")
    ));
  }

  _writeBlockedReason() {
    const state = this._summaryState();
    if (!state || state === "unknown" || state === "unavailable") {
      return "Timer writes are disabled until a live timer summary is available.";
    }
    if (this._attrs().restored === true) {
      return "Timer writes are disabled while Home Assistant is showing restored timer data.";
    }
    const connectedId = this._connectedEntityId();
    const connectedState = connectedId ? this._hass?.states?.[connectedId]?.state : undefined;
    if (connectedState === "off" || connectedState === "false") {
      return "Timer writes are disabled while the Halo cloud connection is disconnected.";
    }
    return "";
  }

  _currentSeason() {
    const attrs = this._attrs();
    return this._season || attrs.current_season || attrs.season || "Summer";
  }

  _slotLabel(slotIndex) {
    const attrs = this._attrs();
    const labels = attrs.slot_labels || {};
    return labels[String(slotIndex)] || `Timer ${slotIndex + 1}`;
  }

  _slotDescriptor(slotIndex) {
    const attrs = this._attrs();
    const season = this._currentSeason();
    const key = season === "Winter" ? "winter_slot_descriptors" : "summer_slot_descriptors";
    const descriptors = attrs[key] || attrs.slot_descriptors || {};
    const value = descriptors[String(slotIndex)];
    return value ? String(value) : "";
  }

  _equipmentCatalog() {
    const attrs = this._attrs();
    const catalog = Array.isArray(attrs.equipment_catalog) ? attrs.equipment_catalog : [];
    if (catalog.length) return catalog;
    // Fallback when the lib hasn't sent the catalog yet (pre-rev integration).
    return EQUIPMENT.map(([key, label]) => ({ key, label, present: true, kind: "unknown" }));
  }

  _equipmentLabel(key) {
    const fromCatalog = this._equipmentCatalog().find((item) => item.key === key);
    if (fromCatalog?.label) return fromCatalog.label;
    return this._config.equipment_names?.[key] || EQUIPMENT.find((item) => item[0] === key)?.[1] || key;
  }

  _equipmentPresent(key) {
    const entry = this._equipmentCatalog().find((item) => item.key === key);
    if (!entry) return true;
    return entry.present !== false;
  }

  _refreshEntityId() {
    if (this._config.refresh_entity) return this._config.refresh_entity;
    const states = this._hass?.states || {};
    return Object.keys(states).find((entityId) => (
      entityId.startsWith("button.") && entityId.includes("refresh_timer_config")
    ));
  }

  async _pressRefresh() {
    if (!this._hass || this._refreshing) return;
    const refreshId = this._refreshEntityId();
    if (!refreshId) return;
    this._refreshing = true;
    this._render();
    try {
      await this._hass.callService("button", "press", { entity_id: refreshId });
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      // Hold the spinner briefly so the user sees the action register; the
      // readback then arrives on the next signalling session push.
      setTimeout(() => {
        this._refreshing = false;
        this._render();
      }, 800);
    }
  }

  _lightingZoneLabel(zoneIndex) {
    const names = this._attrs().lighting_zone_names || {};
    return names[String(zoneIndex)] || `Zone ${zoneIndex + 1}`;
  }

  _rawSlots() {
    const attrs = this._attrs();
    const season = this._currentSeason();
    const lighting = this._currentMode() === "lighting";
    const key = lighting
      ? (season === "Winter" ? "winter_light_slots" : "summer_light_slots")
      : (season === "Winter" ? "winter_slots" : "summer_slots");
    const slots = attrs[key];
    return Array.isArray(slots) ? slots : [];
  }

  _slots() {
    const lighting = this._currentMode() === "lighting";
    const raw = new Map(this._rawSlots().map((slot) => [Number(slot.slot_index), slot]));
    const count = lighting
      ? Math.max(Number(this._attrs().lighting_timer_slots || LIGHT_SLOT_COUNT), LIGHT_SLOT_COUNT)
      : Math.max(Number(this._attrs().equipment_timer_slots || 8), 8);
    const slots = [];
    for (let index = 0; index < count; index += 1) {
      const fallback = lighting
        ? {
            slot_index: index,
            active: false,
            zones_enabled: [],
            start_hour: 0,
            start_minute: 0,
            stop_hour: 0,
            stop_minute: 0,
          }
        : {
            slot_index: index,
            active: false,
            equipment_enabled: [],
            start_hour: 0,
            start_minute: 0,
            stop_hour: 0,
            stop_minute: 0,
            speed: "Medium",
          };
      const key = this._slotKey(index);
      slots.push({ ...fallback, ...(raw.get(index) || {}), ...(this._staged[key] || {}) });
    }
    return slots;
  }

  _slotKey(slotIndex) {
    return `${this._currentMode()}:${this._currentSeason()}:${slotIndex}`;
  }

  _equipmentName(key) {
    return this._equipmentLabel(key);
  }

  _draft(slot) {
    const key = this._slotKey(slot.slot_index);
    if (!this._drafts[key]) {
      this._drafts[key] = {
        ...slot,
        active: Boolean(slot.active),
        equipment_enabled: Array.from(slot.equipment_enabled || []),
        zones_enabled: Array.from(slot.zones_enabled || []),
        // 2026-05-26: SPEEDS now includes AI (was just Low/Medium/High).
        // Falls back to Medium only when the raw slot speed is something
        // we can't render — NOT when it's a legitimate value we just
        // forgot to list.
        speed: SPEEDS.includes(slot.speed) ? slot.speed : "Medium",
      };
    }
    return this._drafts[key];
  }

  _setDraft(slotIndex, patch) {
    const slot = this._slots().find((item) => item.slot_index === slotIndex);
    const draft = this._draft(slot);
    Object.assign(draft, patch);
    this._normalizeEquipmentDraft(draft);
    this._render();
  }

  _stageSlot(slotIndex) {
    const blocked = this._writeBlockedReason();
    if (blocked) {
      this._error = blocked;
      this._render();
      return;
    }
    const key = this._slotKey(slotIndex);
    this._normalizeEquipmentDraft(this._drafts[key]);
    this._staged[key] = { ...this._drafts[key] };
    this._expanded = undefined;
    this._error = "";
    this._render();
  }

  _normalizeEquipmentDraft(draft) {
    if (!draft || this._currentMode() === "lighting") return draft;
    const equipment = new Set(draft.equipment_enabled || []);
    if (!equipment.has("FilterPump") && draft.speed === "AI") {
      draft.speed = "Medium";
    }
    return draft;
  }

  _discardSlot(slotIndex) {
    const key = this._slotKey(slotIndex);
    delete this._drafts[key];
    delete this._staged[key];
    this._expanded = undefined;
    this._error = "";
    this._render();
  }

  _toggleEnabled(slotIndex) {
    const slot = this._slots().find((item) => item.slot_index === slotIndex);
    const draft = this._draft(slot);
    draft.active = !draft.active;
    this._staged[this._slotKey(slotIndex)] = { ...draft };
    this._render();
  }

  _changeSeason(season) {
    if (season === this._currentSeason()) return;
    if (Object.keys(this._staged).length && !confirm(`Discard unsaved ${this._currentSeason()} changes?`)) {
      return;
    }
    this._season = season;
    this._expanded = undefined;
    this._drafts = {};
    this._staged = {};
    this._error = "";
    this._render();
  }

  async _saveAll() {
    if (!this._hass || this._saving) return;
    const blocked = this._writeBlockedReason();
    if (blocked) {
      this._error = blocked;
      this._render();
      return;
    }
    this._saving = true;
    this._error = "";
    this._render();
    const deviceId = this._config.device_id;
    const lighting = this._currentMode() === "lighting";
    try {
      for (const staged of Object.values(this._staged)) {
        if (lighting) {
          await this._hass.callService("astralpool_halo_cloud", "write_lighting_timer", {
            ...(deviceId ? { device_id: deviceId } : {}),
            season: this._currentSeason(),
            slot_index: Number(staged.slot_index),
            enabled: Boolean(staged.active),
            start_hour: Number(staged.start_hour),
            start_min: Number(staged.start_minute),
            start_mode: "Normal",
            stop_hour: Number(staged.stop_hour),
            stop_min: Number(staged.stop_minute),
            stop_mode: "Normal",
            zones: Array.from(staged.zones_enabled || []).map(Number),
          });
        } else {
          const equipment = Array.from(staged.equipment_enabled || []);
          const pumpSpeed = equipment.includes("FilterPump") && SPEEDS.includes(staged.speed)
            ? staged.speed
            : "Medium";
          await this._hass.callService("astralpool_halo_cloud", "write_equipment_timer", {
            ...(deviceId ? { device_id: deviceId } : {}),
            season: this._currentSeason(),
            slot_index: Number(staged.slot_index),
            enabled: Boolean(staged.active),
            start_hour: Number(staged.start_hour),
            start_min: Number(staged.start_minute),
            start_mode: "Normal",
            stop_hour: Number(staged.stop_hour),
            stop_min: Number(staged.stop_minute),
            stop_mode: "Normal",
            equipment,
            pump_speed: pumpSpeed === "AI" && !equipment.includes("FilterPump") ? "Medium" : pumpSpeed,
          });
        }
      }
      this._staged = {};
      this._drafts = {};
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      this._saving = false;
      this._render();
    }
  }

  _renderSlot(slot, readOnly = false) {
    const enabled = Boolean(slot.active);
    const lighting = this._currentMode() === "lighting";
    const items = lighting
      ? Array.from(slot.zones_enabled || [])
      : Array.from(slot.equipment_enabled || []);
    const labels = lighting
      ? (items.map((z) => this._lightingZoneLabel(Number(z))).join(", ") || "no zones selected")
      : (items.map((key) => this._equipmentName(key)).join(", ") || "no equipment selected");
    const speed = slot.speed === "Medium" ? "Med" : slot.speed;
    const hasPump = !lighting && items.includes("FilterPump");
    const slotClass = enabled ? "slot" : "slot disabled";
    const descriptor = this._slotDescriptor(slot.slot_index);
    const isExpanded = this._expanded === slot.slot_index;
    return `
      <div class="${slotClass}">
        <div class="slot-row" ${readOnly ? "" : `data-expand="${slot.slot_index}"`}>
          ${readOnly ? `
            <span class="toggle ${enabled ? "on" : ""}">
              <ha-icon icon="${enabled ? "mdi:circle" : "mdi:circle-outline"}"></ha-icon>
            </span>
          ` : `
            <button class="toggle ${enabled ? "on" : ""}" data-toggle="${slot.slot_index}" title="Toggle slot">
              <ha-icon icon="${enabled ? "mdi:circle" : "mdi:circle-outline"}"></ha-icon>
            </button>
          `}
          <div class="slot-title">
            <div class="slot-name">${escapeHtml(this._slotLabel(slot.slot_index))}</div>
            ${descriptor ? `<div class="slot-descriptor ${descriptor === "Disabled" ? "disabled" : ""}">${escapeHtml(descriptor)}</div>` : ""}
          </div>
          <div class="time">${timeString(slot.start_hour, slot.start_minute)}-${timeString(slot.stop_hour, slot.stop_minute)}</div>
          <div class="equipment-line">${escapeHtml(labels)}</div>
          ${hasPump ? `<div class="speed">${escapeHtml(speed || "Med")}</div>` : ""}
          ${readOnly ? "" : `
            <button class="edit-btn ${isExpanded ? "active" : ""}" data-expand="${slot.slot_index}" title="${isExpanded ? "Close editor" : "Edit timer slot"}" aria-label="${isExpanded ? "Close editor" : "Edit timer slot"}">
              <ha-icon icon="${isExpanded ? "mdi:close" : "mdi:cog"}"></ha-icon>
            </button>
          `}
        </div>
        ${!readOnly && isExpanded ? this._renderEditor(slot) : ""}
      </div>
    `;
  }

  _renderEditor(slot) {
    const draft = this._draft(slot);
    const duration = durationLabel(
      Number(draft.start_hour),
      Number(draft.start_minute),
      Number(draft.stop_hour),
      Number(draft.stop_minute),
    );
    const lighting = this._currentMode() === "lighting";
    const selected = new Set(draft.equipment_enabled || []);
    const zoneSelected = new Set((draft.zones_enabled || []).map(Number));
    const selectorBlock = lighting
      ? `
        <div class="section-label">Light Zones</div>
        <div class="chips">
          ${LIGHT_ZONES.map((zone) => {
            const name = this._lightingZoneLabel(zone);
            const isSelected = zoneSelected.has(zone);
            return `
              <button class="chip ${isSelected ? "selected" : ""}" style="--halo-chip-color:var(--halo-equipment-light, #FDD835)" data-zone="${zone}" data-slot="${slot.slot_index}">
                <span class="dot"></span><ha-icon icon="mdi:lightbulb"></ha-icon>${escapeHtml(name)}
              </button>
            `;
          }).join("")}
        </div>`
      : `
        <div class="section-label">Equipment</div>
        <div class="chips">
          ${EQUIPMENT.filter(([key]) => {
            // Always keep selected chips visible even if presence reports false
            // — otherwise a stale selection becomes invisible/unrecoverable.
            return this._equipmentPresent(key) || selected.has(key);
          }).map(([key, label, icon]) => {
            const name = this._equipmentName(key) || label;
            const isSelected = selected.has(key);
            return `
              <button class="chip ${isSelected ? "selected" : ""}" style="--halo-chip-color:${colorFor(key, name)}" data-equipment="${key}" data-slot="${slot.slot_index}">
                <span class="dot"></span><ha-icon icon="${icon}"></ha-icon>${escapeHtml(name)}
              </button>
            `;
          }).join("")}
        </div>
        <div class="section-label">Pump speed</div>
        <div class="speed-row">
          ${SPEEDS.map((speed) => `
            <button class="radio ${draft.speed === speed ? "selected" : ""}" data-speed="${speed}" data-slot="${slot.slot_index}" ${selected.has("FilterPump") ? "" : "disabled"} title="${speed === "AI" ? "Let the controller pick the speed automatically" : speed}">
              ${speed === "AI" ? `<ha-icon icon="mdi:auto-fix"></ha-icon>` : ""}${escapeHtml(speed)}
            </button>
          `).join("")}
        </div>`;
    return `
      <div class="editor">
        <label class="enabled-row">
          <input type="checkbox" data-field="active" data-slot="${slot.slot_index}" ${draft.active ? "checked" : ""}>
          Enabled
        </label>
        <div class="field-grid">
          <label>Start time
            <input type="time" data-field="start_time" data-slot="${slot.slot_index}" value="${timeString(draft.start_hour, draft.start_minute)}">
          </label>
          <label>Stop time
            <input type="time" data-field="stop_time" data-slot="${slot.slot_index}" value="${timeString(draft.stop_hour, draft.stop_minute)}">
          </label>
        </div>
        <div class="duration ${duration.overnight ? "warn" : ""}">${duration.text}</div>
        ${selectorBlock}
        <div class="actions">
          <button class="text-button" data-discard="${slot.slot_index}">Discard</button>
          <button class="primary-button" data-stage="${slot.slot_index}">Save Slot</button>
        </div>
      </div>
    `;
  }

  _heatEntityId() {
    if (this._config.heat_entity) return this._config.heat_entity;
    const states = this._hass?.states || {};
    return Object.keys(states).find((id) => (
      id.startsWith("sensor.") && id.includes("heat_demand_schedule")
    ));
  }

  _heatAttrs() {
    const id = this._heatEntityId();
    return id ? this._hass?.states?.[id]?.attributes || {} : {};
  }

  _getHeatDraft() {
    if (!this._heatDraft) {
      const a = this._heatAttrs();
      this._heatDraft = {
        enabled: Boolean(a.enabled),
        window_enabled: Boolean(a.window_enabled),
        activated: Boolean(a.activated),
        start_hour: Number(a.window_start_hour || 0),
        start_minute: Number(a.window_start_minute || 0),
        stop_hour: Number(a.window_stop_hour || 0),
        stop_minute: Number(a.window_stop_minute || 0),
      };
    }
    return this._heatDraft;
  }

  _heatSub() {
    const a = this._heatAttrs();
    if (a.enabled === undefined || a.enabled === null) return "no heat-demand data yet";
    if (!a.enabled) return "Heat demand off";
    if (!a.window_enabled) return "Heat demand on · all day";
    return `Heat demand on · ${timeString(a.window_start_hour, a.window_start_minute)}-${timeString(a.window_stop_hour, a.window_stop_minute)}`;
  }

  _renderHeat() {
    const d = this._getHeatDraft();
    return `
      <div class="editor">
        <label class="enabled-row">
          <input type="checkbox" data-heat="enabled" ${d.enabled ? "checked" : ""}> Heat Demand Enabled
        </label>
        <label class="enabled-row">
          <input type="checkbox" data-heat="activated" ${d.activated ? "checked" : ""}> Activated (heating on now)
        </label>
        <label class="enabled-row">
          <input type="checkbox" data-heat="window_enabled" ${d.window_enabled ? "checked" : ""}> Restrict to time window
        </label>
        ${d.window_enabled ? `
          <div class="field-grid">
            <label>Start time
              <input type="time" data-heat="start_time" value="${timeString(d.start_hour, d.start_minute)}">
            </label>
            <label>Stop time
              <input type="time" data-heat="stop_time" value="${timeString(d.stop_hour, d.stop_minute)}">
            </label>
          </div>` : `<div class="duration">Heat demand runs 24h when no window is set.</div>`}
        <div class="actions">
          <button class="text-button" data-heat-discard>Reset</button>
          <button class="primary-button" data-heat-save>${this._saving ? "Saving..." : "Save Heat Demand"}</button>
        </div>
        ${this._error ? `<div class="error">${escapeHtml(this._error)}</div>` : ""}
      </div>`;
  }

  async _saveHeat() {
    if (!this._hass || this._saving) return;
    this._saving = true;
    this._error = "";
    this._render();
    const d = this._getHeatDraft();
    const deviceId = this._config.device_id;
    try {
      await this._hass.callService("astralpool_halo_cloud", "write_heat_demand", {
        ...(deviceId ? { device_id: deviceId } : {}),
        enabled: Boolean(d.enabled),
        window_enabled: Boolean(d.window_enabled),
        activated: Boolean(d.activated),
        start_hour: Number(d.start_hour),
        start_minute: Number(d.start_minute),
        stop_hour: Number(d.stop_hour),
        stop_minute: Number(d.stop_minute),
      });
      this._heatDraft = undefined;
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      this._saving = false;
      this._render();
    }
  }

  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._entityId();
    if (!this._hass || !entityId) {
      this.shadowRoot.innerHTML = `<style>${css()}</style><ha-card><div class="wrap">Set an equipment timer summary entity.</div></ha-card>`;
      return;
    }
    const mode = this._currentMode();
    const attrs = this._attrs();
    const refreshId = this._refreshEntityId();
    const titleByMode = {
      equipment: "Pool Equipment Timers",
      lighting: "Pool Lighting Timers",
      heat: "Heater Demand",
    };

    const modeBar = `
      <div class="segmented">
        ${MODES.map(([key, label, icon]) => `
          <button class="segment ${key === mode ? "active" : ""}" data-mode="${key}">
            <ha-icon icon="${icon}"></ha-icon>${label}
          </button>
        `).join("")}
      </div>`;

    let sub = "";
    let body = "";
    if (mode === "heat") {
      sub = escapeHtml(this._heatSub());
      body = this._renderHeat();
    } else {
      const season = this._currentSeason();
      const slots = this._slots();
      const active = slots.filter((slot) => slot.active).length;
      const stagedCount = Object.keys(this._staged).length;
      const restored = attrs.restored === true;
      const writeBlocked = this._writeBlockedReason();
      const lastSeenSource = restored ? attrs.restored_from_at || attrs.timer_config_last_seen : attrs.timer_config_last_seen;
      const lastSeen = formatLastSeen(lastSeenSource);
      const restoredBadge = restored ? ` <span class="restored-badge">(restored - refreshing...)</span>` : "";
      const noun = mode === "lighting" ? "lighting" : "equipment";
      sub = `${escapeHtml(season)} · ${active} of ${slots.length} active · ${noun} · updated ${escapeHtml(lastSeen)}${restoredBadge}`;
      body = `
        ${writeBlocked ? `<div class="status">${escapeHtml(writeBlocked)}</div>` : ""}
        ${writeBlocked ? "" : `<div class="segmented">
          ${SEASONS.map((item) => `
            <button class="segment ${item === season ? "active" : ""}" data-season="${item}">
              <ha-icon icon="${item === "Summer" ? "mdi:white-balance-sunny" : "mdi:snowflake"}"></ha-icon>${item}
            </button>
          `).join("")}
        </div>`}
        <div class="slots">${slots.map((slot) => this._renderSlot(slot, Boolean(writeBlocked))).join("")}</div>
        ${stagedCount && !writeBlocked ? `
          <div class="save-bar">
            <div class="save-row">
              <span>${stagedCount} slot${stagedCount === 1 ? "" : "s"} have unsaved changes</span>
              <span>
                <button class="text-button" data-discard-all>Discard All</button>
                <button class="primary-button" data-save-all>${this._saving ? "Saving..." : `Save (${stagedCount})`}</button>
              </span>
            </div>
            ${this._error ? `<div class="error">${escapeHtml(this._error)}</div>` : ""}
          </div>
        ` : ""}`;
    }

    this.shadowRoot.innerHTML = `
      <style>${css()}</style>
      <ha-card>
        <div class="wrap">
          <div class="head">
            <div>
              <div class="title">${escapeHtml(this._config.name || titleByMode[mode] || "Pool Timers")}</div>
              <div class="sub">${sub}</div>
            </div>
            ${refreshId ? `
              <button class="icon-button ${this._refreshing ? "spinning" : ""}" data-refresh title="Refresh timer config">
                <ha-icon icon="mdi:refresh"></ha-icon>
              </button>
            ` : ""}
            <button class="icon-button" data-more-info="${entityId}" title="Open timer summary">
              <ha-icon icon="mdi:cog-outline"></ha-icon>
            </button>
          </div>
          ${modeBar}
          ${body}
        </div>
      </ha-card>
    `;
  }

  connectedCallback() {
    this.shadowRoot.addEventListener("click", (event) => {
      const target = event.target.closest("button, .slot-row");
      if (!target) return;
      if (target.dataset.moreInfo) {
        this.dispatchEvent(new CustomEvent("hass-more-info", {
          bubbles: true,
          composed: true,
          detail: { entityId: target.dataset.moreInfo },
        }));
      } else if (target.dataset.refresh !== undefined) {
        this._pressRefresh();
      } else if (target.dataset.mode) {
        this._changeMode(target.dataset.mode);
      } else if (target.dataset.season) {
        this._changeSeason(target.dataset.season);
      } else if (target.dataset.heatSave !== undefined) {
        this._saveHeat();
      } else if (target.dataset.heatDiscard !== undefined) {
        this._heatDraft = undefined;
        this._error = "";
        this._render();
      } else if (target.dataset.zone !== undefined) {
        if (this._writeBlockedReason()) return;
        const slot = Number(target.dataset.slot);
        const draft = this._draft(this._slots().find((item) => item.slot_index === slot));
        const zones = new Set((draft.zones_enabled || []).map(Number));
        const zone = Number(target.dataset.zone);
        if (zones.has(zone)) zones.delete(zone);
        else zones.add(zone);
        this._setDraft(slot, { zones_enabled: Array.from(zones) });
      } else if (target.dataset.toggle) {
        if (this._writeBlockedReason()) return;
        event.stopPropagation();
        this._toggleEnabled(Number(target.dataset.toggle));
      } else if (target.dataset.expand) {
        if (this._writeBlockedReason()) return;
        // Toggle: clicking the row or the cog again collapses an open editor.
        const next = Number(target.dataset.expand);
        this._expanded = this._expanded === next ? undefined : next;
        this._render();
      } else if (target.dataset.equipment) {
        if (this._writeBlockedReason()) return;
        const slot = Number(target.dataset.slot);
        const draft = this._draft(this._slots().find((item) => item.slot_index === slot));
        const equipment = new Set(draft.equipment_enabled || []);
        if (equipment.has(target.dataset.equipment)) equipment.delete(target.dataset.equipment);
        else equipment.add(target.dataset.equipment);
        this._setDraft(slot, { equipment_enabled: Array.from(equipment) });
      } else if (target.dataset.speed) {
        if (this._writeBlockedReason()) return;
        const slot = Number(target.dataset.slot);
        const draft = this._draft(this._slots().find((item) => item.slot_index === slot));
        if (target.dataset.speed === "AI" && !(draft.equipment_enabled || []).includes("FilterPump")) return;
        this._setDraft(slot, { speed: target.dataset.speed });
      } else if (target.dataset.stage) {
        this._stageSlot(Number(target.dataset.stage));
      } else if (target.dataset.discard) {
        this._discardSlot(Number(target.dataset.discard));
      } else if (target.dataset.saveAll !== undefined) {
        this._saveAll();
      } else if (target.dataset.discardAll !== undefined) {
        this._staged = {};
        this._drafts = {};
        this._error = "";
        this._render();
      }
    });
    this.shadowRoot.addEventListener("change", (event) => {
      const target = event.target;
      if (target.dataset.heat) {
        const d = this._getHeatDraft();
        if (target.dataset.heat === "enabled") d.enabled = target.checked;
        else if (target.dataset.heat === "activated") d.activated = target.checked;
        else if (target.dataset.heat === "window_enabled") {
          d.window_enabled = target.checked;
          this._render();
        } else if (target.dataset.heat === "start_time") {
          const [hour, minute] = target.value.split(":").map(Number);
          d.start_hour = hour;
          d.start_minute = minute;
        } else if (target.dataset.heat === "stop_time") {
          const [hour, minute] = target.value.split(":").map(Number);
          d.stop_hour = hour;
          d.stop_minute = minute;
        }
        return;
      }
      const slot = Number(target.dataset.slot);
      if (!Number.isFinite(slot)) return;
      if (target.dataset.field === "active") {
        this._setDraft(slot, { active: target.checked });
      } else if (target.dataset.field === "start_time") {
        const [hour, minute] = target.value.split(":").map(Number);
        this._setDraft(slot, { start_hour: hour, start_minute: minute });
      } else if (target.dataset.field === "stop_time") {
        const [hour, minute] = target.value.split(":").map(Number);
        this._setDraft(slot, { stop_hour: hour, stop_minute: minute });
      }
    });
  }
}

customElements.define("halo-timer-card", HaloTimerCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "halo-timer-card",
  name: "Halo Timer Card",
  description: "Edit AstralPool Halo equipment + lighting timers and the heat-demand schedule.",
});

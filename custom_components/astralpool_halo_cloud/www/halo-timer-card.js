const EQUIPMENT = [
  ["PoolSpa", "Pool/Spa", "mdi:pool", "pool"],
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

const SPEEDS = ["Low", "Medium", "High"];
const SEASONS = ["Summer", "Winter"];

function css() {
  return `
    :host, ha-card { display: block; }
    ha-card { overflow: hidden; }
    .wrap { padding: 16px; display: grid; gap: 12px; }
    .head { display: grid; grid-template-columns: 1fr auto auto; gap: 8px; align-items: start; }
    .title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
    .sub { margin-top: 2px; font-size: 13px; color: var(--secondary-text-color); }
    .restored-badge { color: var(--disabled-text-color); font-size: 12px; }
    .icon-button { border: 0; background: none; color: var(--secondary-text-color); width: 40px; height: 40px; cursor: pointer; border-radius: 999px; }
    .icon-button:hover { background: var(--secondary-background-color); color: var(--primary-text-color); }
    .icon-button.spinning ha-icon { animation: spin 1.1s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .segmented { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .segment { border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); min-height: 40px; border-radius: 8px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 8px; font: inherit; }
    .segment.active { background: var(--accent-color, var(--primary-color)); color: var(--mdc-theme-on-primary, #fff); border-color: transparent; }
    .slots { border-top: 1px solid var(--divider-color); }
    .slot { border-bottom: 1px solid var(--divider-color); }
    .slot-row { min-height: 56px; display: grid; grid-template-columns: 40px minmax(64px, auto) minmax(92px, auto) 1fr auto; gap: 10px; align-items: center; cursor: pointer; }
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
    input[type="time"], select { box-sizing: border-box; width: 100%; min-height: 40px; border: 1px solid var(--divider-color); border-radius: 6px; background: var(--card-background-color); color: var(--primary-text-color); padding: 6px 8px; font: inherit; }
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
      .slot-row { grid-template-columns: 36px 1fr auto; gap: 8px; }
      .slot-name { display: none; }
      .equipment-line { grid-column: 2 / 4; padding-bottom: 8px; }
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
    this._expanded = undefined;
    this._drafts = {};
    this._staged = {};
    this._saving = false;
    this._error = "";
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

  _rawSlots() {
    const attrs = this._attrs();
    const season = this._currentSeason();
    const key = season === "Winter" ? "winter_slots" : "summer_slots";
    const slots = attrs[key];
    return Array.isArray(slots) ? slots : [];
  }

  _slots() {
    const raw = new Map(this._rawSlots().map((slot) => [Number(slot.slot_index), slot]));
    const count = Math.max(Number(this._attrs().equipment_timer_slots || 8), 8);
    const slots = [];
    for (let index = 0; index < count; index += 1) {
      const fallback = {
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
    return `${this._currentSeason()}:${slotIndex}`;
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
        speed: SPEEDS.includes(slot.speed) ? slot.speed : "Medium",
      };
    }
    return this._drafts[key];
  }

  _setDraft(slotIndex, patch) {
    const slot = this._slots().find((item) => item.slot_index === slotIndex);
    const draft = this._draft(slot);
    Object.assign(draft, patch);
    this._render();
  }

  _stageSlot(slotIndex) {
    const key = this._slotKey(slotIndex);
    this._staged[key] = { ...this._drafts[key] };
    this._expanded = undefined;
    this._error = "";
    this._render();
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
    this._saving = true;
    this._error = "";
    this._render();
    const deviceId = this._config.device_id;
    try {
      for (const staged of Object.values(this._staged)) {
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
          equipment: Array.from(staged.equipment_enabled || []),
          pump_speed: staged.speed || "Medium",
        });
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

  _renderSlot(slot) {
    const enabled = Boolean(slot.active);
    const equipment = Array.from(slot.equipment_enabled || []);
    const labels = equipment.map((key) => this._equipmentName(key)).join(", ") || "no equipment selected";
    const speed = slot.speed === "Medium" ? "Med" : slot.speed;
    const hasPump = equipment.includes("FilterPump");
    const slotClass = enabled ? "slot" : "slot disabled";
    const descriptor = this._slotDescriptor(slot.slot_index);
    return `
      <div class="${slotClass}">
        <div class="slot-row" data-expand="${slot.slot_index}">
          <button class="toggle ${enabled ? "on" : ""}" data-toggle="${slot.slot_index}" title="Toggle slot">
            <ha-icon icon="${enabled ? "mdi:circle" : "mdi:circle-outline"}"></ha-icon>
          </button>
          <div class="slot-title">
            <div class="slot-name">${escapeHtml(this._slotLabel(slot.slot_index))}</div>
            ${descriptor ? `<div class="slot-descriptor ${descriptor === "Disabled" ? "disabled" : ""}">${escapeHtml(descriptor)}</div>` : ""}
          </div>
          <div class="time">${timeString(slot.start_hour, slot.start_minute)}-${timeString(slot.stop_hour, slot.stop_minute)}</div>
          <div class="equipment-line">${escapeHtml(labels)}</div>
          ${hasPump ? `<div class="speed">${escapeHtml(speed || "Med")}</div>` : ""}
        </div>
        ${this._expanded === slot.slot_index ? this._renderEditor(slot) : ""}
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
    const selected = new Set(draft.equipment_enabled || []);
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
        <div class="section-label">Equipment</div>
        <div class="chips">
          ${EQUIPMENT.filter(([key]) => {
            // Always keep selected chips visible even if presence reports false
            //. otherwise a stale selection becomes invisible/unrecoverable.
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
            <button class="radio ${draft.speed === speed ? "selected" : ""}" data-speed="${speed}" data-slot="${slot.slot_index}" ${selected.has("FilterPump") ? "" : "disabled"}>
              ${escapeHtml(speed)}
            </button>
          `).join("")}
        </div>
        <div class="actions">
          <button class="text-button" data-discard="${slot.slot_index}">Discard</button>
          <button class="primary-button" data-stage="${slot.slot_index}">Save Slot</button>
        </div>
      </div>
    `;
  }

  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._entityId();
    if (!this._hass || !entityId) {
      this.shadowRoot.innerHTML = `<style>${css()}</style><ha-card><div class="wrap">Set an equipment timer summary entity.</div></ha-card>`;
      return;
    }
    const attrs = this._attrs();
    const season = this._currentSeason();
    const slots = this._slots();
    const active = slots.filter((slot) => slot.active).length;
    const stagedCount = Object.keys(this._staged).length;
    const restored = attrs.restored === true;
    const lastSeenSource = restored ? attrs.restored_from_at || attrs.timer_config_last_seen : attrs.timer_config_last_seen;
    const lastSeen = formatLastSeen(lastSeenSource);
    const refreshId = this._refreshEntityId();
    const restoredBadge = restored ? ` <span class="restored-badge">(restored - refreshing...)</span>` : "";
    this.shadowRoot.innerHTML = `
      <style>${css()}</style>
      <ha-card>
        <div class="wrap">
          <div class="head">
            <div>
              <div class="title">${escapeHtml(this._config.name || "Pool Equipment Timers")}</div>
              <div class="sub">${escapeHtml(season)} · ${active} of ${slots.length} active · updated ${escapeHtml(lastSeen)}${restoredBadge}</div>
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
          <div class="segmented">
            ${SEASONS.map((item) => `
              <button class="segment ${item === season ? "active" : ""}" data-season="${item}">
                <ha-icon icon="${item === "Summer" ? "mdi:white-balance-sunny" : "mdi:snowflake"}"></ha-icon>${item}
              </button>
            `).join("")}
          </div>
          <div class="slots">${slots.map((slot) => this._renderSlot(slot)).join("")}</div>
          ${stagedCount ? `
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
          ` : ""}
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
      } else if (target.dataset.season) {
        this._changeSeason(target.dataset.season);
      } else if (target.dataset.toggle) {
        event.stopPropagation();
        this._toggleEnabled(Number(target.dataset.toggle));
      } else if (target.dataset.expand) {
        this._expanded = Number(target.dataset.expand);
        this._render();
      } else if (target.dataset.equipment) {
        const slot = Number(target.dataset.slot);
        const draft = this._draft(this._slots().find((item) => item.slot_index === slot));
        const equipment = new Set(draft.equipment_enabled || []);
        if (equipment.has(target.dataset.equipment)) equipment.delete(target.dataset.equipment);
        else equipment.add(target.dataset.equipment);
        this._setDraft(slot, { equipment_enabled: Array.from(equipment) });
      } else if (target.dataset.speed) {
        this._setDraft(Number(target.dataset.slot), { speed: target.dataset.speed });
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
  description: "Edit AstralPool Halo equipment timer slots.",
});

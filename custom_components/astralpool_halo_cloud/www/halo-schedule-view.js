const EQUIPMENT_ORDER = [
  ["PoolSpa", "Pool/Spa", "mdi:pool", "var(--primary-color)"],
  ["FilterPump", "Filter", "mdi:pump", "var(--halo-equipment-filter, #1E88E5)"],
  ["Heater", "Heater", "mdi:radiator", "var(--halo-equipment-heater, #E53935)"],
  ["Outlet1", "Outlet 1", "mdi:power-socket-au", "var(--halo-equipment-outlet, #8E24AA)"],
  ["Outlet2", "Outlet 2", "mdi:power-socket-au", "var(--halo-equipment-outlet, #8E24AA)"],
  ["Outlet3", "Outlet 3", "mdi:power-socket-au", "var(--halo-equipment-outlet, #8E24AA)"],
  ["Outlet4", "Outlet 4", "mdi:power-socket-au", "var(--halo-equipment-outlet, #8E24AA)"],
  ["Valve1", "Valve 1", "mdi:pipe-valve", "var(--halo-equipment-valve, #00897B)"],
  ["Valve2", "Valve 2", "mdi:pipe-valve", "var(--halo-equipment-valve, #00897B)"],
  ["Valve3", "Valve 3", "mdi:pipe-valve", "var(--halo-equipment-valve, #00897B)"],
  ["Valve4", "Valve 4", "mdi:pipe-valve", "var(--halo-equipment-valve, #00897B)"],
  ["Relay1", "Relay 1", "mdi:electric-switch", "var(--halo-equipment-relay, #6D4C41)"],
  ["Relay2", "Relay 2", "mdi:electric-switch", "var(--halo-equipment-relay, #6D4C41)"],
];

function styles() {
  return `
    ha-card { display: block; overflow: hidden; }
    .wrap { padding: 16px; display: grid; gap: 12px; }
    .head { display: flex; justify-content: space-between; gap: 12px; align-items: start; }
    .title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
    .sub { margin-top: 2px; font-size: 13px; color: var(--secondary-text-color); }
    .mode { display: inline-grid; grid-template-columns: 1fr 1fr; border: 1px solid var(--divider-color); border-radius: 8px; overflow: hidden; min-width: 132px; }
    .mode button { border: 0; background: var(--card-background-color); color: var(--primary-text-color); min-height: 36px; cursor: pointer; font: inherit; }
    .mode button.active { background: var(--primary-color); color: var(--mdc-theme-on-primary, #fff); }
    .timeline { overflow-x: auto; background: var(--secondary-background-color); border-radius: 8px; padding: 8px 0; }
    svg { min-width: 680px; width: 100%; height: auto; display: block; font-family: var(--ha-card-font-family, Roboto, sans-serif); }
    .axis { fill: var(--secondary-text-color); font-size: 10px; }
    .lane-label { fill: var(--primary-text-color); font-size: 12px; }
    .grid { stroke: var(--divider-color); stroke-width: 1; }
    .bar { rx: 5; ry: 5; cursor: pointer; }
    .bar.inactive { opacity: .36; }
    .slot-label { fill: var(--mdc-theme-on-primary, #fff); font-size: 11px; font-weight: 500; pointer-events: none; }
    .legend { display: flex; flex-wrap: wrap; gap: 8px 12px; font-size: 12px; color: var(--secondary-text-color); }
    .legend-item { display: inline-flex; align-items: center; gap: 6px; min-height: 24px; }
    .dot { width: 8px; height: 8px; border-radius: 999px; background: var(--legend-color); }
    .empty { color: var(--secondary-text-color); padding: 16px 0; text-align: center; }
    @media (max-width: 480px) {
      .wrap { padding: 12px; }
      .head { flex-direction: column; }
      .mode { width: 100%; }
    }
  `;
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

function minutes(slot, field) {
  if (field === "start") return Number(slot.start_hour || 0) * 60 + Number(slot.start_minute || 0);
  return Number(slot.stop_hour || 0) * 60 + Number(slot.stop_minute || 0);
}

function normaliseSegments(slot) {
  const start = minutes(slot, "start");
  let stop = minutes(slot, "stop");
  if (stop < start) {
    return [
      [start, 1440],
      [0, stop],
    ];
  }
  if (stop === start) return [];
  return [[start, stop]];
}

class HaloScheduleView extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = undefined;
    this._view = "day";
  }

  setConfig(config) {
    this._config = config || {};
    this._view = this._config.default_view || "day";
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 6;
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

  _season() {
    return this._attrs().current_season || this._attrs().season || "Summer";
  }

  _slots() {
    const attrs = this._attrs();
    const season = this._season();
    const key = season === "Winter" ? "winter_slots" : "summer_slots";
    const slots = attrs[key];
    return (Array.isArray(slots) ? slots : []).filter((slot) => slot && slot.active);
  }

  _equipmentName(key) {
    return this._config.equipment_names?.[key] || EQUIPMENT_ORDER.find((item) => item[0] === key)?.[1] || key;
  }

  _lanes() {
    const used = new Set();
    for (const slot of this._slots()) {
      for (const key of slot.equipment_enabled || []) used.add(key);
    }
    return EQUIPMENT_ORDER.filter(([key]) => used.has(key));
  }

  _renderSvg() {
    const slots = this._slots();
    const lanes = this._lanes();
    if (!slots.length || !lanes.length) return `<div class="empty">No active equipment timers found.</div>`;
    const width = 960;
    const left = 116;
    const right = 24;
    const top = 34;
    const rowHeight = this._view === "week" ? 30 : 42;
    const axisWidth = width - left - right;
    const height = top + lanes.length * rowHeight + 28;
    const x = (minute) => left + (minute / 1440) * axisWidth;
    const rows = lanes.map(([key, label, icon, color], laneIndex) => {
      const y = top + laneIndex * rowHeight;
      const bars = slots.flatMap((slot) => {
        if (!(slot.equipment_enabled || []).includes(key)) return [];
        return normaliseSegments(slot).map(([start, stop]) => {
          const barX = x(start);
          const barWidth = Math.max(3, x(stop) - barX);
          const text = `Slot ${Number(slot.slot_index) + 1}`;
          return `
            <rect class="bar" x="${barX}" y="${y + 7}" width="${barWidth}" height="${rowHeight - 14}" fill="${color}">
              <title>${escapeHtml(this._equipmentName(key))}: ${escapeHtml(slot.start_time || "")} to ${escapeHtml(slot.stop_time || "")}</title>
            </rect>
            ${barWidth > 48 ? `<text class="slot-label" x="${barX + 8}" y="${y + rowHeight / 2 + 4}">${escapeHtml(text)}</text>` : ""}
          `;
        });
      }).join("");
      return `
        <text class="lane-label" x="16" y="${y + rowHeight / 2 + 5}">${escapeHtml(this._equipmentName(key) || label)}</text>
        <line class="grid" x1="${left}" y1="${y + rowHeight}" x2="${width - right}" y2="${y + rowHeight}"></line>
        ${bars}
      `;
    }).join("");
    const ticks = [0, 360, 720, 1080, 1440].map((minute) => {
      const label = minute === 1440 ? "24:00" : `${String(minute / 60).padStart(2, "0")}:00`;
      return `
        <line class="grid" x1="${x(minute)}" y1="20" x2="${x(minute)}" y2="${height - 20}"></line>
        <text class="axis" x="${x(minute) - 12}" y="15">${label}</text>
      `;
    }).join("");
    return `
      <div class="timeline">
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Halo equipment timer schedule">
          ${ticks}
          ${rows}
        </svg>
      </div>
    `;
  }

  _renderLegend() {
    return this._lanes().map(([key, label, , color]) => `
      <span class="legend-item"><span class="dot" style="--legend-color:${color}"></span>${escapeHtml(this._equipmentName(key) || label)}</span>
    `).join("");
  }

  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._entityId();
    if (!this._hass || !entityId) {
      this.shadowRoot.innerHTML = `<style>${styles()}</style><ha-card><div class="wrap">Set an equipment timer summary entity.</div></ha-card>`;
      return;
    }
    this.shadowRoot.innerHTML = `
      <style>${styles()}</style>
      <ha-card>
        <div class="wrap">
          <div class="head">
            <div>
              <div class="title">${escapeHtml(this._config.name || "Pool Schedule")}</div>
              <div class="sub">${escapeHtml(this._season())} · ${escapeHtml(entityId)}</div>
            </div>
            <div class="mode">
              <button class="${this._view === "day" ? "active" : ""}" data-view="day">Day</button>
              <button class="${this._view === "week" ? "active" : ""}" data-view="week">Week</button>
            </div>
          </div>
          ${this._renderSvg()}
          <div class="legend">${this._renderLegend()}</div>
        </div>
      </ha-card>
    `;
  }

  connectedCallback() {
    this.shadowRoot.addEventListener("click", (event) => {
      const target = event.target.closest("button[data-view]");
      if (!target) return;
      this._view = target.dataset.view;
      this._render();
    });
  }
}

customElements.define("halo-schedule-view", HaloScheduleView);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "halo-schedule-view",
  name: "Halo Schedule View",
  description: "Visualise AstralPool Halo equipment timer slots.",
});

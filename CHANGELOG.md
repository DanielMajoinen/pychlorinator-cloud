# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0-beta.3-gpo.2] - 2026-08-21

### Fixed

- GPO mode writes now use the dedicated `0x01F8` GPO AppAction characteristic with payload `[zero-based GPO index, action]`. The first test build incorrectly sent a general `0x01F4` chlorinator action, which the controller ignored; strict `0x00C9` readback correctly exposed the failure.

## [0.3.0-beta.3-gpo.1] - 2026-08-21

### Added

- Live physical output state for GPO1-GPO4 from the existing `0x00C9` equipment-mode readback. Four new read-only binary sensors expose whether each configured outlet is energised, with its current Off/Auto/On mode, auto-enabled flag, and configured controller name as attributes.
- Guarded GPO1/GPO2 mode selectors using the existing `0x01F4` equipment action path. Writes support Off/Auto/On, reject unconfigured outlets, refresh `0x00C9`, and fail visibly when controller readback does not match the requested mode. Existing Blade (GPO3) and Jets (GPO4) controls now use the same verified path.

## [0.3.0-beta.3] - 2026-07-10

### Fixed

- Home Assistant `hassfest` validation. Services no longer use a device filter under `target` (recent `hassfest` disallows it); each service now takes an optional `device_id` device selector field instead, which resolves the same way and keeps the bundled cards working unchanged. The manifest now declares its `http` usage (the frontend card registration) in `after_dependencies`. No functional change for users.
- `translations/en.json` had a stale config-flow step description; synced with `strings.json`.

### Changed

- Restored the original banner logo in the README; the beta.2 badge artwork is retired.
- Repository cleanup: removed the branding workshop under `docs/branding/` (concepts and intermediate sizes), the superseded `docs/hacs-install-and-test.md` checklist (the README's Installation, Verification, and Firmware Compatibility sections replace it), and the gitleaks CI workflow.

## [0.3.0-beta.2] - 2026-07-09

### Added

- Acid reservoir tracking. The controller has no acid tank-level field, so remaining acid is estimated HA-side from its daily dosing (`0x0259` `DosingPumpSecs`) converted via the acid pump dose rate. New `number.*_acid_bottle_size`, `button.*_log_acid_refill`, and sensors `acid_remaining` (L), `acid_remaining_percent`, `acid_used_today` (mL), `acid_avg_daily`, `acid_days_remaining`, `acid_last_refill`. State is persisted across restarts and handles the controller's daily counter rollover. The seconds→mL conversion is provisional until validated against a real dose.
- Vendor "vomit" opening handshake (`0x006B` + `0x0005`) on every cloud connect, matching the vendor app's post-connect "logical connection notification". Combined with the escalating post-disconnect cooldown, a multi-day soak held mostly 15–30 minute sessions with automatic recovery from the relay's periodic kicks. Adds a diagnostic `logical_connection_established` flag.
- Corrected `0x0259` CellStatistics now exposes `cell_running_hours`, `low_salt_cell_running_hours`, and `filter_pump_minutes_today` sensors, plus `dosing_capable` and the acid pump dose rate from capabilities (`0x0069`).
- All entities are enabled by default in this pre-release build for review; the curated long-term default-disabled set is documented in `docs/DEFAULT_DISABLED_ENTITIES.md`.
- `halo-timer-card` UX rev (vendor-app parity): per-slot “Timer N” labels matching the AstralPool app, header refresh button (when the `button.*_refresh_timer_config` entity is available), “updated Xm ago” badge driven by the 0x0193 last-seen timestamp, and equipment chip filtering that hides valves/outlets/relays that the controller reports as not connected (selected-but-absent chips remain visible so a stale selection stays recoverable).
- `sensor.*_equipment_timer_summary` attributes now include `slot_labels` (vendor-app Timer N mapping), `equipment_catalog` (per-chip {key, label, present, kind} — includes valve custom names, GPO custom names, and PoolSpa-vs-Spa toggle), and `timer_config_last_seen` (ISO timestamp of the most recent 0x0193 readback). All driven from data already on `ChlorinatorLiveData`; no new wire reads required.

### Fixed

- `0x0259` CellStatistics parser was mislabelled against the vendor struct — it reported cell-reversal count as `operating_days` and dropped the acid/filter daily counters. Corrected to the real layout (cell_reversal_count, cell running hours, low-salt hours, previous-day load, acid dosing seconds today, filter pump minutes today). Fixes the affected diagnostic sensors and unlocks acid tracking. (Sensor keys `operating_days` / `today_cell_runtime_minutes` replaced by `cell_running_hours` / `low_salt_cell_running_hours` / `filter_pump_minutes_today`.)
- `0x0192` timer-state no longer corrupts the reported season. Validated against a live firmware-2.3 frame, it is the 4-byte current/next struct for equipment and lighting timers; the previous build derived the season from the active-slot byte, which mislabelled the season whenever a timer in slot 1/2 was active.
- A truncated or malformed cloud frame no longer kills the session. `_update_data` used to branch on the payload type even for parser-error frames, so a short `0x0514`/`0x0516` frame raised `KeyError` and tore down the receive loop (and the whole cloud session). Error frames are now recorded but not fed into the model.
- Manual pump-speed selector no longer flaps Medium↔High every 5-10s. The 0x0324 config carousel cycles sub-records every rotation; previously sub=0x00 (stale `manual_speed_action_code` echo — typically Medium from a connect-time default) and sub=0x03 (authoritative `configured_speed_code`) BOTH overwrote `pump_speed`, so the selector flipped on every rotation. sub=0x00 is now treated as diagnostic-only (still surfaced via `manual_speed_action_code` / `manual_speed_action`), and sub=0x03 is the sole authoritative source for the selector. An earlier fix gated sub=0x03; this pass closes the sub=0x00 side. Live-captured by Rob on the deployed beta.1 dashboard.
- Heat-demand write readback now tolerates the vendor controller's ack-then-update race. Live testing confirmed the first poll after a `0x0451` write returns the PRE-write snapshot even though the write lands; we now settle, re-poll once on mismatch, and only warn if the second poll also disagrees. End state was always correct — only the warning was spurious.
- Obsolete `number.halo_<SERIAL>_filter_period_minutes` / `..._sanitise_period_minutes` entities (replaced by the new fixed-duration selects) are now automatically purged from the entity registry on integration setup, so HACS users don't carry `unavailable` clutter forward.

### Added

- Heater demand schedule support via cmd `0x0451` (`HeaterDemandSettingsCharacteristic`).
  - New sensor: `sensor.halo_<SERIAL>_heat_demand_schedule` (compact summary: `Off` / `Always On` / `HH:MM-HH:MM`).
  - New binary sensors: `binary_sensor.halo_<SERIAL>_heat_demand_enabled`, `..._heat_demand_window_enabled`, `..._heat_demand_activated`.
  - New service: `astralpool_halo_cloud.write_heat_demand` with optional fields (enabled/window_enabled/start_hour/start_minute/stop_hour/stop_minute/activated). Omitted fields preserve the latest live snapshot.
  - `0x0451` is now in the mandatory startup-refresh tier alongside heater state.
- Bundled Lovelace card modules:
  - `custom:halo-timer-card` for staged equipment timer editing.
  - `custom:halo-schedule-view` for equipment schedule visualisation.
- The `equipment_timer_summary` sensor now includes `winter_slots` and `summer_slots` attributes so frontend cards can render both seasonal schedules from one entity.

### Changed

- Filter For Period and Sanitise For Period are now fixed-duration select entities using the same minute increments as Acid Dosing Hold. The old custom-minute number entities were removed because the controller exposes fixed maintenance program durations, not arbitrary timers.

## [0.3.0-beta.1] - 2026-05-20

First public beta on the road to 1.0. Substantial protocol-correctness work plus quality-of-life upgrades.

### Fixed

- **Light state parser was reading the wrong byte offsets in `0x012C`.** Zone colour bytes were being parsed as zone-on flags, causing phantom zones to appear "on" on single-zone hardware. The parser now matches the authoritative chlorinator-side struct (modes at `[0:4]`, colours at `[4:8]`, zone-on flags at `[8]`).
- **Error-info code labels were wrong for 4 of 11 mapped codes**, and 40+ valid codes were missing entirely. Reverse-engineered the full table from the vendor app's resource strings (`ST4ER{code}Text`). Notable corrections:
  - 707: was "SamplingOnly" -> actually "Dosing Disabled" (acid dosing turned off; severity Information)
  - 706: was "DownRate1" -> actually "Water Sampling" (AI-mode sampling notice)
  - 705: was "DownRate2" -> actually "Pump Protect"
  - 703: was "WaterTooCold" -> actually "Down Rating (rate 2)"
  - 708: was "DosingDisabled" -> actually "Water Too Cold"
- Removed the bogus `light_active_timer` sensor. The byte we were reading as a timer index was actually a zone colour. No such timer index exists in the chlorinator light-state struct.
- AI operating speed is now correctly gated on Auto mode (previously could surface stale values when the controller wasn't in Auto).
- Restored the `active_timer_slot` equipment sensor (regression introduced in 0.2.x).
- Zone manual mode now correctly reads from `0x012C` `zone1_mode` on cold start instead of staying "unknown" until the first state change.

### Added

- **Light capabilities readback (`0x012D`)**: new mandatory startup read. New sensors include `lighting_num_zones_in_use`, `lighting_model`, `onboard_light_enabled`, and per-zone multicolour flags.
- **Auto-hide unused zones.** Zone 2/3/4 entities now gate on `lighting_num_zones_in_use`, so single-zone systems no longer show three phantom zones.
- **Custom valve / equipment names.** Valves and outlets configured with custom names in the vendor app (e.g. "Blade", "Jets") now resolve to the user-configured strings via the cmd 27 vomit-sequence trigger + `0x051B` chunk reassembly. Falls back to the built-in enum label ("Other", "Pool Valve", etc.) when no custom name has been configured.
- **Built-in equipment-name readback (`0x0514` / `0x0516`).** Eight new diagnostic sensors expose resolved GPO and valve names with an `is_custom_name` attribute. Default-disabled.
- **`get_equipment_name(slot_index)` helper** resolves the controller's fixed equipment slot map (0-12: pool/spa, filter pump, heater, GPOs, valves, relays) to display names.
- **Firmware version sensor** sourced from `buildinfo.pbver`.
- **Four maintenance buttons**: Abort, Sanitise Until Tomorrow, Filter For Period, Sanitise For Period. (Skipped Sanitise+Clean — requires cleaner pump hardware not present in scope.)
- **Refresh Optional Values button** with 30-second rate limit. Re-reads optional-tier capabilities + equipment names on demand without triggering the full mandatory sweep.
- **Last-known value restore (`RestoreEntity`)** for 25+ sensors that benefit from persistence across HA restarts (chemistry, temps, most setpoints, capabilities, firmware, counters, timer config, acid-hold). Live-only sensors that should never restore (pH/ORP watermarks, heater setpoint, timer pump speed) are deliberately excluded.
- Error-info sensor now exposes attributes: `severity` (Information / Warning / Fault), `category` (Hardware / Sensor / Pump / Heater / Chemistry / Lighting / Solar / Cell / Flow / Acid / Maintenance / Firmware / Network), `reason`, `recommended_action`, `raw_code`.
- New `controller_notice_active` binary sensor (default-disabled): True when any controller notice is present, regardless of severity.
- New `controller_fault_active` binary sensor (default-disabled, device_class=problem): True only when a hardware/equipment fault is present (severity Fault). Excludes informational notices like "Dosing Disabled".
- Full error-code reference table now covers 50+ codes across Hardware, Sensor, Pump, Heater, Chemistry, Lighting, Solar, Cell, Flow, Acid, and Firmware categories.
- Receive watchdog: detects dead cloud connections when the server stops sending messages (11-second timeout). Previously the integration could sit in a zombie connection for 30+ seconds before recovery.
- `dataexchangeerror` from the cloud relay is now treated as a fatal session event, triggering immediate clean disconnect and reconnect rather than silent continuation.
- Server-initiated `disconnect` messages are handled as clean session-end signals.
- Equipment timer write support via service `astralpool_halo_cloud.write_equipment_timer`. Configure any of 8 equipment timer slots per season (Winter/Summer): start/stop time, enabled flag, equipment mask (13 fields covering pool/spa, filter pump, heater, outlets, valves, relays), pump speed, and start/stop mode (Normal/Dusk/Dawn). The controller persists immediately and the integration reads back the slot to confirm. EXPERIMENTAL — protocol fully decoded from vendor app, but live writes have not been validated on hardware; use carefully and verify behaviour with the vendor app.
- `select.halo_<SERIAL>_timer_season` lets HA toggle between Winter and Summer (independent slot sets per season).
- Full timer slot readback: 8 equipment slots per season are now read into ChlorinatorLiveData (current season at startup, either season on demand) and exposed via `equipment_timer_summary` sensor attributes. New `refresh_timer_config` button forces a re-read (30s rate-limited).
- Light timer writes and heat-demand window writes are NOT implemented in this beta. Light timers wait on a season-behaviour clarification; heat-demand window is a separate workstream.

### Changed

- `light_zone_mode` sensors renamed to `light_zone_manual_mode` for clarity. The new name reflects that the value is the user-set manual mode (Off / Auto / On), not the live output state.
- README rewritten as a HACS-facing document. Disclaimer added: unofficial, reverse-engineered, not affiliated with AstralPool / Astral / Fluidra / Astral Labs.
- Default state for Blade / Jets enum-based equipment is now "Off" rather than carrying stale values across reconnects.

### Removed

- `water_too_cold` HA binary sensor. Temperature "too cold" is user-relative; this didn't belong as a built-in.
- `light_active_timer` sensor (see Fixed above — was always parsing a colour byte).

### Internal

- New parsers: `_parse_light_state` (corrected layout), `_parse_light_capabilities`, `_parse_valve_custom_name_chunk`, equipment setup parsers for `0x0514` / `0x0516`.
- New WebSocket method: `request_custom_names_vomit()` triggers cmd 27 vomit-sequence emission.
- `ChlorinatorLiveData` gained `valve_custom_names: dict[int, str]`, lighting capability fields, equipment name fields, and firmware metadata.
- Test count: ~110 → 181 across the beta cycle.

## [0.2.4] - prior release

Previous public release. See git history for details.

[0.3.0-beta.3-gpo.1]: https://github.com/DanielMajoinen/pychlorinator-cloud/releases/tag/0.3.0-beta.3-gpo.1
[0.3.0-beta.3-gpo.2]: https://github.com/DanielMajoinen/pychlorinator-cloud/releases/tag/0.3.0-beta.3-gpo.2
[0.3.0-beta.1]: https://github.com/robmarkoski/pychlorinator-cloud/compare/v0.2.4...v0.3.0-beta.1

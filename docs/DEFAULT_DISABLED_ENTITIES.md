# Default-disabled entities

These entities are the curated **long-term default-disabled** set for the
AstralPool Halo Cloud integration — mostly per-flag diagnostic binary sensors,
raw setpoint read-backs, and duplicate/low-value diagnostics that would clutter
a normal user's device page.

**Current status: ALL ENABLED for the testing phase** (2026-07-06). To restore
the long-term defaults, re-add `entity_registry_enabled_default=False` to the
entity descriptions for the keys below (69 entities).

| Platform | Category | Key | Name |
|---|---|---|---|
| binary_sensor | Diagnostic | `ai_mode_active` | AI Mode Active |
| binary_sensor | Diagnostic | `backwashing` | Backwashing |
| binary_sensor | Diagnostic | `controller_fault_active` | Controller Fault Active |
| binary_sensor | Diagnostic | `controller_notice_active` | Controller Notice Active |
| binary_sensor | Diagnostic | `filtering_only` | Filtering Only |
| binary_sensor | Diagnostic | `heater_cooldown_active` | Heater Cooldown Active |
| binary_sensor | Diagnostic | `heater_flame` | Heater Flame |
| binary_sensor | Diagnostic | `heater_gas_valve` | Heater Gas Valve |
| binary_sensor | Diagnostic | `heater_lockout` | Heater Lockout |
| binary_sensor | Diagnostic | `heater_pressure` | Heater Water Pressure |
| binary_sensor | Diagnostic | `heater_service_required` | Heater Service Required |
| binary_sensor | Diagnostic | `low_speed_no_chlorinating` | Low Speed No Chlorinating |
| binary_sensor | Diagnostic | `manual_acid_dose_active` | Manual Acid Dose Active |
| binary_sensor | Diagnostic | `reduced_output_low_temperature` | Reduced Output Low Temperature |
| binary_sensor | Diagnostic | `sampling_active` | Sampling Active |
| binary_sensor | Diagnostic | `solar_flush_active` | Solar Flush Active |
| binary_sensor | Diagnostic | `solar_pump` | Solar Pump |
| binary_sensor | Diagnostic | `spa_selection` | Spa Selected |
| binary_sensor | Diagnostic | `standby` | Standby |
| binary_sensor | Diagnostic | `time_drift` | Time Drift |
| button | Config | `abort_maintenance_task` | Abort Maintenance Task |
| button | Config | `sanitise_until_tomorrow` | Sanitise Until Tomorrow |
| select | Config | `connection_pause_select` | Connection Hold |
| select | Control | `acid_dosing_select` | Acid Dosing Hold |
| select | Control | `blade_mode_select` | Blade Mode |
| select | Control | `jets_mode_select` | Jets Mode |
| select | Control | `light_mode_select` | Light Mode |
| sensor | Diagnostic | `?` | ? |
| sensor | Diagnostic | `access_level` | Access Level |
| sensor | Diagnostic | `acid_setpoint` | Acid Setpoint |
| sensor | Diagnostic | `board_temperature` | Board Temperature |
| sensor | Diagnostic | `cell_reversal_count` | Cell Reversal Count |
| sensor | Diagnostic | `chlorine_control_type` | Chlorine Control Type |
| sensor | Diagnostic | `controller_datetime` | Controller Time |
| sensor | Diagnostic | `equipment_timer_active_slots` | Equipment Timer Active Slots |
| sensor | Diagnostic | `equipment_timer_slots` | Equipment Timer Slots |
| sensor | Diagnostic | `equipment_timer_summary` | Equipment Timer Summary |
| sensor | Diagnostic | `filter_sanitise_remaining` | Filter/Sanitise Remaining |
| sensor | Diagnostic | `firmware_version` | Firmware Version |
| sensor | Diagnostic | `heater_error` | Heater Error |
| sensor | Diagnostic | `heater_message` | Heater Message |
| sensor | Diagnostic | `highest_orp_measured` | Highest ORP Measured |
| sensor | Diagnostic | `highest_ph_measured` | Highest pH Measured |
| sensor | Diagnostic | `last_update` | Last Update |
| sensor | Diagnostic | `lighting_timer_slots` | Lighting Timer Slots |
| sensor | Diagnostic | `litres_left_to_filter` | Litres Left to Filter |
| sensor | Diagnostic | `lowest_orp_measured` | Lowest ORP Measured |
| sensor | Diagnostic | `lowest_ph_measured` | Lowest pH Measured |
| sensor | Diagnostic | `orp_setpoint` | ORP Setpoint Readback |
| sensor | Diagnostic | `ph_control_type` | pH Control Type |
| sensor | Diagnostic | `ph_setpoint` | pH Setpoint Readback |
| sensor | Diagnostic | `pool_chlorine_setpoint` | Pool Chlorine Setpoint |
| sensor | Diagnostic | `pool_volume` | Pool Volume |
| sensor | Diagnostic | `power_board_runtime_hours` | Power Board Runtime |
| sensor | Diagnostic | `priming_countdown` | Priming Countdown |
| sensor | Diagnostic | `protocol_version` | Protocol Version |
| sensor | Diagnostic | `pump_speed` | Manual Pump Speed (diagnostic) |
| sensor | Diagnostic | `salt_error_raw` | Salt/Error Code |
| sensor | Diagnostic | `solar_message` | Solar Message |
| sensor | Diagnostic | `solar_mode` | Solar Mode |
| sensor | Diagnostic | `solar_roof_temperature` | Solar Roof Temperature |
| sensor | Diagnostic | `solar_water_temperature` | Solar Water Temperature |
| sensor | Diagnostic | `spa_chlorine_setpoint` | Spa Chlorine Setpoint |
| sensor | Diagnostic | `timer_info` | Timer Info |
| sensor | Diagnostic | `timer_next_profile_index` | Next Timer Slot |
| sensor | Diagnostic | `timer_profile_index` | Timer Profile Index |
| sensor | Diagnostic | `timer_pump_speed` | Timer Pump Speed (diagnostic) |
| sensor | Diagnostic | `timer_season` | Timer Season |
| sensor | Diagnostic | `water_temperature_precise` | Water Temperature Precise |

## Rationale by group
- **Per-flag heater/solar/state binary sensors** (heater_flame, heater_lockout,
  solar_pump, standby, sampling_active, etc.): niche; the main state/mode
  entities cover the common case. Enable if you have that hardware.
- **Raw setpoint read-backs** (ph_setpoint, orp_setpoint, *_chlorine_setpoint):
  duplicate the writable number entities; useful for automations/debugging only.
- **Identity/diagnostics** (firmware_version, protocol_version, access_level,
  last_update, controller_datetime): support/debugging.
- **Timer internals** (timer_profile_index, *_timer_slots, timer_summary):
  advanced scheduling introspection.
- **Config selects/buttons** (blade/jets/light mode, acid dosing hold, abort/
  sanitise-until-tomorrow, connection hold): moved to Config category; enable
  per preference.

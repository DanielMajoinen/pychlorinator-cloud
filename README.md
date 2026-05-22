# AstralPool Halo Cloud

<!-- markdownlint-disable MD013 MD028 MD033 MD041 -->

<p align="center">
  <img src="docs/branding/logo-banner.png" alt="AstralPool Halo Cloud" width="540">
</p>

<p align="center">
  <a href="https://hacs.xyz/"><img alt="HACS Custom" src="https://img.shields.io/badge/HACS-Custom-orange.svg"></a>
  <a href="https://www.home-assistant.io/"><img alt="Home Assistant Custom Integration" src="https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
  <a href="https://github.com/robmarkoski/pychlorinator-cloud/releases"><img alt="Preview release" src="https://img.shields.io/badge/release-v0.3.0--preview.1-yellow.svg"></a>
</p>

An unofficial Home Assistant integration for AstralPool Halo chlorinators. Bluetooth is used once for pairing. After that the integration talks to the AstralPool cloud over WebSocket. Not affiliated with AstralPool, Astral, Fluidra, or Astral Labs.

> [!CAUTION]
> Preview release. Tested on one firmware version (`pbver 2.3`). No warranty, no vendor support. It might break. Use it if you know what you're doing.

> [!IMPORTANT]
> Breaking change from 0.2.x. Entity unique IDs, the config flow, the manifest version, and the connection model have all changed. Easiest path: remove the existing integration and pair fresh. See [Migrating from 0.2.x](#migrating-from-02x).

> [!WARNING]
> Don't run this and a BLE-based Halo integration against the same chlorinator. The cloud relay only allows one session per device. If you need to use the phone app or a BLE client, hit Pause Cloud Connection first.

## Contents

- [What you get](#what-you-get)
- [Requirements](#requirements)
- [Install](#install)
- [Configure](#configure)
- [Migrating from 0.2.x](#migrating-from-02x)
- [Entities](#entities)
  - [Chemistry](#chemistry)
  - [Pump and filtration](#pump-and-filtration)
  - [Sanitisation cell](#sanitisation-cell)
  - [Heater and heat demand](#heater-and-heat-demand)
  - [Lighting](#lighting)
  - [Equipment timers](#equipment-timers)
  - [Maintenance tasks](#maintenance-tasks)
  - [Cloud session](#cloud-session)
  - [Diagnostics](#diagnostics)
  - [Status flags](#status-flags)
- [Lovelace cards](#lovelace-cards)
- [Example dashboards](#example-dashboards)
- [Services](#services)
- [Automation examples](#automation-examples)
- [Troubleshooting](#troubleshooting)
- [What's new in 0.3.0-preview.1](#whats-new-in-030-preview1)
- [Roadmap](#roadmap)
- [Limitations](#limitations)
- [Reporting issues](#reporting-issues)
- [License](#license)

## What you get

Over 100 entities covering chemistry, pump, cell, heater, lighting, timers, maintenance tasks, and diagnostics. Two bundled Lovelace cards (timer editor and schedule view) that register themselves. Two services for writing equipment timer slots and the heat-demand schedule.

## Requirements

| Component        | Notes                                                |
| ---------------- | ---------------------------------------------------- |
| Hardware         | AstralPool Halo chlorinator with cloud connectivity  |
| Home Assistant   | 2024.1.0 or newer                                    |
| HACS             | Required for install                                 |
| Bluetooth        | Adapter or ESPHome BLE proxy, used only for pairing  |
| Vendor app       | Halo Chlor GO should already work against the unit   |
| Firmware tested  | `pbver 2.3`. Other firmware versions are untested    |

## Install

1. HACS, Integrations, three-dot menu, **Custom repositories**.
2. Add:
   - URL: `https://github.com/robmarkoski/pychlorinator-cloud`
   - Type: `Integration`
3. Find **AstralPool Halo Cloud** in the HACS list, click **Download**.
4. Restart Home Assistant.

## Configure

1. Settings, Devices & services, **Add Integration**, search for **AstralPool Halo Cloud**.
2. The setup flow scans for nearby Halo chlorinators advertising as `HCHLOR`.
3. Pick your controller. Confirm pairing on the controller's local UI or enter the access code shown on its display.
4. After pairing the integration pulls the cloud credentials from the controller and switches to cloud mode. Bluetooth is not used again.

The device appears under Settings, Devices & services with all entities populated.

## Migrating from 0.2.x

Entity unique IDs and config data layout have changed. Cleanest path:

1. Note any automations and dashboards that reference `*halo*` or `*pool_chlorinator*` entity IDs.
2. Settings, Devices & services, open the existing AstralPool Halo entry, three-dot menu, **Delete**.
3. HACS, Integrations, find AstralPool Halo Cloud, **Redownload** (or remove and re-add).
4. Restart Home Assistant.
5. Add the integration fresh, complete BLE pairing.
6. Update your dashboards and automations. New entity ID pattern is `<domain>.halo_<SERIAL>_<key>`.

If you used the old custom-duration filter or sanitise minute number entities, swap them for the new fixed-period selects (see [Maintenance tasks](#maintenance-tasks)).

## Entities

All entities are scoped to one device per chlorinator. Entity ID pattern: `<domain>.halo_<SERIAL>_<key>`.

### Chemistry

| Entity                       | Domain        | Notes                                          |
| ---------------------------- | ------------- | ---------------------------------------------- |
| pH                           | sensor        | Current pH reading                             |
| ORP Measurement              | sensor        | Current ORP in mV                              |
| Highest pH Measured          | sensor        | High watermark since reset                     |
| Lowest pH Measured           | sensor        | Low watermark since reset                      |
| Highest ORP Measured         | sensor        | High watermark since reset                     |
| Lowest ORP Measured          | sensor        | Low watermark since reset                      |
| Chlorine Status              | sensor        | Controller-reported chlorine state             |
| pH Status                    | sensor        | Controller-reported pH state                   |
| pH Control Type              | sensor        | Configured pH control strategy                 |
| Chlorine Control Type        | sensor        | Configured chlorine control strategy           |
| pH Setpoint                  | number        | Adjustable pH setpoint                         |
| ORP Setpoint                 | number        | Adjustable ORP setpoint                        |
| pH Setpoint Readback         | sensor        | Echo of the last accepted setpoint             |
| ORP Setpoint Readback        | sensor        | Echo of the last accepted setpoint             |
| Pool Chlorine Setpoint       | sensor        | Configured pool chlorine target                |
| Spa Chlorine Setpoint        | sensor        | Configured spa chlorine target                 |
| Acid Setpoint                | sensor        | Configured acid setpoint                       |
| Chemistry Values Current     | binary_sensor | True while readings are fresh                  |
| Chemistry Values Valid       | binary_sensor | True when probe state is trusted               |

### Pump and filtration

| Entity                          | Domain          | Notes                                |
| ------------------------------- | --------------- | ------------------------------------ |
| System Mode                     | sensor + select | Off / Auto / Manual / AI             |
| Pump Speed                      | sensor          | Current operating speed              |
| Manual Pump Speed               | select          | Low / Medium / High in Manual mode   |
| Manual Pump Speed (diagnostic)  | sensor          | Last manual speed code reported      |
| Timer Pump Speed (diagnostic)   | sensor          | Last timer-slot speed in use         |
| Priming Countdown               | sensor          | Seconds remaining in priming         |
| Pump Operating                  | binary_sensor   | True while pump is running           |
| Pump Priming                    | binary_sensor   | True while priming                   |
| No Flow                         | binary_sensor   | Controller-reported no-flow          |
| Backwashing                     | binary_sensor   | True during automatic backwash       |
| Valve 0                         | binary_sensor   | Valve 0 active state                 |
| Valve 1                         | binary_sensor   | Valve 1 active state                 |

### Sanitisation cell

| Entity                          | Domain        | Notes                                          |
| ------------------------------- | ------------- | ---------------------------------------------- |
| Cell Level                      | sensor        | Cell output level                              |
| Cell Current                    | sensor        | Cell current draw                              |
| Cell Reversal Count             | sensor        | Polarity reversals since reset                 |
| Today's Cell Runtime            | sensor        | Minutes of cell runtime today                  |
| Cell Operating                  | binary_sensor | True while electrolysing                       |
| Cell Reversed                   | binary_sensor | True while in reversed polarity                |
| Cell Reversing                  | binary_sensor | True during polarity transition                |
| Cell Disabled                   | binary_sensor | True when manually or fault-disabled           |
| Sanitising Active               | binary_sensor | Sanitising task running                        |
| Sampling Active                 | binary_sensor | Probe sampling cycle running                   |
| Sampling Only                   | binary_sensor | Probe-only mode, no sanitisation               |
| Filtering Only                  | binary_sensor | Filter-only mode, no sanitisation              |
| Standby                         | binary_sensor | Controller in standby                          |
| Low Speed No Chlorinating       | binary_sensor | Low-speed safety inhibit                       |
| Reduced Output Low Temperature  | binary_sensor | Output reduced due to low water temp           |
| Low Salt                        | binary_sensor | Low salt warning                               |
| High Salt                       | binary_sensor | High salt warning                              |

### Heater and heat demand

| Entity                       | Domain        | Notes                                          |
| ---------------------------- | ------------- | ---------------------------------------------- |
| Heater Mode                  | sensor        | Current heater mode                            |
| Heater Mode Control          | select        | Set heater mode (Off / Auto / On)              |
| Heater Pump Mode             | sensor        | Pump association                               |
| Heat Pump Mode               | sensor        | Set if a heat pump is configured               |
| Heater Setpoint              | sensor        | Configured heater setpoint                     |
| Heater Setpoint Control      | number        | Adjustable heater setpoint                     |
| Heater Water Temperature     | sensor        | Heater-side water temperature                  |
| Heater Error                 | sensor        | Heater-side error string                       |
| Heater On                    | binary_sensor | True while heating                             |
| Heater Cooldown Active       | binary_sensor | Post-heating cooldown                          |
| Heat Demand Schedule         | sensor        | Summary string of the heat-demand window       |
| Heat Demand Enabled          | binary_sensor | Master heat-demand enable                      |
| Heat Demand Window Enabled   | binary_sensor | Window time-restriction flag                   |
| Heat Demand Activated        | binary_sensor | Activation flag within an enabled schedule     |

Set the heat-demand schedule via the [`write_heat_demand`](#services) service.

### Lighting

| Entity                       | Domain        | Notes                                          |
| ---------------------------- | ------------- | ---------------------------------------------- |
| Light Mode                   | select        | Set lighting mode                              |
| Pool Light (Zone 1)          | binary_sensor | True when Zone 1 lights are on                 |
| Light Zone 2                 | binary_sensor | True when Zone 2 lights are on                 |
| Light Zone 3                 | binary_sensor | True when Zone 3 lights are on                 |
| Light Zone 4                 | binary_sensor | True when Zone 4 lights are on                 |
| Zone 1 to 4 Manual Mode      | sensor x4     | Per-zone manual-mode flag                      |
| Zone 1 to 4 Active Source    | sensor x4     | Which control source is driving the zone       |
| Blade Mode                   | select        | Pool blade (jet / feature) mode if equipped    |
| Jets Mode                    | select        | Spa jets mode if equipped                      |

### Equipment timers

Eight timer slots per season, two seasons (Winter / Summer). Per-slot equipment selection, start and stop times, pump speed.

| Entity                       | Domain        | Notes                                          |
| ---------------------------- | ------------- | ---------------------------------------------- |
| Timer Season                 | select        | Switch active season Winter / Summer           |
| Equipment Timer Slots        | sensor        | Per-slot config in attributes                  |
| Equipment Timer Active Slots | sensor        | Count of currently-active slots                |
| Equipment Timer Summary      | sensor        | Compact summary plus slot descriptor maps      |
| Refresh Timer Config         | button        | Force a re-read of all timer characteristics   |
| Timer Info                   | sensor        | Per-slot info messages                         |

Write individual slots via the [`write_equipment_timer`](#services) service or interactively via the bundled `halo-timer-card` (see [Lovelace cards](#lovelace-cards)).

### Maintenance tasks

| Entity                          | Domain        | Notes                                       |
| ------------------------------- | ------------- | ------------------------------------------- |
| Filter For Period               | select        | Fixed-duration filter task (1 min to 24 h)  |
| Sanitise For Period             | select        | Fixed-duration sanitise task (1 min to 24 h)|
| Acid Dosing Hold                | select        | Hold acid dosing for a fixed duration       |
| Acid Dosing Hold Remaining      | sensor        | Time remaining on an active dosing hold     |
| Filter/Sanitise Remaining       | sensor        | Time remaining on the current task          |
| Sanitise Until Tomorrow         | button        | "Sanitise until next timer slot"            |
| Abort Maintenance Task          | button        | Cancel an in-progress task                  |
| Manual Acid Dose Active         | binary_sensor | True during a manual acid dose              |
| Dosing Pump                     | binary_sensor | True while the dosing pump is running       |
| Dosing Disabled                 | binary_sensor | True when dosing is disabled                |
| Daily Acid Dose Limit Reached   | binary_sensor | True once today's limit is reached          |

### Cloud session

Controls for handing the cloud session over to the vendor app or a BLE client without uninstalling.

| Entity                       | Domain        | Notes                                          |
| ---------------------------- | ------------- | ---------------------------------------------- |
| Connection Hold              | select        | Active / Paused                                |
| Pause Cloud Connection       | button        | One-shot pause                                 |
| Resume Cloud Connection      | button        | One-shot resume                                |
| Cloud Pause Duration         | number        | Auto-resume after N minutes (0 = indefinite)   |
| Cloud Connected              | binary_sensor | True while the WebSocket session is healthy    |

### Diagnostics

| Entity                       | Domain        | Notes                                          |
| ---------------------------- | ------------- | ---------------------------------------------- |
| Firmware Version             | sensor        | `pbver` reported by the controller             |
| Protocol Version             | sensor        | Reported protocol version                      |
| Access Level                 | sensor        | Reported access level                          |
| Controller Time              | sensor        | Controller wall-clock                          |
| Last Update                  | sensor        | Timestamp of the last successful poll          |
| Time Drift                   | binary_sensor | True when controller clock skews past threshold|
| Time Drift Threshold         | number        | Drift threshold in seconds                     |
| Sync Controller Time         | button        | Push HA time to the controller                 |
| Refresh Optional Values      | button        | Sweep optional / non-pushed registers          |
| Board Temperature            | sensor        | Controller board temperature                   |
| Cooling Fan                  | binary_sensor | True while the cooling fan is on               |
| Power Board Runtime          | sensor        | Lifetime hours on the power board              |
| Operating Days               | sensor        | Days powered on                                |
| Water Temperature            | sensor        | Pool water temperature, 1 C resolution         |
| Water Temperature Precise    | sensor        | Pool water temperature, 0.1 C resolution       |
| WiFi Signal Strength         | sensor        | Chlorinator's own WiFi RSSI                    |

### Status flags

| Entity                                | Domain        | Notes                                         |
| ------------------------------------- | ------------- | --------------------------------------------- |
| AI Mode Active                        | binary_sensor | True while AI-mode logic is in control        |
| Spa Selected                          | binary_sensor | True when spa mode is active                  |
| Sanitising Until Next Timer Tomorrow  | binary_sensor | "Run until next timer" mode engaged           |
| Controller Notice Active              | binary_sensor | A non-fault notice is present                 |
| Controller Fault Active               | binary_sensor | A fault notice is present                     |
| Info Message                          | sensor        | Current info message string                   |
| Error Message                         | sensor        | Current error message string                  |
| Hide Error                            | button        | Dismiss the current error message             |

## Lovelace cards

Two custom cards are bundled with the integration and registered automatically. You don't need to add resources manually.

### `halo-timer-card`

8-slot equipment timer editor matching the vendor app. Winter / Summer season switching, per-slot equipment chips, pump-speed picker, staged-edit confirmation with readback.

```yaml
type: custom:halo-timer-card
entity: sensor.halo_<SERIAL>_equipment_timer_summary
device_id: <HA_DEVICE_ID>
name: Pool Equipment Timers
```

### `halo-schedule-view`

Read-only day or week timeline of scheduled equipment runs. Useful as a quick "what's running when" view on a wall tablet.

```yaml
type: custom:halo-schedule-view
entity: sensor.halo_<SERIAL>_equipment_timer_summary
name: Pool Schedule
```

After making timer edits, press `button.halo_<SERIAL>_refresh_timer_config` to force a re-read of timer state.

## Example dashboards

### Current state at a glance

```yaml
type: vertical-stack
title: Pool
cards:
  - type: glance
    entities:
      - entity: sensor.halo_<SERIAL>_water_temperature_precise
        name: Water
      - entity: sensor.halo_<SERIAL>_ph_measurement
        name: pH
      - entity: sensor.halo_<SERIAL>_orp_measurement
        name: ORP
      - entity: sensor.halo_<SERIAL>_cell_level
        name: Cell
  - type: entities
    title: Status
    entities:
      - sensor.halo_<SERIAL>_mode
      - sensor.halo_<SERIAL>_current_operating_speed
      - binary_sensor.halo_<SERIAL>_pump_operating
      - binary_sensor.halo_<SERIAL>_cell_operating
      - binary_sensor.halo_<SERIAL>_heater_on
      - binary_sensor.halo_<SERIAL>_cloud_connected
```

### Maintenance controls

```yaml
type: entities
title: Pool Maintenance
entities:
  - select.halo_<SERIAL>_mode_select
  - select.halo_<SERIAL>_pump_speed_select
  - select.halo_<SERIAL>_filter_for_period
  - select.halo_<SERIAL>_sanitise_for_period
  - select.halo_<SERIAL>_acid_dosing_select
  - button.halo_<SERIAL>_sanitise_until_tomorrow
  - button.halo_<SERIAL>_abort_maintenance_task
  - button.halo_<SERIAL>_dismiss_info_message
```

### Cloud session

```yaml
type: entities
title: Cloud Session
entities:
  - binary_sensor.halo_<SERIAL>_cloud_connected
  - select.halo_<SERIAL>_connection_pause_select
  - number.halo_<SERIAL>_connection_pause_minutes
  - button.halo_<SERIAL>_pause_cloud_connection
  - button.halo_<SERIAL>_resume_cloud_connection
```

### Heat demand

```yaml
type: entities
title: Heat Demand
entities:
  - sensor.halo_<SERIAL>_heat_demand_schedule
  - binary_sensor.halo_<SERIAL>_heat_demand_enabled
  - binary_sensor.halo_<SERIAL>_heat_demand_window_enabled
  - binary_sensor.halo_<SERIAL>_heat_demand_activated
  - select.halo_<SERIAL>_heater_mode_select
  - number.halo_<SERIAL>_heater_setpoint_control
```

## Services

### `astralpool_halo_cloud.write_equipment_timer`

Write one equipment timer slot. 8 slots per season, 2 seasons.

```yaml
service: astralpool_halo_cloud.write_equipment_timer
target:
  device_id: <HA_DEVICE_ID>
data:
  season: Winter
  slot_index: 0
  enabled: true
  start_hour: 7
  start_min: 0
  start_mode: Normal           # Normal | Dusk | Dawn
  stop_hour: 11
  stop_min: 0
  stop_mode: Normal
  equipment:                    # one or more of:
    - FilterPump                #   PoolSpa, FilterPump, Heater,
    - Heater                    #   Outlet1..4, Valve1..4, Relay1..2
  pump_speed: Medium            # Low | Medium | High
```

### `astralpool_halo_cloud.write_heat_demand`

Write the heater demand schedule. All fields are optional. Omitted fields are preserved from the latest known live snapshot, so you can flip one flag without re-specifying the whole schedule.

```yaml
service: astralpool_halo_cloud.write_heat_demand
target:
  device_id: <HA_DEVICE_ID>
data:
  enabled: true
  window_enabled: true
  start_hour: 6
  start_minute: 0
  stop_hour: 22
  stop_minute: 0
  activated: true
```

To toggle heat demand on or off without touching the schedule:

```yaml
service: astralpool_halo_cloud.write_heat_demand
target:
  device_id: <HA_DEVICE_ID>
data:
  activated: false
```

## Automation examples

### Pause the cloud session when you open the vendor phone app

The cloud relay only allows one session per chlorinator. If you sometimes use Halo Chlor GO, pause the cloud connection automatically so HA gets out of the way:

```yaml
alias: Pool - pause cloud when phone is home
trigger:
  - platform: state
    entity_id: device_tracker.phone_ios   # adjust to your device
    to: "home"
action:
  - service: button.press
    target:
      entity_id: button.halo_<SERIAL>_pause_cloud_connection
```

### Notify on a persistent controller fault

```yaml
alias: Pool - fault notice
trigger:
  - platform: state
    entity_id: binary_sensor.halo_<SERIAL>_controller_fault_active
    to: "on"
    for: "00:02:00"
action:
  - service: notify.mobile_app_phone
    data:
      title: Pool controller fault
      message: "{{ states('sensor.halo_<SERIAL>_error_message') }}"
```

### Sanitise overnight if ORP drops

```yaml
alias: Pool - overnight sanitise on low ORP
trigger:
  - platform: numeric_state
    entity_id: sensor.halo_<SERIAL>_orp_measurement
    below: 650
    for: "01:00:00"
condition:
  - condition: time
    after: "22:00:00"
    before: "06:00:00"
action:
  - service: select.select_option
    target:
      entity_id: select.halo_<SERIAL>_sanitise_for_period
    data:
      option: "6 hours"
```

## Troubleshooting

**Entities show "unavailable" for the first 30 seconds.**
Expected on first connect. The cloud relay does an initial state burst and some entities wait on their first characteristic. Give it one signalling cycle.

**Cloud session disconnects shortly after connecting.**
Earlier builds had a post-connect disconnect bug. If you see it on `0.3.0-preview.1`, open an issue with debug logs.

**Pairing fails: "Wrong credentials" or "Chlorinator unavailable".**
Power-cycle the controller, wait 30 seconds, retry. Confirm Halo Chlor GO can still connect. Make sure no other HA integration (BLE Halo, BLE chlorinator) is active for the same device. If the controller is on firmware 2.7 or later, BLE pairing may not be possible. See the open repo issue on the firmware 2.7+ Play Integrity / App Attest gate.

**pH or ORP readings look stale.**
Check Chemistry Values Current and Chemistry Values Valid. If those are false, the controller hasn't sampled yet. Probe sampling is on a controller-side schedule, not the integration's.

**Phone app or BLE client is fighting with HA.**
The cloud relay only allows one session per chlorinator. Use Pause Cloud Connection. Set a Cloud Pause Duration for an auto-resume.

**Clean removal.**
Settings, Devices & services, delete the device. Then uninstall the HACS download. The bundled card resources unregister on uninstall. Any card YAML you added by hand needs removing manually.

## What's new in 0.3.0-preview.1

Short summary. See [CHANGELOG.md](CHANGELOG.md) for the full list.

**Architecture reset**

- Cloud-first runtime. BLE is used once for pairing, then the integration talks to the vendor cloud over WebSocket.
- Old BLE-direct operation has been removed.

**Entities**

- Over 100 entities exposed. Equipment timer surface now matches the vendor app (8 slots per season, Winter and Summer).
- New heat-demand sensors and `write_heat_demand` service.
- Per-zone lighting controls with manual mode and active-source attributes.
- AI / Auto / Manual pump modes with mode-aware speed surfacing.
- Structured error-code sensor with severity and category.
- Firmware version, WiFi RSSI, cell runtime, cooling fan, dosing pump, board temperature.

**Lovelace cards**

- Bundled `halo-timer-card` (vendor-app parity timer editor).
- Bundled `halo-schedule-view` (read-only day / week timeline).
- Cards auto-register, no manual resource setup.

**Reliability**

- Connection lifecycle rewritten. Non-blocking setup, bounded backoff, fail-closed keepalive with an application-layer time poll alongside the JSON heartbeat. Earlier disconnect bug is closed.
- Pause and Resume Cloud Connection controls so the phone app or a BLE client can use the chlorinator without uninstalling.
- Equipment timer writes back with readback confirmation.

**Removed**

- BLE-direct operation (BLE is pairing-only now).
- Custom-minute filter / sanitise period number entities. Replaced by fixed-duration selects.

**Project**

- MIT licence.
- `SECURITY.md` documenting the provenance of the hardcoded vendor cloud credentials.
- HACS custom-repository install path with a proper `hacs.json`.

## Roadmap

No dates. Order is rough priority.

| Status      | Item                                                                 |
| ----------- | -------------------------------------------------------------------- |
| Considering | Manual credential entry path for firmware 2.7+ users where BLE pairing is blocked by Play Integrity / App Attest |
| Considering | Multi-zone lighting writes (per-zone colour selects)                 |
| Considering | Wider lighting-model coverage beyond SLX / FLX                       |
| Considering | Confirm timer write path against firmware 2.7+                       |
| Considering | Surface BLE-only fields (Summer timer config readback) where viable  |
| Wishlist    | Multi-controller support in a single HA install                      |
| Wishlist    | Optional energy / runtime statistics exposed via Energy dashboard    |
| Wishlist    | Cleaner per-firmware capability detection                            |
| Wishlist    | Better wording across UI strings and translations beyond English     |
| Wishlist    | More example dashboards and a proper docs site                       |

Writing and docs are a known weak point. Improvements welcome. PRs against existing wording are fine.

## Limitations

- One firmware tested: `pbver 2.3`. Newer firmware (notably 2.7+) may not pair over Bluetooth. Track the relevant repo issue.
- One cloud session per chlorinator. If the phone app connects, HA gets bumped. Cooperate via the cloud-session controls.
- Lighting model coverage is currently SLX/FLX-style. Other lighting models may report different colour-index semantics.
- Per-zone independent lighting writes are not exposed as separate entities. Lighting controls default to Zone 0.

## Reporting issues

Bugs and unexpected behaviour: [GitHub Issues](https://github.com/robmarkoski/pychlorinator-cloud/issues).
Security issues: [SECURITY.md](SECURITY.md). Don't include real device serial numbers, full packet captures, or session tokens in public issues.
Feature requests: open an issue with a `feature-request` prefix.

When filing a bug, include:

- Integration version (the AstralPool Halo Cloud card in Settings, Devices & services)
- Home Assistant version
- Controller firmware (`pbver`) from the Firmware Version sensor
- Debug logs for `pychlorinator_cloud` and `custom_components.astralpool_halo_cloud`

## License

MIT. See [LICENSE](LICENSE).

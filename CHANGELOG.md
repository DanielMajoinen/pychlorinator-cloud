# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0-preview.1] - 2026-05-23

First public preview release of the cloud-first architecture. This is a
substantial reset on top of 0.2.3. the cloud-mode connection path,
entity layout, and configuration flow have all changed.

### Added

- Cloud-first runtime: WebSocket signalling against
  the vendor cloud after a one-off BLE pairing step.
- Over 100 entities across sensors, binary sensors, selects, numbers,
  and buttons covering chemistry, pump, lighting, timers, heater
  demand, diagnostics, and cloud-session control.
- **Bundled Lovelace cards**: `halo-timer-card` (8-slot equipment timer
  editor with Winter/Summer season switching and vendor-app parity UX)
  and `halo-schedule-view` (read-only day/week timeline).
- Heater demand schedule (read + write) including master enable,
  optional time-window restriction, and an activation flag.
- Per-zone light controls including light mode readback and custom
  valve names.
- AI / Auto / Manual pump modes with mode-aware speed surfacing and
  vendor-app-parity speed change tracking.
- Pause / Resume Cloud Connection controls so the vendor app or a BLE
  client can be used temporarily without uninstalling.
- Equipment timer write support (write back to 0x0193) with
  readback-confirmation safety.
- Hide Error button and structured error-code sensor with
  severity / category attributes.
- Firmware version, Wi-Fi RSSI, cell runtime, cooling-fan, dosing-pump,
  and board-temperature diagnostic sensors.
- HACS-custom-repository install path with `hacs.json`.
- MIT license and `SECURITY.md` describing the provenance of the
  hardcoded vendor cloud credentials.

### Changed

- Connection model rewritten end to end. The 0.2.x BLE-direct
  architecture is replaced by cloud-after-pair.
- Timer surfacing now matches the vendor app: 8 slots per Winter and
  Summer season with per-slot equipment chips.
- Pump-speed selector no longer flaps Medium/High on echo frames.
- Connection lifecycle hardened: non-blocking setup, bounded backoff,
  fail-closed keepalive with an application-layer time poll alongside
  the JSON heartbeat.

### Removed

- BLE-direct operation (BLE is now used only during the one-off
  pairing flow).
- Custom-minute maintenance period number entities. replaced by
  fixed-duration selects.

### Known Limitations

- Tested on a single firmware version (`pbver 2.3`). Other firmware
  versions, controller variants, regions, and accessory combinations
  are untested.
- Cloud-relay simultaneous sessions are limited by the vendor; do not
  run a BLE-based Halo integration against the same chlorinator at
  the same time.

---

## [0.2.3] - 2024 / earlier

Earlier BLE-direct releases. See git tag history (`v0.2.2`, `v0.2.3`)
for the prior architecture.

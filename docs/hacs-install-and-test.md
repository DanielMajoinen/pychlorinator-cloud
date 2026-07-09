# HACS install and test checklist

## Purpose / scope

This checklist is for testing the AstralPool Halo Cloud custom integration via a HACS custom repository install.

## Before starting

- Confirm HACS is already installed in Home Assistant.
- Confirm the GitHub repository URL you plan to add in HACS: `https://github.com/robmarkoski/pychlorinator-cloud`
- Confirm the intended branch/track:
  - `main` = stable
  - `beta` = beta testing
  - `dev` = experimental
- Note that an exact chlorinator firmware version is not yet recorded in the repository docs.
- This project is unofficial, reverse-engineered, and should be used at your own risk.

## HACS install steps

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/robmarkoski/pychlorinator-cloud` as a custom repository.
3. Choose **Integration** as the repository type.
4. Install from `main` first.
5. Restart Home Assistant.
6. Go to **Settings -> Devices & Services**.
7. Add **AstralPool Halo Cloud**.

## What to test during installation

- HACS can see the repository and install it successfully.
- No dependency or manual-copy step is needed for `pychlorinator_cloud`.
- Home Assistant restart completes cleanly.
- The integration appears in **Devices & Services** after restart.
- The config flow opens successfully.
- The manual credential path behaves correctly.
- The BLE path is only exercised if you intentionally want to test it.

## Post-install validation checklist

- The integration loads successfully.
- Entities appear as expected.
- Existing core entities update correctly:
  - mode
  - pump speed
  - water temperature
  - chlorine status
  - info message
- New binary sensors appear and make sense, especially:
  - `low_salt`
  - `no_flow`
  - `sanitising_active`
  - `filtering_only`
  - `sampling_active`
  - `standby`
  - `reduced_output_low_temperature`
  - `manual_acid_dose_active`
  - `backwashing`
- Confirm `water_too_cold` is **not** exposed as a binary sensor anymore.
- Check that entity names and object IDs look acceptable under the current device-scoped naming strategy.
- Check there is no obvious startup blocking, traceback noise, or retry spam in logs.

## 1.0 release gate: BLE pairing must be proven

BLE pairing-based onboarding should be considered a required gate before calling this integration an official 1.0 stable release.

If BLE pairing is not proven end to end, the integration should be treated as **beta/preview** rather than 1.0 stable.

Required checks for the 1.0 gate:

- Fresh install path is tested, not just an upgrade over an already-working setup.
- BLE discovery works as expected.
- Pairing succeeds and password retrieval behaves correctly.
- A config entry is created successfully from the pairing-based flow.
- The first cloud connection succeeds after pairing-based onboarding.
- Entities load successfully after onboarding completes.
- A Home Assistant restart still comes back healthy, with reconnect working correctly after pairing-based setup.

## Branch / track testing

- Test `main` first.
- Only test `beta` after the stable path is proven.
- Only use `dev` for explicit experimental testing.
- HACS release/prerelease support should get cleaner once tagged GitHub releases exist.

## What to capture if something fails

- Exact branch used.
- HACS install error text.
- Relevant Home Assistant log snippet.
- Whether the failure happened during install, restart, config flow, or entity load.
- Whether this was a fresh install, upgrade, or reinstall.

## Recommended test order

1. Fresh HACS install from `main`.
2. Restart Home Assistant and confirm the integration appears in **Devices & Services**.
3. Complete the config flow with the normal manual credential path.
4. Validate entity creation, updates, and binary sensor behaviour.
5. Check logs for startup issues or retry noise.
6. Only after `main` looks solid, repeat on `beta` if you want release-candidate coverage.
7. Only test `dev` if you explicitly want experimental coverage or deeper troubleshooting.

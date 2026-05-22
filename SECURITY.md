# Security & Credentials

## Vendor Cloud Credentials

This integration includes two hardcoded values used to authenticate the
WebSocket signalling session against the vendor cloud:

- `SIGNALLING_AUTH_USERNAME`
- `SIGNALLING_AUTH_PASSWORD`

**These are not personal credentials.** They are the hardcoded HTTP Basic
authentication values embedded in every copy of the official **Halo Chlor GO**
mobile app (iOS / Android). They are extracted directly from the public app
binary, ship in every install of the vendor app, and are functionally a
public protocol parameter rather than a secret.

Without them, no client. vendor or otherwise. can talk to the chlorinator's
cloud relay. Publishing them here is necessary for the integration to work
out of the box from HACS without each user needing to perform their own
reverse engineering of the vendor app.

If the vendor rotates these values in a future app release, this integration
will stop working until they are updated.

## Reporting Security Issues

If you find a security issue in this code (an injection vector in the
WebSocket parser, an unsafe deserialization path, a credential-leak bug in
the config flow, etc.), please open a GitHub issue or email the maintainer
listed in `manifest.json`. Do **not** include real device serial numbers,
session tokens, or full packet captures in public issues.

## What is NOT a security issue

- The presence of `SIGNALLING_AUTH_USERNAME` / `SIGNALLING_AUTH_PASSWORD` in
  the source tree (see above).
- The integration speaking to AstralPool's cloud. this is by design.
- Use of the (cloud-required) Bluetooth onboarding flow to retrieve
  device-generated cloud credentials. The credentials are stored locally in
  Home Assistant config entry data and never leave your installation.

## Not Affiliated

This project is not affiliated with AstralPool, Astral, Fluidra, or Astral
Labs. It is an independent, unofficial, community integration.

"""Constants for the AstralPool Halo Cloud integration."""

from __future__ import annotations

DOMAIN = "astralpool_halo_cloud"

CONF_SERIAL_NUMBER = "serial_number"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEVICE_NAME = "device_name"
CONF_AREA_ID = "area_id"
CONF_TIME_DRIFT_THRESHOLD_MINUTES = "time_drift_threshold_minutes"
CONF_CONNECTION_PAUSE_MINUTES = "connection_pause_minutes"
CONF_POST_PAIR_CLOUD_SETTLE_UNTIL = "post_pair_cloud_settle_until"

# After BLE pairing, the controller/relay can report chlorinator_unavailable or
# actively close fresh cloud sessions while the BLE leg is released. The vendor
# app does not immediately open a relay session after pairing; mirror that by
# letting the coordinator wait before its first cloud connect.
POST_PAIR_CLOUD_SETTLE_SECONDS = 60

PLATFORMS = ["sensor", "binary_sensor", "select", "number", "button"]


def default_device_name(serial_number: str | None) -> str:
    """Return the default Home Assistant device name for a Halo chlorinator."""
    if serial_number:
        return f"Halo {serial_number}"
    return "Halo Chlorinator"

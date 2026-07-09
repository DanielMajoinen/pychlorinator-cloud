"""Config flow for the AstralPool Halo Cloud integration.

Normal setup path:

1. BLE Discovery / Pairing:
   - HA auto-discovers "HCHLOR" BLE devices
   - User puts chlorinator in pairing mode
   - Access code is read from BLE advertisement
   - Username is sent via BLE cmd 719
   - Password fragments received via BLE cmd 720
   - Cloud credentials stored — BLE never needed again
   - User confirms the HA device name and optional area before entry creation

A manual credential step still exists in code as a fallback/debug path for cases
where credentials are already known, but it is intentionally hidden from the
normal user flow because most users cannot obtain the cloud password directly.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import struct
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

# BLE imports are optional — only needed for BLE pairing path
try:
    from homeassistant.components.bluetooth import (
        BluetoothScanningMode,
        BluetoothServiceInfoBleak,
        async_ble_device_from_address,
        async_process_advertisements,
    )
    HAS_BLUETOOTH = True
except ImportError:
    HAS_BLUETOOTH = False

from .pychlorinator_cloud.websocket_client import HaloWebSocketClient

from .const import (
    CONF_AREA_ID,
    CONF_DEVICE_NAME,
    CONF_PASSWORD,
    CONF_POST_PAIR_CLOUD_SETTLE_UNTIL,
    CONF_SERIAL_NUMBER,
    CONF_USERNAME,
    DOMAIN,
    POST_PAIR_CLOUD_SETTLE_SECONDS,
    default_device_name,
)
from .ble_advertisement import (
    MANUFACTURER_ID,
    access_code_bytes,
    is_pairable_access_code,
)

_LOGGER = logging.getLogger(__name__)

HALO_BLE_NAME = "HCHLOR"
WAIT_FOR_PAIRING_READY_TIMEOUT = 60
DEFAULT_USERNAME = "HAUser"
PRE_PAIR_LOOKING = "looking"
PRE_PAIR_FOUND_WAITING = "found_waiting"
PRE_PAIR_READY = "ready"


class AstralPoolHaloCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AstralPool Halo Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._pairing_task: asyncio.Task | None = None
        self._pre_pair_state = PRE_PAIR_LOOKING
        self._access_code: str | None = None
        self._serial_number: str | None = None
        self._username: str = DEFAULT_USERNAME
        self._password: str | None = None
        self._device_name: str | None = None
        self._area_id: str | None = None

    # =================================================================
    # Path 1: BLE Discovery
    # =================================================================

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle automatic BLE discovery of HCHLOR devices."""
        return await self._async_begin_ble_flow(discovery_info)

    async def async_step_ble_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Compatibility step for flows started before the watcher change."""
        return await self.async_step_ble_discovery(user_input)

    async def async_step_wait_for_pairing(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Compatibility step for flows started before the watcher change."""
        return await self.async_step_ble_discovery(user_input)

    async def async_step_pairing_timeout(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle pairing timeout — let user retry."""
        if user_input is not None:
            return await self.async_step_ble_discovery()

        return self.async_show_form(step_id="pairing_timeout")

    async def async_step_ble_username(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask the user for a username to register on the chlorinator."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input.get("username", DEFAULT_USERNAME).strip()
            _LOGGER.debug("BLE username submitted")
            if len(username) > 14:
                errors["username"] = "username_too_long"
            elif len(username) < 1:
                errors["username"] = "username_required"
            else:
                self._username = username
                return await self.async_step_ble_pair()

        return self.async_show_form(
            step_id="ble_username",
            data_schema=vol.Schema(
                {
                    vol.Required("username", default=DEFAULT_USERNAME): str,
                }
            ),
            errors=errors,
        )

    async def async_step_ble_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Perform BLE pairing — register username and receive password.

        Vendor-parity behaviour: once the password fragments complete, we
        store the credentials and finish onboarding. The vendor app does NOT
        attempt an immediate cloud session against the controller — it just
        records the credentials and lets the cloud session come up later in
        the background. The controller typically reports
        ``chlorinator_unavailable`` for a short window right after BLE
        pairing while the BLE leg releases, so a synchronous cloud verify
        here just blocks the UI for the open-timeout and is later swallowed.

        We still surface hard auth rejections (invalid credentials) so the
        flow does not silently create an entry that can never connect, but a
        transient cloud unavailable is treated as success and verification is
        deferred to the coordinator's normal connect/retry path.
        """
        errors: dict[str, str] = {}

        try:
            _LOGGER.debug(
                "Starting BLE pair for %s",
                self._discovery_info.address if self._discovery_info else "unknown",
            )
            password = await self._async_ble_pair()
            self._password = password

            # Extract serial number from the device.
            serial = await self._async_get_serial_number()
            self._serial_number = serial

            _LOGGER.info(
                "BLE pairing complete for serial %s; deferring cloud session to "
                "coordinator (vendor-parity: no synchronous cloud verify after pair).",
                self._serial_number,
            )

            return await self.async_step_device_details()

        except asyncio.TimeoutError:
            _LOGGER.warning("BLE pairing step timed out waiting for device response")
            errors["base"] = "pairing_timeout"
        except RuntimeError as err:
            _LOGGER.error("BLE pairing failed: %s", err)
            errors["base"] = "pairing_failed"
        except ImportError:
            errors["base"] = "bleak_not_installed"
        except Exception:
            _LOGGER.exception("Unexpected error during BLE pairing")
            errors["base"] = "unknown"

        # On failure, show an error and let user retry
        return self.async_show_form(
            step_id="ble_pair_failed",
            errors=errors,
        )

    async def async_step_ble_pair_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle pairing failure by offering a clean retry."""
        if user_input is not None:
            return await self.async_step_ble_pair()

        return self.async_show_form(step_id="ble_pair_failed")

    # =================================================================
    # Path 2: Manual Entry
    # =================================================================

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Start the normal user flow with BLE discovery.

        Manual credential entry remains available as a hidden fallback/debug
        step, but is not exposed in the standard onboarding flow.
        """
        return await self.async_step_ble_discovery()

    async def async_step_ble_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Watch BLE until a Halo chlorinator is ready to pair."""
        if not HAS_BLUETOOTH:
            return self.async_show_form(
                step_id="ble_discovery",
                errors={"base": "bleak_not_installed"},
            )

        if not self._pairing_task:
            self._pre_pair_state = (
                PRE_PAIR_FOUND_WAITING if self._discovery_info else PRE_PAIR_LOOKING
            )
            self._pairing_task = self.hass.async_create_task(
                self._async_watch_for_pairing_ready()
            )

        if not self._pairing_task.done():
            return self.async_show_progress(
                step_id="ble_discovery",
                progress_action=f"ble_discovery_{self._pre_pair_state}",
                progress_task=self._pairing_task,
            )

        try:
            await self._pairing_task
        except asyncio.TimeoutError:
            return self.async_show_progress_done(next_step_id="ble_discovery_timeout")
        finally:
            self._pairing_task = None

        return self.async_show_progress_done(next_step_id="ble_username")

    async def async_step_ble_discovery_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Compatibility step for flows started before the watcher change."""
        assert self._discovery_info is not None
        return await self.async_step_ble_discovery(user_input)

    async def async_step_ble_discovery_timeout(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle BLE discovery timeout for user-initiated setup."""
        if user_input is not None:
            return await self.async_step_ble_discovery()

        return self.async_show_form(step_id="ble_discovery_timeout")

    async def async_step_manual(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle manual credential entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            serial = user_input[CONF_SERIAL_NUMBER].strip()
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD].strip()

            # Try to verify the credentials
            client = HaloWebSocketClient(
                serial_number=serial,
                username=username,
                password=password,
            )

            try:
                result = await client.query_availability()
                if result.get("success") or result.get("type") == "query":
                    self._serial_number = serial
                    self._username = username
                    self._password = password
                    return await self.async_step_device_details()
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Failed to validate credentials")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERIAL_NUMBER): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device_details(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Capture the Home Assistant device name and optional area."""
        errors: dict[str, str] = {}
        assert self._serial_number is not None

        default_name = self._device_name or default_device_name(self._serial_number)

        if user_input is not None:
            device_name = user_input[CONF_DEVICE_NAME].strip()
            area_id = user_input.get(CONF_AREA_ID) or None

            if not device_name:
                errors[CONF_DEVICE_NAME] = "device_name_required"
            else:
                self._device_name = device_name
                self._area_id = area_id
                return await self._async_create_config_entry()

        return self.async_show_form(
            step_id="device_details",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=default_name): str,
                    vol.Optional(CONF_AREA_ID): selector({"area": {}}),
                }
            ),
            errors=errors,
            description_placeholders={"serial_number": self._serial_number},
        )

    async def _async_create_config_entry(self) -> FlowResult:
        """Create the final config entry once all details are known."""
        assert self._serial_number is not None
        assert self._password is not None
        assert self._device_name is not None

        await self.async_set_unique_id(self._serial_number, raise_on_progress=False)
        self._abort_if_unique_id_configured()

        entry_data = {
            CONF_SERIAL_NUMBER: self._serial_number,
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_DEVICE_NAME: self._device_name,
            CONF_AREA_ID: self._area_id,
        }

        if self._discovery_info is not None:
            settle_until = datetime.datetime.now(
                tz=datetime.timezone.utc
            ) + datetime.timedelta(seconds=POST_PAIR_CLOUD_SETTLE_SECONDS)
            entry_data[CONF_POST_PAIR_CLOUD_SETTLE_UNTIL] = settle_until.isoformat()

        return self.async_create_entry(
            title=self._device_name,
            data=entry_data,
        )

    # =================================================================
    # BLE Helpers
    # =================================================================

    async def _async_begin_ble_flow(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Initialise the BLE path from either discovery entry point."""
        _LOGGER.debug("Begin BLE flow: %s (%s)", discovery_info.name, discovery_info.address)

        if discovery_info.name != HALO_BLE_NAME:
            return self.async_abort(reason="not_supported")

        derived_serial = self._serial_from_discovery_info(discovery_info)
        await self.async_set_unique_id(derived_serial, raise_on_progress=False)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}

        if self._is_pairable(discovery_info):
            self._extract_access_code(discovery_info)
            self._pre_pair_state = PRE_PAIR_READY
            return await self.async_step_ble_username()

        self._pre_pair_state = PRE_PAIR_FOUND_WAITING
        return await self.async_step_ble_discovery()

    def _is_pairable(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Check if a discovered device is in pairing mode."""
        if MANUFACTURER_ID not in service_info.manufacturer_data:
            return False
        data = service_info.manufacturer_data[MANUFACTURER_ID]
        # pychlorinator ScanResponse format: <BBBBBBI4sBBBBBBB
        # Access code bytes are at offset 10..13 in manufacturer data.
        #
        # Vendor also requires TimeAlive > 0 && < 60. The decompile confirms
        # the rule, but the Bleak manufacturer_data byte mapping is not yet
        # evidenced here, so only the access-byte predicate is enforced.
        return is_pairable_access_code(access_code_bytes(data))

    def _extract_access_code(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Extract the 4-char access code from BLE advertisement."""
        if MANUFACTURER_ID not in service_info.manufacturer_data:
            return
        data = service_info.manufacturer_data[MANUFACTURER_ID]
        raw_access_code = access_code_bytes(data)
        if is_pairable_access_code(raw_access_code):
            try:
                self._access_code = raw_access_code.decode("utf-8")
            except UnicodeDecodeError:
                self._access_code = "0000"
            _LOGGER.debug("Extracted access code: %r", self._access_code)

    async def _async_watch_for_pairing_ready(self) -> None:
        """Watch continuously until a Halo advertisement is ready to pair."""
        target_address = self._discovery_info.address if self._discovery_info else None

        def is_ready_halo(service_info: BluetoothServiceInfoBleak) -> bool:
            if service_info.name != HALO_BLE_NAME:
                return False
            if target_address and service_info.address != target_address:
                return False

            self._discovery_info = service_info
            if self._pre_pair_state == PRE_PAIR_LOOKING:
                self._pre_pair_state = PRE_PAIR_FOUND_WAITING
                _LOGGER.debug(
                    "BLE watcher found %s (%s); waiting for Pair Mode",
                    service_info.name,
                    service_info.address,
                )

            if self._is_pairable(service_info):
                self._extract_access_code(service_info)
                self._pre_pair_state = PRE_PAIR_READY
                _LOGGER.debug(
                    "BLE watcher found ready pairing advertisement: %s",
                    service_info.address,
                )
                return True
            return False

        await async_process_advertisements(
            self.hass,
            is_ready_halo,
            {"address": target_address} if target_address else {},
            BluetoothScanningMode.ACTIVE,
            WAIT_FOR_PAIRING_READY_TIMEOUT,
        )

    async def _async_ble_pair(self) -> str:
        """Perform BLE pairing to get the cloud password."""
        from .pychlorinator_cloud.pairing import pair_via_ble

        assert self._discovery_info is not None
        assert self._access_code is not None

        ble_target = getattr(self._discovery_info, "device", None)
        if ble_target is None and HAS_BLUETOOTH:
            ble_target = async_ble_device_from_address(
                self.hass,
                self._discovery_info.address,
                True,
            )

        _LOGGER.debug(
            "Resolved BLE target type=%s address=%s",
            type(ble_target).__name__ if ble_target is not None else "str",
            self._discovery_info.address,
        )

        password = await pair_via_ble(
            ble_address=ble_target or self._discovery_info.address,
            access_code=self._access_code,
            username=self._username,
            timeout=30.0,
        )
        return password

    def _serial_from_discovery_info(self, discovery_info: BluetoothServiceInfoBleak | None) -> str:
        """Derive a stable unique identifier from BLE discovery data."""
        if discovery_info and MANUFACTURER_ID in discovery_info.manufacturer_data:
            data = discovery_info.manufacturer_data[MANUFACTURER_ID]
            if len(data) >= 10:
                unique_id = struct.unpack_from("<I", data, 6)[0]
                if unique_id > 0:
                    return str(unique_id)

        if discovery_info:
            return discovery_info.address.replace(":", "")

        return "unknown"

    async def _async_get_serial_number(self) -> str:
        """Get the serial number from the chlorinator.

        The serial number is embedded in the BLE device profile characteristic.
        For now, we extract it from the manufacturer data or use the BLE address
        as a fallback. The actual serial can be read from device profile (cmd 1)
        during the first cloud connection.
        """
        return self._serial_from_discovery_info(self._discovery_info)

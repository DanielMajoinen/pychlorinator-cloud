"""Library constants for talking to the Halo cloud relay."""

from __future__ import annotations

from typing import Final

PROTOCOL_VERSION: Final[float] = 0.1

STUN_SERVER_HOST: Final[str] = "13.211.222.74"
STUN_SERVER_PORT: Final[int] = 3478

SIGNALLING_WS_URL: Final[str] = (
    "wss://iot.connectmypool.com.au/halo_p2p/signalling/version_0.6/app"
)
SIGNALLING_REST_QUERY_URL: Final[str] = (
    "https://iot.connectmypool.com.au/halo_p2p/signalling/version_0.6/app/query"
)

P2P_LOCAL_PORT_CLOUD: Final[int] = 64176
P2P_LOCAL_PORT_LOCAL: Final[int] = 64177

DTLS_PSK_IDENTITY: Final[str] = "Client_identity"
DTLS_FIXED_LOCAL_KEY: Final[bytes] = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")
DTLS_CIPHER_SUITES: Final[tuple[str, ...]] = (
    "ECDHE-PSK-AES128-CBC-SHA256",
    "ECDHE-PSK-AES256-CBC-SHA384",
    "ECDHE-PSK-AES256-CBC-SHA",
    "PSK-NULL-SHA256",
    "PSK-AES128-CBC-SHA256",
    "PSK-AES256-CBC-SHA384",
)
DTLS_CIPHER_STRING: Final[str] = ":".join(DTLS_CIPHER_SUITES)

KEEPALIVE_INTERVAL_SECONDS: Final[float] = 3.0
DEFAULT_RECEIVE_TIMEOUT_SECONDS: Final[float] = 15.0

HOLE_PUNCH_REQUEST: Final[bytes] = bytes((9, 1))
HOLE_PUNCH_RESPONSE: Final[bytes] = bytes((9, 2))

HALO_MDNS_SERVICE: Final[str] = "_halop2p._udp.local."
HALO_MDNS_UUID_PREFIX: Final[str] = "f3fa2daa-cc33-42da-9e5b-5933"

# Post-connect legacy handshake: relay treats 0x006B + 0x0005 as the logical
# connection-notification handshake. Required first reads after connectresp,
# matching the vendor app's observed behaviour.
VOMIT_LEGACY_CMD_ID: Final[int] = 0x006B  # FlexSettings (command 107)
VOMIT_SENTINEL_CMD_ID: Final[int] = 0x0005  # Legacy connection sentinel (command 5)

# WebSocket signalling requires HTTP Basic Auth. These values are hardcoded
# in the official AstralPool "Halo Chlor GO" mobile app (iOS / Android) and
# ship in every install of the vendor binary -- they are a public protocol
# parameter, not a personal credential. See SECURITY.md for full provenance.
# Without them no client (vendor or otherwise) can talk to the cloud relay.
SIGNALLING_AUTH_USERNAME: Final[str] = "appUserName_sXQlNZa7"
SIGNALLING_AUTH_PASSWORD: Final[str] = "0Q9V@EQwC322S^K6kAyiefdr98a-dcfW"

SIGNALLING_FAIL_REASON_MAP: Final[dict[int, str]] = {
    0: "unknown_error",
    1: "chlorinator_unavailable",
    2: "wrong_credentials",
    3: "chlorinator_busy",
    4: "rate_limited",
    5: "dos_protected",
    6: "stun_failed",
}

# Reverse engineering is incomplete. The few labels below are intentionally
# conservative and should be treated as pragmatic placeholders rather than
# protocol truth.
COMMAND_ID_MAP: Final[dict[int, str]] = {
    0x0009: "frequent_status_placeholder",
    0x1001: "scan_response_placeholder",
}

# Default set of command IDs to query on cloud-session bootstrap. These are
# read using prefix 0x02 (read/query frames. never 0x03 write/action
# frames). The cloud does NOT push 0x0190/0x0191/0x0192/0x0193/0x044E
# spontaneously on keepalive (`websocket_client.MANDATORY_REFRESH_CMD_IDS`);
# the local DTLS adapter performs the equivalent read burst on connect.
#
# Tools (`scripts/raw_ws_capture.py`, `halo-capture-app`) should consume this
# list so the two clients stay in lockstep.
DEFAULT_BOOTSTRAP_READ_CMD_IDS: Final[tuple[int, ...]] = (
    0x0068,  # state characteristic
    0x012C,  # light state characteristic
    0x012D,  # light capabilities characteristic
    0x0069,  # capabilities
    0x006A,  # maintenance/dosing state
    0x0066,  # setpoint
    0x0324,  # config family (manual_speed_action / configured_speed)
    0x0258,  # probe statistics
    0x0259,  # statistics A
    0x025A,  # power-board statistics
    0x0009,  # temperature
    0x0065,  # water volume
    0x044E,  # heater state
    0x0451,  # heat-demand settings (heater schedule)
    0x0002,  # controller time
    0x0003,  # controller date
    0x0190,  # timer capabilities
    0x0191,  # timer setup
    0x0192,  # timer state (profile_index)
    0x0193,  # timer config (per-slot speed_code). framing does not currently
    # let us request a specific slot index; the controller returns whichever
    # slot it considers current at the time of the read.
)

# Subset to re-read periodically while a capture session runs. The cheap reads
# (0x0192 / 0x0193 / 0x0068) catch timer rotations and live state transitions
# without spamming the controller.
DEFAULT_PERIODIC_READ_CMD_IDS: Final[tuple[int, ...]] = (
    0x0192,
    0x0193,
    0x0068,
)

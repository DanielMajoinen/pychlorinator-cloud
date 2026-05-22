"""Tests for controller notice/fault binary sensor logic."""

from __future__ import annotations

from pychlorinator_cloud.error_codes import (
    controller_fault_active,
    controller_notice_active,
)
from pychlorinator_cloud.websocket_client import ChlorinatorLiveData


def _data(raw_code: int | None, severity: str | None) -> ChlorinatorLiveData:
    data = ChlorinatorLiveData()
    data.salt_error_raw = raw_code
    data.error_severity = severity
    return data


def test_controller_notice_active_when_error_code_nonzero() -> None:
    assert controller_notice_active(_data(707, "Information")) is True
    assert controller_notice_active(_data(0, None)) is False
    assert controller_notice_active(_data(None, None)) is None


def test_controller_fault_active_only_when_severity_is_fault() -> None:
    assert controller_fault_active(_data(707, "Information")) is False
    assert controller_fault_active(_data(1, "Fault")) is True
    assert controller_fault_active(_data(9, "Warning")) is False


def test_707_is_notice_not_fault() -> None:
    data = _data(707, "Information")

    assert controller_notice_active(data) is True
    assert controller_fault_active(data) is False


def test_hardware_fault_is_notice_and_fault() -> None:
    data = _data(1, "Fault")

    assert controller_notice_active(data) is True
    assert controller_fault_active(data) is True

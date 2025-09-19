"""Firmware compatibility helpers for Tailwind devices."""

from __future__ import annotations

from awesomeversion import AwesomeVersion, AwesomeVersionStrategy

from gotailwind.const import MIN_REQUIRED_FIRMWARE_VERSION
from gotailwind.exceptions import TailwindUnsupportedFirmwareVersionError
from gotailwind.models import TailwindDeviceStatus, TailwindResponse

NEW_HARDWARE_PREFIX = "iq3 2"
NEW_HARDWARE_MIN_VERSION = AwesomeVersion(
    "1.00", ensure_strategy=AwesomeVersionStrategy.SIMPLEVER
)

# Cache to avoid re-patching when module reloads under tests
_PATCHED = False


def _parse_version(version: str) -> AwesomeVersion:
    """Parse a firmware version string using SIMPLEVER semantics."""
    return AwesomeVersion(version, ensure_strategy=AwesomeVersionStrategy.SIMPLEVER)


def minimum_supported_version(product: str | None) -> AwesomeVersion:
    """Return the minimum supported firmware version for a product."""
    if product and product.lower().startswith(NEW_HARDWARE_PREFIX):
        return NEW_HARDWARE_MIN_VERSION
    return MIN_REQUIRED_FIRMWARE_VERSION


def is_supported_firmware(version: str, product: str | None) -> bool:
    """Check if the firmware version is supported for the given product."""
    return _parse_version(version) >= minimum_supported_version(product)


def _patch_tailwind_models() -> None:
    """Adjust Tailwind model validation to accept new hardware firmware versions."""
    global _PATCHED
    if _PATCHED:
        return

    original_method = TailwindDeviceStatus.__pre_deserialize__

    def _patched_pre_deserialize(
        cls: type[TailwindDeviceStatus], data: dict[str, object]
    ) -> dict[str, object]:
        version = data.get("fw_ver")
        product = data.get("product")
        if isinstance(version, str) and not is_supported_firmware(version, product):
            min_version = minimum_supported_version(product)
            msg = (
                f"Unsupported firmware version {version}. "
                f"Minimum required version is {min_version}. "
                "Please update your Tailwind device."
            )
            raise TailwindUnsupportedFirmwareVersionError(msg)

        TailwindResponse.__pre_deserialize__(data)
        for door_id, door in data.get("data", {}).items():
            if isinstance(door, dict):
                door["door_id"] = door_id
        return data

    _patched_pre_deserialize.__doc__ = original_method.__doc__
    TailwindDeviceStatus.__pre_deserialize__ = classmethod(_patched_pre_deserialize)

    _PATCHED = True


_patch_tailwind_models()

__all__ = [
    "is_supported_firmware",
    "minimum_supported_version",
]

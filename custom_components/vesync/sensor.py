"""Sensors for VeSync devices."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from py_vesync import normalize_program_key

from .const import DOMAIN
from .coordinator import VeSyncCoordinator, is_airfryer_device
from .entity import VeSyncEntity

COOK_STATUS_OPTIONS = [
    "standby",
    "cooking",
    "cookend",
    "cookstop",
    "preheat",
    "heating",
    "keepwarm",
    "pause",
    "pullout",
    "end",
    "off",
]
PROGRAM_OPTIONS = [
    "air_fry",
    "bake",
    "broil",
    "chicken",
    "french_fries",
    "frozen",
    "normal",
    "reheat",
    "roast",
    "seafood",
    "steak",
    "veggies",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VeSync sensors."""
    coordinator: VeSyncCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for cid, state in (coordinator.data or {}).items():
        entities.append(VeSyncRssiSensor(coordinator, cid))
        if is_airfryer_device(state.device):
            entities.extend(
                [
                    VeSyncCookStatusSensor(coordinator, cid),
                    VeSyncProgramSensor(coordinator, cid),
                    VeSyncTemperatureSensor(coordinator, cid),
                    VeSyncRemainingTimeSensor(coordinator, cid),
                    VeSyncElapsedTimeSensor(coordinator, cid),
                    VeSyncLastCookDurationSensor(coordinator, cid),
                ]
            )
    async_add_entities(entities)


class VeSyncCookStatusSensor(VeSyncEntity, SensorEntity):
    """Translatable cook status sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = COOK_STATUS_OPTIONS

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "cook_status")

    @property
    def native_value(self) -> str | None:
        state = self._state
        if state is None or not state.status:
            return None
        val = str(state.status.get("cookStatus") or "").strip().lower()
        return val or None


class VeSyncProgramSensor(VeSyncEntity, SensorEntity):
    """Translatable active or last-used program sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PROGRAM_OPTIONS

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "program")

    @property
    def native_value(self) -> str | None:
        state = self._state
        if state is None:
            return None
        if state.last_completed_session and not state.is_running and state.last_completed_session.program_key:
            return state.last_completed_session.program_key
        if state.status:
            step0 = (state.status.get("stepArray") or [None])[0]
            if isinstance(step0, dict) and step0.get("mode"):
                return normalize_program_key(step0.get("mode"))
            return normalize_program_key(state.status.get("cookMode"))
        return None


class VeSyncTemperatureSensor(VeSyncEntity, SensorEntity):
    """Current cavity temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "current_temperature")

    @property
    def native_unit_of_measurement(self) -> str:
        state = self._state
        unit = str((state.status if state else {}).get("tempUnit") or "c").lower()
        return UnitOfTemperature.FAHRENHEIT if unit == "f" else UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> int | None:
        state = self._state
        if state is None or not state.status:
            return None
        return state.status.get("currentTemp")


class VeSyncRemainingTimeSensor(VeSyncEntity, SensorEntity):
    """Remaining cooking time reported by the device."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "remaining_time")

    @property
    def native_value(self) -> int | None:
        state = self._state
        if state is None or not state.status:
            return None
        return state.status.get("totalTimeRemaining")


class VeSyncElapsedTimeSensor(VeSyncEntity, SensorEntity):
    """Live elapsed seconds of the current cooking session."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "elapsed_time")

    @property
    def native_value(self) -> float | None:
        state = self._state
        return state.elapsed_seconds if state is not None else None


class VeSyncLastCookDurationSensor(VeSyncEntity, SensorEntity):
    """Measured real duration of the last completed cooking session."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "last_cook_duration")

    @property
    def native_value(self) -> float | None:
        state = self._state
        if state is None or state.last_completed_session is None:
            return None
        return state.last_completed_session.actual_seconds

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._state
        if state is None or state.last_completed_session is None:
            return {}
        return {k: v for k, v in asdict(state.last_completed_session).items() if not k.startswith("_")}


class VeSyncRssiSensor(VeSyncEntity, SensorEntity):
    """Wi-Fi RSSI diagnostic sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "rssi")

    @property
    def native_value(self) -> int | None:
        state = self._state
        return state.device.rssi if state is not None else None

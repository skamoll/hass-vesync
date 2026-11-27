"""Binary sensors for VeSync devices."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VeSyncCoordinator, is_airfryer_device
from .entity import VeSyncEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VeSync binary sensors."""
    coordinator: VeSyncCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    for cid, state in (coordinator.data or {}).items():
        entities.append(VeSyncOnlineBinarySensor(coordinator, cid))
        if is_airfryer_device(state.device):
            entities.append(VeSyncRunningBinarySensor(coordinator, cid))
    async_add_entities(entities)


class VeSyncRunningBinarySensor(VeSyncEntity, BinarySensorEntity):
    """Indicates whether the air fryer is currently active."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "running")

    @property
    def is_on(self) -> bool | None:
        state = self._state
        return state.is_running if state is not None else None


class VeSyncOnlineBinarySensor(VeSyncEntity, BinarySensorEntity):
    """Indicates whether the device is connected to VeSync cloud."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "online")

    @property
    def is_on(self) -> bool | None:
        state = self._state
        if state is None:
            return None
        return state.device.connection_status.lower() == "online"

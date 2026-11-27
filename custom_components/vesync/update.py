"""Firmware update entities for VeSync devices."""

from __future__ import annotations

from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VeSyncCoordinator
from .entity import VeSyncEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VeSync firmware update entities."""
    coordinator: VeSyncCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        VeSyncFirmwareUpdate(coordinator, cid)
        for cid, state in (coordinator.data or {}).items()
        if state.device.current_firmware or state.device.latest_firmware
    ]
    async_add_entities(entities)


class VeSyncFirmwareUpdate(VeSyncEntity, UpdateEntity):
    """Reports installed and latest firmware versions for a VeSync device."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "firmware")

    @property
    def installed_version(self) -> str | None:
        state = self._state
        return state.device.current_firmware if state is not None else None

    @property
    def latest_version(self) -> str | None:
        state = self._state
        return state.device.latest_firmware if state is not None else None

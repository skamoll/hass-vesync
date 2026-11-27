"""Button entities for VeSync devices."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up VeSync button entities."""
    coordinator: VeSyncCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        VeSyncStopButton(coordinator, cid)
        for cid, state in (coordinator.data or {}).items()
        if is_airfryer_device(state.device)
    ]
    async_add_entities(entities)


class VeSyncStopButton(VeSyncEntity, ButtonEntity):
    """Stops active cooking on the air fryer via endCook."""

    def __init__(self, coordinator: VeSyncCoordinator, cid: str) -> None:
        super().__init__(coordinator, cid, "stop")

    async def async_press(self) -> None:
        state = self._state
        if state is None:
            return
        await self.coordinator.client.end_cook(self._cid, state.device.config_module)
        await self.coordinator.async_request_refresh()

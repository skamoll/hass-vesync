"""Image entity exposing the VeSync device photo."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up VeSync device image entities."""
    coordinator: VeSyncCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        VeSyncDeviceImage(hass, coordinator, cid)
        for cid, state in (coordinator.data or {}).items()
        if state.device.image_url or state.device.default_image_url
    ]
    async_add_entities(entities)


class VeSyncDeviceImage(VeSyncEntity, ImageEntity):
    """Official product image for a VeSync device."""

    def __init__(self, hass: HomeAssistant, coordinator: VeSyncCoordinator, cid: str) -> None:
        VeSyncEntity.__init__(self, coordinator, cid, "device_image")
        ImageEntity.__init__(self, hass)

    @property
    def image_url(self) -> str | None:
        state = self._state
        if state is None:
            return None
        return state.device.image_url or state.device.default_image_url

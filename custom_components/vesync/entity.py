"""Base entity for VeSync devices."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DeviceRuntimeState, VeSyncCoordinator


class VeSyncEntity(CoordinatorEntity[VeSyncCoordinator]):
    """Base entity bound to a VeSync device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VeSyncCoordinator, cid: str, key: str) -> None:
        super().__init__(coordinator)
        self._cid = cid
        self._attr_unique_id = f"{cid}_{key}"
        self._attr_translation_key = key

    @property
    def _state(self) -> DeviceRuntimeState | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._cid)

    @property
    def device_info(self) -> DeviceInfo:
        state = self._state
        if state is None:
            return DeviceInfo(identifiers={(DOMAIN, self._cid)})
        dev = state.device
        connections = {(CONNECTION_NETWORK_MAC, dev.mac_id)} if dev.mac_id else set()
        return DeviceInfo(
            identifiers={(DOMAIN, dev.cid)},
            connections=connections,
            name=dev.name,
            manufacturer="VeSync",
            model=dev.device_type or None,
            sw_version=dev.current_firmware,
            suggested_area=dev.room_name or None,
        )

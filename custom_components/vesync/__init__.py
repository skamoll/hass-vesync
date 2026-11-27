"""The VeSync integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_END_COOK,
    SERVICE_SET_COOK_TIME,
    SERVICE_SET_TEMP_UNIT,
    SERVICE_START_COOK,
)
from .coordinator import DeviceRuntimeState, VeSyncCoordinator

PRESET_RECIPE_IDS: dict[str, int] = {
    "Steak": 1,
    "Chicken": 2,
    "Seafood": 3,
    "Frozen": 5,
    "Reheat": 10,
    "Bake": 11,
    "French fries": 12,
    "Roast": 13,
    "AirFry": 14,
    "Veggies": 15,
    "Broil": 17,
}


def _resolve_target(hass: HomeAssistant, cid: str | None) -> tuple[VeSyncCoordinator, DeviceRuntimeState]:
    entries: dict[str, VeSyncCoordinator] = hass.data.get(DOMAIN, {})
    for coordinator in entries.values():
        data = coordinator.data or {}
        if cid and cid in data:
            return coordinator, data[cid]
        if not cid and len(data) == 1:
            only_state = next(iter(data.values()))
            return coordinator, only_state
    raise HomeAssistantError(f"VeSync device not found for cid={cid!r}")


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_END_COOK):
        return

    async def handle_end_cook(call: ServiceCall) -> None:
        coordinator, state = _resolve_target(hass, call.data.get("cid"))
        await coordinator.client.end_cook(state.device.cid, state.device.config_module)
        await coordinator.async_request_refresh()

    async def handle_start_cook(call: ServiceCall) -> None:
        coordinator, state = _resolve_target(hass, call.data.get("cid"))
        mode = call.data["mode"]
        recipe_id = call.data.get("recipe_id") or PRESET_RECIPE_IDS.get(mode, 14)
        await coordinator.client.start_cook(
            state.device.cid,
            state.device.config_module,
            mode=mode,
            cook_seconds=call.data["cook_seconds"],
            cook_temp=call.data["cook_temp"],
            temp_unit=call.data["temp_unit"],
            recipe_id=recipe_id,
            preheat_temp=call.data["preheat_temp"],
            shake_seconds=call.data["shake_seconds"],
            has_warm=call.data["has_warm"],
        )
        await coordinator.async_request_refresh()

    async def handle_set_cook_time(call: ServiceCall) -> None:
        coordinator, state = _resolve_target(hass, call.data.get("cid"))
        await coordinator.client.set_cook_time(
            state.device.cid,
            state.device.config_module,
            call.data["cook_seconds"],
        )
        await coordinator.async_request_refresh()

    async def handle_set_temp_unit(call: ServiceCall) -> None:
        coordinator, state = _resolve_target(hass, call.data.get("cid"))
        await coordinator.client.set_temp_unit(
            state.device.cid,
            state.device.config_module,
            call.data["unit"],
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_END_COOK,
        handle_end_cook,
        schema=vol.Schema({vol.Optional("cid"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_COOK,
        handle_start_cook,
        schema=vol.Schema(
            {
                vol.Optional("cid"): cv.string,
                vol.Optional("mode", default="AirFry"): cv.string,
                vol.Optional("cook_seconds", default=600): vol.All(vol.Coerce(int), vol.Range(min=60, max=7200)),
                vol.Optional("cook_temp", default=180): vol.All(vol.Coerce(int), vol.Range(min=50, max=230)),
                vol.Optional("temp_unit", default="c"): vol.In(["c", "f"]),
                vol.Optional("recipe_id"): vol.Coerce(int),
                vol.Optional("preheat_temp", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=230)),
                vol.Optional("shake_seconds", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
                vol.Optional("has_warm", default=False): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COOK_TIME,
        handle_set_cook_time,
        schema=vol.Schema(
            {
                vol.Optional("cid"): cv.string,
                vol.Required("cook_seconds"): vol.All(vol.Coerce(int), vol.Range(min=60, max=7200)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TEMP_UNIT,
        handle_set_temp_unit,
        schema=vol.Schema(
            {
                vol.Optional("cid"): cv.string,
                vol.Required("unit"): vol.In(["c", "f"]),
            }
        ),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VeSync from a config entry."""
    coordinator = VeSyncCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await _async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

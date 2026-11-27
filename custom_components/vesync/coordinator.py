"""DataUpdateCoordinator for VeSync devices."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from py_vesync import (
    AsyncVeSyncClient,
    CookSession,
    CookSessionTracker,
    VeSyncAPIError,
    VeSyncAuthError,
    VeSyncDevice,
)

from .const import (
    CONF_ACCOUNT_ID,
    CONF_REGION,
    CONF_TERMINAL_ID,
    CONF_TOKEN,
    DEFAULT_ACTIVE_INTERVAL,
    DEFAULT_REGION,
    DEFAULT_STANDBY_INTERVAL,
    DOMAIN,
    EVENT_COOK_COMPLETED,
)

_LOGGER = logging.getLogger(__name__)


def is_airfryer_device(dev: VeSyncDevice) -> bool:
    """Return True if the device supports AirFryer bypassV2 status."""
    cfg = dev.config or {}
    if cfg.get("airFryerInfo") is not None:
        return True
    return dev.device_type.startswith("CAF-") or "_AFR_" in dev.config_module


@dataclass(slots=True)
class DeviceRuntimeState:
    """Combined device metadata, live status and session tracker."""

    device: VeSyncDevice
    status: dict[str, Any]
    is_running: bool
    elapsed_seconds: float
    last_completed_session: CookSession | None


class VeSyncCoordinator(DataUpdateCoordinator[dict[str, DeviceRuntimeState]]):
    """Coordinator managing VeSync devices and adaptive 10s/5s polling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_STANDBY_INTERVAL),
        )
        self.entry = entry
        self.client = AsyncVeSyncClient(
            region=entry.data.get(CONF_REGION, DEFAULT_REGION),
            http_client=get_async_client(hass),
        )
        self.client.restore_session(
            {
                "token": entry.data.get(CONF_TOKEN, ""),
                "account_id": entry.data.get(CONF_ACCOUNT_ID, ""),
                "region": entry.data.get(CONF_REGION, DEFAULT_REGION),
                "terminal_id": entry.data.get(CONF_TERMINAL_ID, ""),
            }
        )
        self._trackers: dict[str, CookSessionTracker] = {}

    async def _async_relogin(self) -> None:
        email = self.entry.data.get(CONF_EMAIL, "")
        password = self.entry.data.get(CONF_PASSWORD, "")
        if not email or not password:
            raise ConfigEntryAuthFailed("Missing VeSync credentials")
        try:
            await self.client.login(email, password)
        except VeSyncAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        session = self.client.export_session()
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                CONF_REGION: session["region"],
                CONF_TOKEN: session["token"],
                CONF_ACCOUNT_ID: session["account_id"],
                CONF_TERMINAL_ID: session["terminal_id"],
            },
        )

    async def _async_update_data(self) -> dict[str, DeviceRuntimeState]:
        try:
            devices = await self._fetch_devices_with_reauth()
        except (VeSyncAPIError, httpx.HTTPError) as err:
            raise UpdateFailed(f"Error communicating with VeSync: {err}") from err

        states: dict[str, DeviceRuntimeState] = {}
        any_running = False

        for dev in devices:
            status: dict[str, Any] = {}
            running = False
            elapsed = 0.0
            last_done: CookSession | None = None

            if is_airfryer_device(dev):
                tracker = self._trackers.setdefault(
                    dev.cid,
                    CookSessionTracker(
                        dev.cid,
                        device_name=dev.name,
                        standby_interval=float(DEFAULT_STANDBY_INTERVAL),
                        active_interval=float(DEFAULT_ACTIVE_INTERVAL),
                    ),
                )
                try:
                    status = await self.client.get_airfryer_status(dev.cid, dev.config_module)
                except VeSyncAuthError:
                    await self._async_relogin()
                    status = await self.client.get_airfryer_status(dev.cid, dev.config_module)
                except (VeSyncAPIError, httpx.HTTPError) as err:
                    _LOGGER.debug("Status fetch failed for %s: %s", dev.cid, err)

                if status:
                    running, _, completed = tracker.update(status)
                    if running and tracker.active_session is not None and not tracker.active_session.program_name:
                        await self._enrich_session(tracker, dev)
                    if completed is not None:
                        self._fire_cook_completed(completed)
                    elapsed = tracker.current_elapsed_seconds
                    last_done = tracker.last_completed_session
                    any_running = any_running or running

            states[dev.cid] = DeviceRuntimeState(
                device=dev,
                status=status,
                is_running=running,
                elapsed_seconds=elapsed,
                last_completed_session=last_done,
            )

        target_seconds = DEFAULT_ACTIVE_INTERVAL if any_running else DEFAULT_STANDBY_INTERVAL
        self.update_interval = timedelta(seconds=target_seconds)
        return states

    async def _fetch_devices_with_reauth(self) -> list[VeSyncDevice]:
        try:
            return await self.client.get_devices_full()
        except VeSyncAuthError:
            await self._async_relogin()
            return await self.client.get_devices_full()

    async def _enrich_session(self, tracker: CookSessionTracker, dev: VeSyncDevice) -> None:
        try:
            page = await self.client.get_cooking_history(dev.cid, dev.config_module, page_size=1)
            latest = (page.get("cookHistoryList") or [None])[0]
            tracker.enrich_from_history_entry(latest)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not enrich session from history for %s", dev.cid)

    def _fire_cook_completed(self, session: CookSession) -> None:
        payload = {k: v for k, v in asdict(session).items() if not k.startswith("_")}
        self.hass.bus.async_fire(EVENT_COOK_COMPLETED, payload)

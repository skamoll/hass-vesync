# hass-vesync

Home Assistant custom integration for VeSync devices powered by [`py-vesync`](https://github.com/skamoll/py-vesync).

## Features

- UI configuration flow (`EU` / `US` regions, automatic cross-region redirect and token persistence).
- Discovers all devices with full metadata (model, firmware version, room, MAC, Wi-Fi RSSI, product image).
- Adaptive polling: 10s in `standby`, automatically switching to 5s while cooking.
- Measures real cook duration (`last_cook_duration` + `vesync_cook_completed` event) and live `elapsed_time`.
- Multi-language support (`en`, `es`) for status and cooking programs.

## Installation (HACS)

1. Add `https://github.com/skamoll/hass-vesync` as a custom repository in HACS (category: Integration).
2. Install **VeSync** and restart Home Assistant.
3. Add the integration via **Settings -> Devices & Services -> Add Integration -> VeSync**.

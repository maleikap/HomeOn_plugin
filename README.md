<p align="center">
  <img src="brand/homeon-logo.svg" alt="HomeOn" width="600">
</p>

<p align="center">
  Integracja HomeOn Automation dla Home Assistant
</p>

---

# HomeOn Automation for Home Assistant

Custom Home Assistant integration for a HomeOn controller connected through a local WebSocket server.

## Features

- Local push communication through WebSocket
- Relay outputs exposed as lights
- Blinds exposed as covers, including position control
- Temperature sensors
- Counters
- Automatic reconnection after a network or controller interruption
- Configuration through the Home Assistant user interface
- Installation and updates through HACS

## Installation through HACS

1. Put this repository on GitHub.
2. In HACS open **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Paste the GitHub repository address and select **Integration**.
5. Install **HomeOn Automation**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration** and search for **HomeOn Automation**.
8. Enter the controller/server IP address and WebSocket port. The default port is `18080`.

## Manual installation

Copy `custom_components/homeon` to the Home Assistant configuration directory:

```text
/config/custom_components/homeon
```

Restart Home Assistant and add the integration from **Settings → Devices & services**.

## Repository preparation

Before publishing, replace `OWNER` in `custom_components/homeon/manifest.json` with your GitHub account or organization name. Optionally add the GitHub username to `codeowners`.

Use semantic GitHub release tags, for example:

```text
v2.0.0
```

## Diagnostics

Add this temporarily to `configuration.yaml` when debugging:

```yaml
logger:
  logs:
    custom_components.homeon: debug
```

## Protocol compatibility

The integration keeps the original HomeOn JSON commands and notifications:

- `get_aliases`
- `get_config`
- `set_output`
- `set_percent`
- `is_config`
- `is_output`
- `is_percent`
- `is_temperature`
- `is_counter`

The controller is currently queried using device address `1`, matching the original integration.

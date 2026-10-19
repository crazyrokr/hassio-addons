# Home Assistant Add-On: Obsidian

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

## Summary

This add-on runs [Obsidian](https://obsidian.md/) — the full Markdown
knowledge-base desktop app — inside Home Assistant, so your notes, tasks, and
vaults live right next to your home automation. It is based on the
[LinuxServer.io Obsidian](https://docs.linuxserver.io/images/docker-obsidian)
image and is delivered to the HA interface through the Selkies web UI on
add-on ingress, which means the whole app works from a browser tab or the HA
side panel — no separate VNC client needed.

The add-on is not just "Obsidian in a container": it integrates with Home
Assistant as a first-class citizen. Since version 0.9.0 it follows the active
Home Assistant theme in real time — switching HA to dark mode re-themes
Obsidian, the streamed desktop background, and the web UI chrome around it,
all without a restart.

## Features

- **Obsidian inside Home Assistant.** The full Obsidian app streamed over the
  Selkies web UI on port 3000 — open it from the add-on **Web UI**, the HA
  side panel, or standalone via the exposed HTTP (3000) / HTTPS (3001) ports.
- **Adaptive theme sync.** The add-on matches Obsidian's theme to the active
  Home Assistant theme: dark HA themes switch Obsidian to `obsidian` (dark),
  light ones to `moonstone`. Detection is luminance-based (WCAG relative
  luminance of the HA background color), so it works with stock themes *and*
  custom community themes. Re-syncs are event-driven (CSS-variable mutations
  plus `prefers-color-scheme` changes) with zero idle cost, and the change is
  applied live through the Obsidian CLI — no add-on restart.
- **New vaults inherit the last theme.** A background watcher on Obsidian's
  vault registry (inotify, idle cost zero) applies the remembered theme to
  vaults created after the last sync and reloads the app; vaults that already
  existed keep their user-chosen theme.
- **Desktop background mirrors the theme.** The desktop behind the streamed
  session is painted in the exact HA background color — the Xvfb root window
  in X mode, the nested labwc compositor (via `swaybg`) in Wayland mode — and
  the last color is restored at boot.
- **The web UI follows the theme too.** Selkies' pre-stream "waiting for
  stream" screen, the streaming letterbox bars, and the dashboard chrome
  (sidebar, settings, notifications) track the active HA theme from first
  paint.
- **Safe by design.** Theme writes go through a loopback-only daemon
  (`127.0.0.1:8090`) behind nginx, with strict API semantics (400 on
  unknown themes, 404 elsewhere) and atomic, ownership-safe writes to the
  vault's `appearance.json`.
- **aarch64 & amd64.** Built on the digest-pinned LinuxServer.io Obsidian
  base image (`v1.13.7-ls144`), with Renovate keeping the pin current.

## How to Install

1. **Add the add-on repository.** In Home Assistant go to
   **Settings → Add-ons → Add-on store**, open the ⋮ menu in the top-right
   corner and choose **Repositories**, then add:

   ```text
   https://github.com/crazyrokr/hassio-addons
   ```

   and click **Reload**.

2. **Install the add-on.** The **Obsidian** add-on now appears in the add-on
   store — install it.

3. **Open it.** Use the add-on's **Web UI** link or the side panel. No
   configuration is required for the theme sync: the first sync happens
   automatically the moment the page loads, and every later HA theme switch
   is picked up live.

4. **Your vault.** The default vault lives in the add-on's config directory
   (`/config`), which is persisted across updates. Additional vaults can be
   placed under the add-on's `share` mount.

## How the theme sync works

A small script injected into the Selkies web UI reads the active HA theme
(luminance-based, from the parent window; browser `prefers-color-scheme` when
standalone) and posts it to a loopback daemon through nginx. The daemon
resolves the active vault, writes `appearance.json` atomically, repaints the
desktop background in the theme's color, and reloads the running app via the
Obsidian system CLI. The full design, a defect log of the first draft, and an
end-to-end verification guide live in [`docs/ha-obsidian-theme-sync.md`](docs/ha-obsidian-theme-sync.md);
the decision record is in
[`docs/adr/0001-obsidian-ha-theme-sync.md`](docs/adr/0001-obsidian-ha-theme-sync.md).

## Documentation

- [`docs/ha-obsidian-theme-sync.md`](docs/ha-obsidian-theme-sync.md) — theme
  synchronization: architecture, verified base-image facts, step-by-step
  breakdown, troubleshooting.
- [`docs/adr/0001-obsidian-ha-theme-sync.md`](docs/adr/0001-obsidian-ha-theme-sync.md) —
  architecture decision record for the theme sync.
- [`docs/security-gates-implementation.md`](docs/security-gates-implementation.md) —
  CI/CD security gates plan (dependency scan, Trivy, cosign, SBOM).

## License

[MIT License](LICENSE)

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg

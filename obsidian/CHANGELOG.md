## 0.9.3
Update Obsidian to [v1.14.5](https://obsidian.md/changelog/2026-10-22-desktop-v1.14.5/) and linuxserver to [ls150](https://hub.docker.com/layers/linuxserver/obsidian/v1.14.5-ls150/images/sha256-0bf1a3caea94802cbe9fd61dbd241f66e6f8b179f8bbacc222dd5ed92699d758)

## 0.9.1
Update linuxserver/obsidian version to [v1.14.4-ls149](https://hub.docker.com/layers/linuxserver/obsidian/v1.14.4-ls149/images/sha256-956cb0841329585e65e943351a5c1180ae72de5da3704506dee3b35d3155337e)

## 0.9.0
✨ Features — Adaptive theme (#24)

- Apply the active HA theme to Obsidian — loopback daemon (theme_server.py, s6 service on 127.0.0.1:8090) + client script in the Selkies web UI; vault resolved per request, atomic appearance.json writes
- Live reload via the Obsidian system CLI — init-obsidian-cli s6-rc oneshot merges "cli": true into the global config after /config is chowned; reloads target the CLI binary, not the app launcher
- Event-driven re-sync — prefers-color-scheme change event + MutationObserver on the parent document replace 15 s polling; failed sends retried up to 3 times
- New vaults inherit the last requested theme — inotify-based watcher on the vault registry (polling only as fallback); pre-existing vaults are never overwritten
- Desktop background mirrors the theme color — xsetroot on Xvfb (X mode) / swaybg client of the nested labwc (Wayland), supervisor thread, restored at boot; color validated against theme (light color + dark theme → 400)
- Selkies web UI follows the theme — pre-stream screen, letterbox bars, and dashboard chrome (sidebar, settings, notifications) rethemed from first paint
- Refactors — reorganize folder structure; all resources copied via COPY root /; theme + color unified into one parent read; reload skipped when the theme is unchanged
- Base image — swaybg installed, build-time nginx/Selkies hooks against the regeneration sources, run scripts executable in source
- Quality — 2,607 lines of pytest + 702 of node tests, ADR 0001, theme-sync design doc;

🔧 Fixes — Renovate / image pinning

- fix(renovate): monitor and append the LinuxServer image revision (#22)
- fix(renovate): loose versioning for lscr.io docker images (#19)
- Update Renovate regex patterns (#12)
- Finish auto-pinning — pins the lscr.io/linuxserver/obsidian digest in config.yaml

## 0.7.0
Update linuxserver/obsidian version to [v1.12.7-ls131](https://hub.docker.com/layers/linuxserver/obsidian/v1.12.7-ls131/images/sha256-6004393da17c50afacd9c81ae7130bf245cac3bb85f75d312b0142e9adfcc9ca)

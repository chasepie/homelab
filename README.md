# Homelab

Docker Compose configurations for my self-hosted homelab infrastructure, managed across multiple hosts with [Komodo](https://komo.do/).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Pangolin VPS                                           │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │ Pangolin  │  │  Gerbil   │  │     Traefik       │    │
│  │ (tunnel)  │  │(WireGuard)│  │ (reverse proxy)   │    │
│  └───────────┘  └───────────┘  └───────────────────┘    │
│  ┌───────────┐                                          │
│  │Healthchks │                                          │
│  └───────────┘                                          │
└─────────────────────────────────────────────────────────┘
            │ WireGuard tunnel
┌───────────┴─────────────────────────────────────────────┐
│  Unraid Server (NVIDIA GPU)                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │  Immich   │  │ Open WebUI│  │ Komodo Periphery  │    │
│  │ (photos)  │  │ + Ollama  │  │  (node agent)     │    │
│  └───────────┘  └───────────┘  └───────────────────┘    │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │ Pangolin  │  │  Karakeep │  │  Actual Budget    │    │
│  │   Newt    │  │(bookmarks)│  │  (finances)       │    │
│  └───────────┘  └───────────┘  └───────────────────┘    │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │   ROMM    │  │  Site     │  │  Red DiscordBot   │    │
│  │  (ROMs)   │  │  Checker  │  │                   │    │
│  └───────────┘  └───────────┘  └───────────────────┘    │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │1Password  │  │Healthchks │  │  Grafana + Loki   │    │
│  │ Connect   │  │           │  │  (logging)        │    │
│  └───────────┘  └───────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi 01                                        │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │Nginx Proxy│  │  Pi-hole  │  │     Komodo        │    │
│  │  Manager  │  │           │  │  (infra mgmt)     │    │
│  └───────────┘  └───────────┘  └───────────────────┘    │
│  ┌───────────┐                                          │
│  │Healthchks │                                          │
│  └───────────┘                                          │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi 02                                        │
│  ┌───────────┐  ┌───────────────────┐  ┌───────────┐    │
│  │  Pi-hole  │  │ Komodo Periphery  │  │Healthchks │    │
│  │           │  │  (node agent)     │  │           │    │
│  └───────────┘  └───────────────────┘  └───────────┘    │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi 03                                        │
│  ┌───────────────────┐  ┌───────────┐                   │
│  │ Komodo Periphery  │  │Healthchks │                   │
│  │  (node agent)     │  │           │                   │
│  └───────────────────┘  └───────────┘                   │
└─────────────────────────────────────────────────────────┘
```

## Services

### Tunneling & Reverse Proxy

| Service                                               | Directory                     | Description                                                            |
| ----------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------- |
| [Pangolin](https://github.com/fosrl/pangolin)         | `docker/pangolin/`            | Tunnel orchestrator with Gerbil (WireGuard) and Traefik reverse proxy. |
| [Pangolin Newt](https://github.com/fosrl/newt)        | `docker/pangolin-newt/`       | Tunnel client connecting local services to the Pangolin VPS.           |
| [Nginx Proxy Manager](https://nginxproxymanager.com/) | `docker/nginx-proxy-manager/` | Local network reverse proxy running on a Raspberry Pi.                 |

### Media & Storage

| Service                                 | Directory        | Description                                                                                                       |
| --------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------- |
| [Immich](https://immich.app/)           | `docker/immich/` | Self-hosted photo/video management with NVIDIA GPU-accelerated ML inference (CUDA) and video transcoding (NVENC). |
| [ROMM](https://github.com/rommapp/romm) | `docker/romm/`   | ROM library manager with metadata scraping from IGDB, SteamGridDB, RetroAchievements, and more.                   |

### AI & LLM

| Service                                       | Directory            | Description                                                                    |
| --------------------------------------------- | -------------------- | ------------------------------------------------------------------------------ |
| [Open WebUI](https://openwebui.com/) + Ollama | `docker/open-webui/` | LLM frontend and Ollama inference server running on all available NVIDIA GPUs. |

### Productivity

| Service                                              | Directory               | Description                                                                                              |
| ---------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------- |
| [Actual Budget](https://actualbudget.org/)           | `docker/actual-budget/` | Personal finance manager with AI-powered transaction classification via Ollama.                          |
| [Karakeep](https://github.com/karakeep-app/karakeep) | `docker/karakeep/`      | Web archiving and bookmarking with AI tagging/summarization (Ollama) and full-text search (Meilisearch). |

### Infrastructure & Monitoring

| Service                                                  | Directory                  | Description                                                                                               |
| -------------------------------------------------------- | -------------------------- | --------------------------------------------------------------------------------------------------------- |
| [Komodo](https://komo.do/)                               | `docker/komodo/`           | Infrastructure management dashboard. Manages deployments across all hosts (Unraid, VPS, Raspberry Pis).   |
| [Komodo Periphery](https://komo.do/)                     | `docker/komodo-periphery/` | Komodo node agent running on Unraid and all Raspberry Pis for local Docker management.                    |
| [Grafana + Loki](https://grafana.com/oss/loki/)          | `docker/grafana-loki/`     | Log aggregation (Loki), visualization (Grafana), and collection (Alloy) stack with OpenTelemetry support. |
| [Healthchecks](https://healthchecks.io/)                 | `docker/healthchecks/`     | Cron/scheduled task ping monitoring. Deployed on all hosts for uptime visibility.                         |
| [Site Checker](https://github.com/chasepie/site-checker) | `docker/site-checker/`     | Multi-network site monitoring with headless Chrome, including a PIA VPN exit for geo-testing.             |

### Networking & Security

| Service                                                            | Directory           | Description                                                                                                        |
| ------------------------------------------------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [Pi-hole](https://pi-hole.net/)                                    | `docker/pi-hole/`   | Network-wide DNS sinkhole for ad blocking. Two instances deployed across both Raspberry Pis for high availability. |
| [1Password Connect](https://developer.1password.com/docs/connect/) | `docker/1password/` | Secret management API used by Komodo and other services for credential injection.                                  |

### Other

| Service                                                          | Directory                | Description          |
| ---------------------------------------------------------------- | ------------------------ | -------------------- |
| [Red DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) | `docker/red-discordbot/` | Modular Discord bot. |

## Secrets Management

Secrets are managed through [1Password Connect](https://developer.1password.com/docs/connect/) and the 1Password CLI (`op`). Services reference secrets via `op://` URIs which are resolved at container startup. See [unraid/README.md](unraid/README.md) for 1Password CLI installation on Unraid.

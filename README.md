# Homelab

Docker Compose configurations for my self-hosted homelab infrastructure, managed across multiple hosts with [Komodo](https://komo.do/).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Pangolin VPS                                                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │ Pangolin  │  │  Gerbil   │  │     Traefik       │            │
│  │ (tunnel)  │  │(WireGuard)│  │ (reverse proxy)   │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────────────┐  ┌───────────────────┐    │
│  │Healthchks │  │ Komodo Periphery  │  │  Uptime Kuma      │    │
│  │           │  │  (node agent)     │  │  (monitoring)     │    │
│  └───────────┘  └───────────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
            │ WireGuard tunnel
┌───────────┴─────────────────────────────────────────────────────┐
│  Unraid Server (NVIDIA GPU)                                     │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │  Immich   │  │ Open WebUI│  │ Komodo Periphery  │            │
│  │ (photos)  │  │ + Ollama  │  │  (node agent)     │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │ Pangolin  │  │  Karakeep │  │  Actual Budget    │            │
│  │   Newt    │  │(bookmarks)│  │  (finances)       │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │   ROMM    │  │  Site     │  │  Red DiscordBot   │            │
│  │  (ROMs)   │  │  Checker  │  │                   │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │1Password  │  │Healthchks │  │  Grafana + Loki   │            │
│  │ Connect   │  │           │  │  (logging)        │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │  MeTube   │  │  Firefox  │  │  SparkyFitness    │            │
│  │(downloads)│  │ (browser) │  │  (fitness)        │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐                                                  │
│  │  acme.sh  │                                                  │
│  │  (certs)  │                                                  │
│  └───────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  Raspberry Pi 01                                                │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │Nginx Proxy│  │  Pi-hole  │  │     Komodo        │            │
│  │  Manager  │  │           │  │  (infra mgmt)     │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────────────┐                           │
│  │Healthchks │  │  Semaphore UI     │                           │
│  │           │  │  (Ansible UI)     │                           │
│  └───────────┘  └───────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  Raspberry Pi 02                                                │
│  ┌───────────┐  ┌───────────────────┐  ┌───────────┐            │
│  │  Pi-hole  │  │ Komodo Periphery  │  │Healthchks │            │
│  │           │  │  (node agent)     │  │           │            │
│  └───────────┘  └───────────────────┘  └───────────┘            │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  Raspberry Pi 03                                                │
│  ┌───────────────────┐  ┌───────────┐                           │
│  │ Komodo Periphery  │  │Healthchks │                           │
│  │  (node agent)     │  │           │                           │
│  └───────────────────┘  └───────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## Services

### Tunneling & Reverse Proxy

| Service                                               | Directory                     | Description                                                            |
| ----------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------- |
| [Pangolin](https://pangolin.net)                      | `docker/pangolin/`            | Tunnel orchestrator with Gerbil (WireGuard) and Traefik reverse proxy. |
| [Pangolin Newt](https://github.com/fosrl/newt)        | `docker/pangolin-newt/`       | Tunnel client connecting local services to the Pangolin VPS.           |
| [Nginx Proxy Manager](https://nginxproxymanager.com/) | `docker/nginx-proxy-manager/` | Local network reverse proxy running on a Raspberry Pi.                 |

### Media & Storage

| Service                                      | Directory        | Description                                                                                                       |
| -------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------- |
| [Immich](https://immich.app/)                | `docker/immich/` | Self-hosted photo/video management with NVIDIA GPU-accelerated ML inference (CUDA) and video transcoding (NVENC). |
| [ROMM](https://romm.app)                     | `docker/romm/`   | ROM library manager with metadata scraping from IGDB, SteamGridDB, RetroAchievements, and more.                   |
| [MeTube](https://github.com/alexta69/metube) | `docker/metube/` | Web frontend for yt-dlp for downloading videos and audio from YouTube and other sites.                            |

### AI & LLM

| Service                                       | Directory            | Description                                                                    |
| --------------------------------------------- | -------------------- | ------------------------------------------------------------------------------ |
| [Open WebUI](https://openwebui.com/) + Ollama | `docker/open-webui/` | LLM frontend and Ollama inference server running on all available NVIDIA GPUs. |

### Productivity

| Service                                                       | Directory                | Description                                                                                              |
| ------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------- |
| [Actual Budget](https://actualbudget.org/)                    | `docker/actual-budget/`  | Personal finance manager with AI-powered transaction classification via Ollama.                          |
| [Karakeep](https://karakeep.app)                              | `docker/karakeep/`       | Web archiving and bookmarking with AI tagging/summarization (Ollama) and full-text search (Meilisearch). |
| [SparkyFitness](https://github.com/codewithcj/sparky-fitness) | `docker/sparky-fitness/` | Fitness and health tracking with Garmin integration and a PostgreSQL backend.                            |
| [Firefox](https://github.com/linuxserver/docker-firefox)      | `docker/firefox/`        | Containerized Firefox browser accessible via web UI.                                                     |

### Infrastructure & Monitoring

| Service                                                  | Directory                  | Description                                                                                               |
| -------------------------------------------------------- | -------------------------- | --------------------------------------------------------------------------------------------------------- |
| [Komodo](https://komo.do/)                               | `docker/komodo/`           | Infrastructure management dashboard. Manages deployments across all hosts (Unraid, VPS, Raspberry Pis).   |
| [Komodo Periphery](https://komo.do/)                     | `docker/komodo-periphery/` | Komodo node agent running on the VPS, Unraid, and all Raspberry Pis for local Docker management.          |
| [Grafana + Loki](https://grafana.com/oss/loki/)          | `docker/grafana-loki/`     | Log aggregation (Loki), visualization (Grafana), and collection (Alloy) stack with OpenTelemetry support. |
| [Healthchecks](https://healthchecks.io/)                 | `docker/healthchecks/`     | Cron/scheduled task ping monitoring. Deployed on all hosts for uptime visibility.                         |
| [Uptime Kuma](https://github.com/louislam/uptime-kuma)   | `docker/uptime-kuma/`      | Uptime monitoring and status page running on the Pangolin VPS.                                            |
| [Semaphore UI](https://semaphoreui.com/)                 | `docker/semaphore-ui/`     | Web UI for running and scheduling Ansible playbooks.                                                      |
| [Site Checker](https://github.com/chasepie/site-checker) | `docker/site-checker/`     | Multi-network site monitoring with headless Chrome, including a PIA VPN exit for geo-testing.             |

### Networking & Security

| Service                                                            | Directory           | Description                                                                                                        |
| ------------------------------------------------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [Pi-hole](https://pi-hole.net/)                                    | `docker/pi-hole/`   | Network-wide DNS sinkhole for ad blocking. Two instances deployed across both Raspberry Pis for high availability. |
| [1Password Connect](https://developer.1password.com/docs/connect/) | `docker/1password/` | Secret management API used by Komodo and other services for credential injection.                                  |
| [acme.sh](https://github.com/acmesh-official/acme.sh)              | `docker/acme/`      | Automated TLS certificate management via Let's Encrypt using the Porkbun DNS challenge.                            |

### Other

| Service                                                          | Directory                | Description          |
| ---------------------------------------------------------------- | ------------------------ | -------------------- |
| [Red DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot) | `docker/red-discordbot/` | Modular Discord bot. |

## Ansible

Ansible playbooks for automating server management are in the [`ansible/`](ansible/) directory. See [ansible/README.md](ansible/README.md) for usage and playbook documentation.

## Secrets Management

Secrets are managed through [1Password Connect](https://developer.1password.com/docs/connect/) and the 1Password CLI (`op`). Services reference secrets via `op://` URIs which are resolved at container startup. See [unraid/README.md](unraid/README.md) for 1Password CLI installation on Unraid.

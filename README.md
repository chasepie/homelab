# Homelab

Declarative configuration for my self-hosted homelab: Docker Compose stacks
spread across three Raspberry Pis, an Unraid server and a gaming PC, deployed by
[Komodo](https://komo.do/).

Everything lives on the LAN. Nginx Proxy Manager is the only reverse proxy and
nothing is published to the internet.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Raspberry Pi 5 - 01  ("Local" — Komodo control plane)          │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │   Komodo  │  │Nginx Proxy│  │  Komodo Periphery │            │
│  │(core + UI)│  │  Manager  │  │    (node agent)   │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │  Pi-hole  │  │ 1Password │  │   Grafana + Loki  │            │
│  │  (DNS 1)  │  │  Connect  │  │   + Alloy (logs)  │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐                                   │
│  │    ROMM   │  │ Healthchks│                                   │
│  │   (ROMs)  │  │(heartbeat)│                                   │
│  └───────────┘  └───────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  Raspberry Pi 5 - 02                                            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │   Immich  │  │  Postgres │  │  Komodo Periphery │            │
│  │  (server) │  │  + Valkey │  │    (node agent)   │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │  Pi-hole  │  │   Actual  │  │    Site Checker   │            │
│  │  (DNS 2)  │  │   Budget  │  │  (+ PIA VPN exit) │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐                                   │
│  │   Samba   │  │ Healthchks│                                   │
│  │  (media)  │  │(heartbeat)│                                   │
│  └───────────┘  └───────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
     │ SMB media share + Postgres/Valkey on the LAN, remote ML over HTTP
┌─────────────────────────────────────────────────────────────────┐
│  Unraid Server  (RTX 3080, 12 GB)                               │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐            │
│  │   Immich  │  │ Immich ML │  │  Komodo Periphery │            │
│  │ microsvcs │  │   (CUDA)  │  │    (node agent)   │            │
│  └───────────┘  └───────────┘  └───────────────────┘            │
│  ┌───────────┐  ┌───────────┐                                   │
│  │  Valheim  │  │ Healthchks│                                   │
│  │ (Midgaard)│  │(heartbeat)│                                   │
│  └───────────┘  └───────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  Gaming PC  (RTX 5080, 16 GB — intermittent)                    │
│  ┌───────────┐  ┌───────────────────┐                           │
│  │ Immich ML │  │  Komodo Periphery │                           │
│  │  (CUDA 2) │  │    (node agent)   │                           │
│  └───────────┘  └───────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

Komodo Core runs on Pi 01 and dispatches stacks to a Periphery agent on every
other host. It pulls this repo and writes state back through Commit Sync, so
commits authored as `[Komodo]` come from the dashboard rather than a human. The
authoritative host assignment for each stack is
[docker/komodo/config.toml](docker/komodo/config.toml) — Pi 01 appears there as
the server named `Local`.

The gaming PC is not always on, so unreachable alerts are disabled for it and it
carries nothing but a second Immich ML endpoint.

## Services

### Photos & media

| Service                                      | Directory        | Description                                                                                                                                                                                                                                                                                  |
| -------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Immich](https://immich.app/)                | `docker/immich/` | Photo and video management, split across hosts: server, Postgres and Valkey on Pi 02, the GPU microservices worker and CUDA machine learning on Unraid, a second ML endpoint on the gaming PC. Media reaches the GPU hosts over SMB. See [docker/immich/README.md](docker/immich/README.md). |
| [ROMM](https://romm.app)                     | `docker/romm/`   | ROM library manager with metadata scraping from IGDB, SteamGridDB, RetroAchievements and more.                                                                                                                                                                                               |
| [MeTube](https://github.com/alexta69/metube) | `docker/metube/` | Web frontend for yt-dlp for downloading video and audio from YouTube and other sites.                                                                                                                                                                                                        |

### Home & productivity

| Service                                                       | Directory                | Description                                                                                                                                                                |
| ------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Actual Budget](https://actualbudget.org/)                    | `docker/actual-budget/`  | Personal finance manager.                                                                                                                                                  |
| [Karakeep](https://karakeep.app)                              | `docker/karakeep/`       | Web archiving and bookmarking with AI tagging and summarization through an OpenAI-compatible endpoint, headless Chrome for crawling, and full-text search via Meilisearch. |
| [SparkyFitness](https://github.com/codewithcj/sparky-fitness) | `docker/sparky-fitness/` | Fitness and health tracking with Garmin integration and a PostgreSQL backend.                                                                                              |
| [Homebridge](https://homebridge.io/)                          | `docker/homebridge/`     | Bridges non-HomeKit devices into Apple Home. Runs with host networking and Avahi so mDNS reaches the LAN.                                                                  |

### Gaming

| Service                                                                     | Directory                 | Description                                                                                                                                                                                         |
| --------------------------------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Valheim](https://github.com/community-valheim-tools/valheim-server-docker) | `docker/valheim-servers/` | One self-contained stack per world on Unraid, with crossplay through the PlayFab relay — players join by code, not by IP. See [docker/valheim-servers/README.md](docker/valheim-servers/README.md). |

### Infrastructure & monitoring

| Service                                                  | Directory                  | Description                                                                                                                                                  |
| -------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Komodo](https://komo.do/)                               | `docker/komodo/`           | Deployment dashboard and control plane, backed by FerretDB on Postgres. Manages every stack in this repo and syncs its own configuration back to it.         |
| [Komodo Periphery](https://komo.do/)                     | `docker/komodo-periphery/` | Node agent for local Docker management, running on every host Komodo deploys to.                                                                             |
| [Grafana + Loki](https://grafana.com/oss/loki/)          | `docker/grafana-loki/`     | Log aggregation: Alloy tails container logs into Loki, Grafana queries them. Proxied through Nginx Proxy Manager.                                            |
| [Healthchecks](https://healthchecks.io/)                 | `docker/healthchecks/`     | Per-host heartbeat — a small container that pings a healthchecks.io URL every five minutes, so a host that goes dark raises an alert. One instance per host. |
| [Site Checker](https://github.com/chasepie/site-checker) | `docker/site-checker/`     | Multi-network site monitoring with headless Chrome, including a PIA VPN exit for geo-testing.                                                                |

### Networking & security

| Service                                                            | Directory                     | Description                                                                                                |
| ------------------------------------------------------------------ | ----------------------------- | ---------------------------------------------------------------------------------------------------------- |
| [Nginx Proxy Manager](https://nginxproxymanager.com/)              | `docker/nginx-proxy-manager/` | The reverse proxy for the whole LAN. Owns the external `npm` Docker network that proxied stacks attach to. |
| [Pi-hole](https://pi-hole.net/)                                    | `docker/pi-hole/`             | Network-wide DNS sinkhole for ad blocking. Two instances, on Pi 01 and Pi 02, for high availability.       |
| [1Password Connect](https://developer.1password.com/docs/connect/) | `docker/1password/`           | Secret management API used by Komodo and the `op` CLI on each host for credential injection.               |

## Ansible

Playbooks for host management are in [`ansible/`](ansible/). See
[ansible/README.md](ansible/README.md) for the playbook and task catalog.

## Secrets management

Secrets are managed through
[1Password Connect](https://developer.1password.com/docs/connect/) and the
1Password CLI (`op`). Committed `compose.env` files hold `op://` URIs rather
than values, resolved at container start on the host; real `.env` files are
gitignored.

## Hosts & hardware

- [docs/hardware.md](docs/hardware.md) — what each machine is.
- [docs/hosts/unraid.md](docs/hosts/unraid.md) — 1Password CLI installation on Unraid.
- [docs/hosts/raspberry-pi.md](docs/hosts/raspberry-pi.md) — Raspberry Pi notes, including mounting a CIFS/SMB network share.

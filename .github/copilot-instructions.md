# Homelab Copilot Instructions

This repository contains Docker Compose configurations for a self-hosted homelab managed with [Komodo](https://komo.do/).

## Architecture

Three hosts are in use:

- **Pangolin VPS** — Public-facing entry point. Runs Pangolin (tunnel orchestrator), Gerbil (WireGuard), and Traefik (reverse proxy).
- **Unraid Server** (NVIDIA GPU) — Primary server. Runs most services. GPU used for CUDA ML inference (Immich) and NVENC transcoding, and Ollama LLM inference.
- **Raspberry Pi** — Runs Nginx Proxy Manager (local reverse proxy) and Pangolin Newt (tunnel client).

## Repository Structure

```
docker/<service-name>/
  compose.yaml      # Service definition
  compose.env       # Environment variables (loaded by Komodo, not Docker directly)
  config/           # Optional: additional config files
```

Each service lives in its own directory under `docker/`. There is no top-level compose file — each service is deployed independently by Komodo.

## Key Conventions

### Compose Files

- Use `compose.yaml` (not `docker-compose.yml`).
- Use `compose.env` for environment variables, not `.env`. These are loaded by Komodo's deployment system.
- Standard restart policy is `restart: unless-stopped`.
- Persist data to named volumes or bind mounts under `/mnt/main/appdata/<service>/` on Unraid.
- Use `container_name` to give containers stable names.

### Secrets Management

Secrets are managed via [1Password Connect](https://developer.1password.com/docs/connect/) using the `op` CLI. Reference secrets in `compose.env` files using `op://` URIs:

```env
MY_SECRET="op://VaultName/ItemName/FieldName"
MY_OTHER_SECRET="op://Dev/ServiceName/Environment Variables/VAR_NAME"
```

These are resolved at container startup when Komodo runs `op run -- docker compose up`. Never hardcode secrets or commit real credentials.

### Networking

- Services that need to be exposed publicly connect to the `pangolin` external network, which routes traffic through the Pangolin/Traefik reverse proxy.
- The `pangolin` network is created externally and referenced as:
  ```yaml
  networks:
    pangolin:
      external: true
  ```
- Internal-only services only use the default bridge network.

### Komodo Labels

Add `komodo.skip` label to containers that should not be stopped by Komodo's `StopAllContainers` action (e.g., databases, Komodo itself):

```yaml
labels:
  komodo.skip:
```

### GPU / Hardware Acceleration

For NVIDIA GPU workloads (on Unraid), use the `deploy.resources` section or `extends` from a hardware acceleration file:

```yaml
extends:
  file: hwaccel.transcoding.yml
  service: nvenc
```

## Adding a New Service

1. Create `docker/<service-name>/compose.yaml` — define the service(s).
2. Create `docker/<service-name>/compose.env` — define environment variables, using `op://` URIs for secrets.
3. If the service needs public access, attach it to the `pangolin` network and configure a route in Pangolin/Traefik.
4. Add the service to Komodo for deployment management.
5. Update `README.md` with a row in the appropriate services table.

## Services Overview

| Service | Host | Purpose |
|---|---|---|
| Pangolin + Gerbil + Traefik | VPS | Tunneling & public reverse proxy |
| Pangolin Newt | Raspberry Pi | Tunnel client |
| Nginx Proxy Manager | Raspberry Pi | Local reverse proxy |
| Immich | Unraid | Photo/video management (GPU) |
| ROMM | Unraid | ROM library manager |
| Open WebUI + Ollama | Unraid | LLM frontend + inference (GPU) |
| Actual Budget | Unraid | Personal finance |
| Karakeep | Unraid | Bookmarking + web archiving |
| Komodo + Periphery | Unraid | Infrastructure management |
| Grafana + Loki + Alloy | Unraid | Log aggregation + visualization |
| Healthchecks | Unraid | Cron ping monitoring |
| Site Checker | Unraid | Multi-network uptime monitoring |
| Pi-hole | Unraid | DNS ad blocking |
| 1Password Connect | Unraid | Secret management API |
| Red DiscordBot | Unraid | Discord bot |

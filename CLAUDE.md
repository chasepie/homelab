# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Declarative configuration for a self-hosted homelab: Docker Compose stacks under [docker/](docker/), Ansible automation under [ansible/](ansible/), and host-specific notes under [unraid/](unraid/). There is no application code to build, lint, or test — changes are configuration that gets deployed to physical hosts.

Deployment is orchestrated by [Komodo](https://komo.do/) (running on a Raspberry Pi) which pulls this repo and dispatches stacks to Komodo Periphery agents on each host (Pangolin VPS, Unraid server, three Raspberry Pis). The host that runs each stack is documented in the topology diagram in [README.md](README.md).

Komodo writes back to this repo via "Commit Sync" — commits authored as `[Komodo]` in `git log` come from the dashboard, not a human, and represent state pulled from a live host.

## Conventions for Docker stacks

Every service in [docker/](docker/) follows the same layout:

- `compose.yaml` — the stack definition
- `compose.env` — committed env file with **`op://` URIs** as values (not real secrets); resolved at container start by the 1Password CLI on the host. Real `.env` files are gitignored.
- Some stacks add extras (e.g. [docker/immich/](docker/immich/) has `hwaccel.*.yml`, [docker/komodo/](docker/komodo/) has `config.toml`).

When editing a `compose.env`, leave secrets as `op://Vault/Item/field` references — do not inline values.

### Shared external Docker networks

Several stacks attach to networks that are **declared external** and created out-of-band by their owning stack. Do not redefine them:

- `pangolin` — created by [docker/pangolin/](docker/pangolin/); used by services that need to be reachable through the Pangolin tunnel/Traefik on the VPS (e.g. [docker/immich/compose.yaml](docker/immich/compose.yaml)).
- `npm` — created by [docker/nginx-proxy-manager/](docker/nginx-proxy-manager/); used by services proxied through NPM on the local network (e.g. [docker/grafana-loki/](docker/grafana-loki/)).

### Hardware-accelerated services

Stacks that need the Unraid GPU (Immich ML/transcoding, Open WebUI + Ollama) use NVIDIA CUDA/NVENC image tags and `hwaccel.*.yml` extension files. These will not run on the Raspberry Pis.

## Ansible

Run playbooks from the [ansible/](ansible/) directory:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/<playbook>.yml
```

`inventory/hosts.ini` is gitignored; copy from `hosts.ini.example`. Requires the `community.docker` collection (`ansible-galaxy collection install -r requirements.yml`).

Playbook structure: top-level files in [ansible/playbooks/](ansible/playbooks/) are entry points; files in [ansible/tasks/](ansible/tasks/) are reusable includes split by distro family (`*.debian.yml` / `*.redhat.yml`) and are not run directly. When adding host-management logic, prefer extending a task file and including it from a playbook rather than inlining tasks. See [ansible/README.md](ansible/README.md) for the playbook/task catalog.

## Secrets

Managed via [1Password Connect](https://developer.1password.com/docs/connect/) ([docker/1password/](docker/1password/)) and the `op` CLI on each host. Unraid needs the CLI installed manually — see [unraid/README.md](unraid/README.md).

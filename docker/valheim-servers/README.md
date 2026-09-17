# Valheim Servers

One directory per world, each a self-contained stack deployed to Unraid, plus
shared helpers in `scripts/`. Adding a world means copying an existing
directory rather than editing a shared file.

| Path                    | Purpose                                              |
| ----------------------- | ---------------------------------------------------- |
| `Midgaard/`             | The Midgaard world — `compose.yaml` + `compose.env`  |
| `scripts/get-join-codes.sh` | Prints the current join code for every running world |

Images come from
[community-valheim-tools/valheim-server](https://github.com/community-valheim-tools/valheim-server-docker).

## Crossplay means join codes, not IP addresses

`CROSSPLAY=true` puts the server behind the PlayFab relay. It registers with
PlayFab on startup and clients connect through Azure, so the server **never
binds its game port** — there is nothing listening on `2456/udp` to connect to,
even on the LAN, and no port forwarding is required on the router.

Players join with **Join Game → Join by code**. The code is assigned by PlayFab
at session registration and **changes on every restart**, so there is no static
place to look it up; the server log is the only record:

```bash
./scripts/get-join-codes.sh           # on the host, where the repo is cloned
./scripts/get-join-codes.sh unraid    # from anywhere, via ~/.ssh/config
```

```
Midgaard         123456   0 online
```

`SERVER_PUBLIC=false` also keeps the worlds out of the public server browser,
so the code is the only way in.

To trade crossplay for direct-IP joining instead, set `CROSSPLAY=false` and
publish `2457/udp` alongside `2456/udp` — Valheim uses the second port for
Steam queries when joining by address. Non-Steam players lose access.

## Adding a world

Copy `Midgaard/`, rename it, and make three things unique:

1. **Host ports** — the game port and the supervisor port, e.g. `2466:2466/udp`
   and `9002:9001/tcp`. `SERVER_PORT` in `compose.env` must match the game port.
2. **Volume paths** — `/mnt/user/appdata/valheim-server-<world>/…`, or the two
   servers will fight over one save.
3. **`SERVER_NAME` / `WORLD_NAME`** — `get-join-codes.sh` labels its output with the
   session name from the log.

Keep `valheim` in the service name. `get-join-codes.sh` discovers worlds with
`docker ps --filter name=valheim`, so a new stack needs no change to the script,
but a service named otherwise will be invisible to it.

## Secrets

`compose.env` holds `op://` references, resolved at container start by the 1Password
CLI on Unraid. Real `.env` files are gitignored. Each world's password lives at
`op://Dev/Valheim Server/<World>/password`.

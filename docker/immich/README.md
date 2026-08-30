# Immich

Immich runs split across two hosts: the **server** (API, Postgres, Valkey) on a
Raspberry Pi, and a **microservices worker** on the Unraid box so that
transcoding and machine learning can use the NVIDIA GPU. See the topology
diagram in [../../README.md](../../README.md).

This split follows [immich-app/immich#14142](https://github.com/immich-app/immich/discussions/14142).

| File | Host | Purpose |
| --- | --- | --- |
| `compose.yaml` | Pi | Server, Postgres, Valkey |
| `compose.microservices.yaml` | Unraid | GPU worker |
| `compose.remote-ml.yaml` | Unraid | Remote machine learning |
| `smb.conf` | Pi | Samba share definition (applied by hand, see below) |
| `hwaccel.*.yml` | Unraid | NVENC / CUDA extension files |

## Why SMB is involved

Every Immich worker needs read/write access to the same media directory. The
media lives on the Pi at `/srv/docker/immich/library`, so the Unraid worker
reaches it over SMB and mounts it as a CIFS Docker volume at `/data`.

The server also exposes Postgres and Valkey on the LAN for the worker:

- `2284` → Valkey (container port 6379)
- `2285` → Postgres (container port 5432)

Traffic runs the other way too: `compose.remote-ml.yaml` exposes the CUDA
machine-learning container on Unraid at `3003`, which the server is pointed at
via its **Machine Learning** settings in the Immich admin UI.

## Part 1 — export the share from the Pi

`smb.conf` in this directory is the share definition. It is **not** deployed by
Komodo; append it to the Pi's `/etc/samba/smb.conf` by hand.

```bash
sudo apt update && sudo apt install -y samba

# Append the share definition from this repo.
sudo tee -a /etc/samba/smb.conf < /path/to/repo/docker/immich/smb.conf

# Create the SMB user. This must be an existing Unix user, and the password
# must match the SMB_PASSWORD stored in 1Password.
sudo smbpasswd -a YOUR_USER

sudo systemctl restart smbd
```

Confirm the share is exported:

```bash
smbclient -L //localhost -U YOUR_USER
```

You should see `upload_location_share` in the list.

### Why `force user = root`

The Immich server container writes into `/srv/docker/immich/library` as root, so
files land root-owned `0755`. Without `force user = root` the authenticating SMB
user can *read* those files but not *write* them, and the worker fails at
startup with `EACCES` on `/data/encoded-video/.immich`.

`writeable = yes` alone is not enough — it grants permission at the Samba layer
while the underlying Unix ownership still applies. Setting `uid=0,gid=0` on the
client mount does not help either; those options only relabel ownership for
display, and the SMB server still enforces permissions as the authenticated
user. It has to be fixed on the Pi.

## Part 2 — the worker on Unraid

The CIFS volume is defined at the bottom of `compose.microservices.yaml`. Two
things about it are easy to get wrong:

**`device` is the share name, not a filesystem path.** It must be
`//PI_HOST/upload_location_share` — matching the `[upload_location_share]`
header in `smb.conf`, not the `path =` underneath it.

**`/data` mounts the named volume, not `${UPLOAD_LOCATION}`.** Upstream's
compose file says "do not edit" on that line, and it is edited here on purpose.
`UPLOAD_LOCATION` describes a path on the *server* host; on Unraid there is no
local copy of the media, so interpolating it would bind-mount an empty local
directory and the worker would fail with `ENOENT` on the `.immich` marker files.

The healthcheck is disabled because a `microservices`-only worker does not serve
the API, so the image's default healthcheck would always fail.

## Verifying

Test the mount on its own before starting Immich — it separates a share problem
from an Immich problem:

```bash
docker volume create --driver local \
  --opt type=cifs \
  --opt o="username=YOUR_USER,password=YOUR_PASSWORD,uid=0,gid=0,vers=3.0" \
  --opt device="//PI_HOST/upload_location_share" cifstest

# Read: should list thumbs, upload, backups, library, profile, encoded-video.
docker run --rm -v cifstest:/data alpine ls -la /data

# Write: should print WRITE OK for all six.
docker run --rm -v cifstest:/data alpine sh -c '
  for d in thumbs upload backups library profile encoded-video; do
    if touch /data/$d/.writetest 2>/dev/null; then
      rm -f /data/$d/.writetest; echo "  $d: WRITE OK"
    else echo "  $d: DENIED"; fi
  done'

docker volume rm -f cifstest
```

A healthy worker logs `Successfully verified system mount folder checks` and
then continues to `Bootstrapping metadata service`.

## Gotchas

**Docker caches named volume definitions.** Editing `driver_opts` in the compose
file does nothing to a volume that already exists — the old, broken definition
is reused silently. After changing the CIFS options you must remove it first:

```bash
docker compose -f compose.microservices.yaml down
docker volume rm immich_upload_location_share
docker compose -f compose.microservices.yaml up -d
```

**`UPLOAD_LOCATION` is not read by the container.** It is a Compose-only
variable used for the volume mount. The path inside the container comes from
`IMMICH_MEDIA_LOCATION`, which defaults to `/data`. See the
[environment variables docs](https://docs.immich.app/install/environment-variables).

**A null value in `environment:` does not unset a variable.** `KEY:` with no
value resolves from the shell environment *and* the project `.env`, so a
variable defined in `.env` is passed through regardless. Use `KEY: ""` to blank
one.

**`env_file:` does not feed `${...}` interpolation.** Only the project `.env`
and the shell environment do. Setting a variable under `environment:` cannot
affect a `${...}` used in a `volumes:` entry — interpolation happens when the
YAML is parsed, long before the container environment is built.

**Transcoding I/O crosses the network.** The GPU work happens on Unraid, but
every source read and encoded write goes over SMB to the Pi. If throughput
disappoints, look here before the NVENC settings.

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
| `ml-vram-probe.py` | any | Measures ML memory cost, derives the tuning values below |

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

## Sizing machine learning for a host

`compose.remote-ml.yaml` sets `MACHINE_LEARNING_REQUEST_THREADS` and
`MACHINE_LEARNING_MAX_BATCH_SIZE__FACIAL_RECOGNITION` because the upstream
defaults exhaust a 12 GB card (see Gotchas). Those two numbers are host
specific. `ml-vram-probe.py` measures them rather than guessing:

```bash
docker exec -i -e RESERVE_MIB=4096 immich-machine-learning python - < ml-vram-probe.py
```

It runs each measurement in a forked child, because onnxruntime's arena only
grows and two phases sharing a process would read each other's high-water mark.
`RESERVE_MIB` is the only input you have to think about: how much of the device
to leave for everything else on it.

Peak memory is well described by:

```
peak = fixed + REQUEST_THREADS x MAX_BATCH_SIZE x per_face
```

On the Unraid 3080 (12 GB) the probe measures `fixed` at 508 MiB and `per_face`
at **18.5 MiB**, linear from batch 32 upward. Both are properties of the
*model*, not the machine — the same ONNX graph and the same activations run
anywhere — so on another NVIDIA host you can expect roughly the same figures
and only the budget changes. A CPU-only host is the same arithmetic against
RAM, which the probe falls back to measuring when there is no GPU.

That makes sizing a division, not a search: pick the reserve, and
`threads x batch <= (total - reserve - fixed) / per_face`.

### Spend the budget on batch, not threads

The probe also times concurrency, and the answer is emphatic:

| threads | sec/req | speedup |
| ---: | ---: | ---: |
| 1 | 0.014 | 1.00x |
| 2 | 0.011 | 1.24x |
| 4 | 0.010 | 1.34x |
| 8 | 0.010 | 1.34x |
| 16 | 0.010 | 1.33x |

Throughput saturates at 4 threads — the GPU serializes the compute regardless —
while memory keeps climbing linearly. The upstream default is `os.cpu_count()`,
which is 20 here: sixteen threads' worth of VRAM for **no** throughput.
`REQUEST_THREADS` should be the saturation point and nothing more.

Batch size is a *cap*, not a preallocation, so it only binds on photos with
many faces and costs nothing on ordinary ones. There is no reward for spending
the whole budget — pick the reserve pessimistically.

### Per-host values

`compose.remote-ml.yaml` reads both from the environment, so one compose file
serves every ML host. The defaults are the 3080's values; a host that differs
overrides them in its **Komodo stack environment** — not in `compose.env`,
which does not feed `${...}` interpolation (see Gotchas).

| Host | Device | `ML_REQUEST_THREADS` | `ML_FACE_BATCH` | Basis |
| --- | --- | ---: | ---: | --- |
| Unraid | RTX 3080, 12 GB | 4 | 16 | Measured. Shares the card with Ollama and NVENC, so the reserve is large. |
| *(second GPU host)* | RTX 5080, 16 GB | 4 | *run the probe* | Not yet measured — see the Blackwell caveat below. |

Threads is 4 on both: saturation is a property of the GPU serializing the
compute, not of how much memory it has. A bigger card buys batch, not threads.

For the 5080 the arithmetic predicts a comfortable `ML_FACE_BATCH` of 64 —
`508 + 4 x 64 x 18.5 = 5236 MiB` of 16384 — but that assumes `per_face` holds
at 18.5 MiB on Blackwell, which is exactly the assumption to check rather than
inherit. Run the probe with a `RESERVE_MIB` that reflects what else lives on
that card.

### Blackwell (RTX 50-series) is not a given on this image

The `-cuda` image links its CUDA execution provider against **CUDA 12.2**
(`libcudart.so.12.2.140`, built Aug 2023) with cuDNN 9 and onnxruntime 1.26.
CUDA 12.2 predates Blackwell; consumer `sm_120` needs CUDA 12.8 or newer. The
driver is not the constraint — Unraid's is new enough — the userspace libraries
baked into the image are.

So on the 5080 the CUDA provider may fail to initialise, and Immich's provider
list falls back to `CPUExecutionProvider` **silently**. The symptom is not an
error; it is machine learning that works and is inexplicably slow. Confirm
which provider actually got used before tuning anything:

```bash
docker exec immich-machine-learning python -c \
  "from immich_ml.models.facial_recognition.recognition import FaceRecognizer; \
   m = FaceRecognizer('buffalo_l'); m.load(); \
   print('providers in use:', m.session.session.get_providers())"
```

If that reports only `CPUExecutionProvider`, the tuning values change meaning
entirely — the budget is `MemAvailable` rather than VRAM. The probe checks the
same thing itself and switches to measuring RAM, so trust its `device:` line
over the presence of a GPU in the box.

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

**Machine learning defaults assume a CPU box, not a 12 GB GPU.** On CUDA the
facial-recognition batch size defaults to *unlimited* and the inference thread
pool defaults to `os.cpu_count()` (20 on Unraid), so a facial-recognition sweep
runs 20 concurrent, unbounded batches and exhausts VRAM. It shows up as
onnxruntime errors on `Conv` nodes, failing on allocations far smaller than the
free VRAM would suggest:

```
[E:onnxruntime:, sequential_executor.cc:615 ExecuteKernel] Non-zero status code
returned while running Conv node. Name:'Conv_0' ... BFCArena::AllocateRawInternal
... Failed to allocate memory for requested buffer of size 75520
```

`MACHINE_LEARNING_MAX_BATCH_SIZE__FACIAL_RECOGNITION` and
`MACHINE_LEARNING_REQUEST_THREADS` in `compose.remote-ml.yaml` bound both; see
[Sizing machine learning for a host](#sizing-machine-learning-for-a-host) for
how those values are derived. The errors are per-asset: the job fails and the
asset is retried, so a burst that stops on its own has still left assets
unprocessed — re-run **Face Detection → Missing** afterwards.

**Transcoding I/O crosses the network.** The GPU work happens on Unraid, but
every source read and encoded write goes over SMB to the Pi. If throughput
disappoints, look here before the NVENC settings.

"""Measure what Immich's ML container actually costs on this host, and derive
safe values for MACHINE_LEARNING_REQUEST_THREADS and
MACHINE_LEARNING_MAX_BATCH_SIZE__FACIAL_RECOGNITION.

Run it against a live ML container -- it needs nothing installed on the host:

    docker exec -i immich-machine-learning python - < ml-vram-probe.py

Tunables (pass with `docker exec -e`):
    RESERVE_MIB   memory to leave for everything else sharing the device --
                  other containers (Ollama), NVENC transcoding, and the CLIP
                  and OCR models that stay resident alongside. Default 4096.
    MODEL         facial recognition model name. Default buffalo_l.

On a host with no NVIDIA GPU it measures process RSS against MemAvailable
instead: same arithmetic, different budget.

Each phase runs in its own forked child. onnxruntime's BFC arena only ever
grows, so two phases in one process would read each other's high-water mark
instead of their own. The parent deliberately never touches CUDA before
forking -- a CUDA context does not survive fork().
"""

import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

RESERVE = int(os.environ.get("RESERVE_MIB", 4096))
MODEL = os.environ.get("MODEL", "buffalo_l")
PROBE_BATCH = 16
BATCHES = (1, 2, 4, 8, 16, 32, 64, 128, 256)
THREADS = (1, 2, 4, 8, 16)


def _gpu():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [int(x) for x in out.decode().strip().splitlines()[0].split(",")]


def _meminfo(key):
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith(key):
                return int(line.split()[1]) // 1024


def _rss():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024


HAS_SMI = _gpu() is not None
# Resolved after phase_detect(): a GPU being present is not the same as
# onnxruntime using it. If the CUDA EP fails to initialise -- an image built
# against a CUDA too old for the card, say -- Immich falls back to CPU
# silently, and then the budget is RAM, not VRAM.
GPU = False
used = _rss
TOTAL = 0


def phase_detect():
    """Which execution provider actually got the model? Presence of a GPU is
    not the answer -- only this is."""
    from immich_ml.models.facial_recognition.recognition import FaceRecognizer

    model = FaceRecognizer(MODEL)
    model.load()
    return {"providers": list(model.session.session.get_providers())}


def _setup():
    """Load the model and return (measure_fn, make_face, fixed_cost)."""
    import numpy as np

    from immich_ml.models.facial_recognition.recognition import FaceRecognizer

    start = used()
    model = FaceRecognizer(MODEL)
    model.load()

    def face():
        return np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)

    model.model.get_feat([face()])
    return model, face, used() - start


def phase_batch():
    """Marginal memory per face. The arena's high-water mark after each batch
    is the space that batch demanded, so sweep upward and read off the slope."""
    model, face, fixed = _setup()
    base = used()
    rows, per_face = [], None
    for b in BATCHES:
        if used() > TOTAL * 0.85:
            break
        try:
            model.model.get_feat([face() for _ in range(b)])
        except Exception as e:
            rows.append((b, None, None, type(e).__name__))
            break
        over = used() - base
        rows.append((b, used(), over, None))
        if b >= 32:  # small batches are dominated by fixed overhead
            per_face = over / b
    return {"fixed": fixed, "rows": rows, "per_face": per_face}


def phase_threads():
    """Does concurrency buy throughput? The GPU serializes the compute, so
    past a few threads this goes flat while memory keeps climbing."""
    model, face, fixed = _setup()
    rows, first = [], None
    for n in THREADS:
        if used() > TOTAL * 0.85:
            break
        work = [[face() for _ in range(PROBE_BATCH)] for _ in range(n * 4)]
        with ThreadPoolExecutor(max_workers=n) as ex:
            list(ex.map(model.model.get_feat, work))  # warm the pool
            t0 = time.time()
            list(ex.map(model.model.get_feat, work))
            per_req = (time.time() - t0) / len(work)
        first = first or per_req
        rows.append((n, per_req, first / per_req))
    return {"rows": rows}


def run_isolated(fn):
    """Run fn in a forked child so it gets a private CUDA context and arena."""
    path = tempfile.mktemp(suffix=".json")
    if os.fork() == 0:
        try:
            with open(path, "w") as f:
                json.dump(fn(), f)
        finally:
            os._exit(0)
    os.wait()
    with open(path) as f:
        result = json.load(f)
    os.unlink(path)
    return result


providers = run_isolated(phase_detect)["providers"]
GPU = HAS_SMI and "CUDAExecutionProvider" in providers
used = (lambda: _gpu()[0]) if GPU else _rss
TOTAL = _gpu()[1] if GPU else _meminfo("MemAvailable:")

print(f"providers       : {', '.join(providers)}")
print(f"device          : {'CUDA' if GPU else 'CPU'}")
if HAS_SMI and not GPU:
    print("  !! a GPU is present but onnxruntime is not using it -- measuring RAM.")
    print("  !! check the image's CUDA version against this card before tuning.")
print(f"total {'VRAM' if GPU else 'RAM':<10}: {TOTAL} MiB")
print(f"used by others  : {used()} MiB")

thr = run_isolated(phase_threads)
bat = run_isolated(phase_batch)
fixed, per_face = bat["fixed"], bat["per_face"]
print(f"fixed cost      : {fixed} MiB  (context + weights, paid once per process)\n")

print(f"Throughput vs concurrency (batch={PROBE_BATCH}):")
print(f"  {'threads':>7} {'sec/req':>8} {'speedup':>8}")
for n, per_req, speedup in thr["rows"]:
    print(f"  {n:>7} {per_req:>8.3f} {speedup:>7.2f}x")

print("\nCost per face:")
print(f"  {'batch':>6} {'peak':>8} {'over fixed':>11} {'MiB/face':>9}")
for b, peak, over, err in bat["rows"]:
    if err:
        print(f"  {b:>6}  FAILED: {err} -- device limit reached")
    else:
        print(f"  {b:>6} {peak:>8} {over:>11} {over / b:>9.2f}")

# The useful thread count is the smallest one within 5% of peak throughput --
# anything past it is memory spent for no speed.
peak_speedup = max(s for _, _, s in thr["rows"])
best_threads = next(n for n, _, s in thr["rows"] if s >= 0.95 * peak_speedup)

budget = TOTAL - RESERVE - fixed
print(f"\n{'-' * 62}")
print(f"budget          : {TOTAL} total - {RESERVE} reserved - {fixed} fixed = {budget} MiB")
if per_face and budget > 0:
    print(f"per face        : {per_face:.1f} MiB")
    print(f"concurrency pays: up to {best_threads} thread(s) ({peak_speedup:.2f}x); past that it is flat")
    batch = min(max(1, int(budget / per_face) // best_threads), 64)
    print(f"\n  MACHINE_LEARNING_REQUEST_THREADS: \"{best_threads}\"")
    print(f"  MACHINE_LEARNING_MAX_BATCH_SIZE__FACIAL_RECOGNITION: \"{batch}\"")
    print(f"\n  worst case = {fixed} + {best_threads} x {batch} x {per_face:.1f}"
          f" = {fixed + best_threads * batch * per_face:.0f} MiB of {TOTAL} MiB")
else:
    print("no headroom -- lower RESERVE_MIB, or this host cannot run ML alongside its other work")

# Development setup

## Isolation policy

The project must not install Python packages into the system interpreter or install Harbor as a
global tool. Use `scripts/uv-local` for every Python operation. The wrapper keeps the managed
Python runtime, package cache, and virtual environment under ignored repository paths:

```text
.local/uv/python/
.local/uv/cache/
.local/uv/bin/
.local/mini-swe-agent/
.venv/
```

Frontend packages live in `frontend/node_modules/`; the npm cache lives in
`.local/npm/cache/`. Docker images and containers are deferred until the live Harbor integration
spike and require a separate resource check.

## Required local configuration

Copy `.env.example` to `.env` and set these values locally:

```text
HY3_BASE_URL
HY3_MODEL
HY3_API_KEY
```

Do not paste credentials into source files, commands that may be logged, screenshots, or issue
reports. The health endpoint checks only whether values exist and never calls the model.

## Python environment

```bash
./scripts/uv-local python install 3.12
./scripts/uv-local sync --all-groups
./scripts/uv-local run pytest
./scripts/uv-local run ruff check .
```

After configuring `.env`, run the explicit, single-request Hy3 compatibility check:

```bash
./scripts/check-hy3
```

The command reports only response metadata and whether content was received. It never prints the
credential or sends a request implicitly from the health endpoint.

Run the API with:

```bash
./scripts/uv-local run hy3-workbench
```

## Frontend environment

The repository pins Node 24 LTS in `.node-version`. With `fnm`:

```bash
fnm install
fnm use
cd frontend
npm install
npm run test
npm run build
```

Run the Vite development server with `npm run dev`. Requests below `/api` are proxied to the
FastAPI server at `http://127.0.0.1:8000` unless `VITE_API_PROXY_TARGET` is changed.

## Docker gate

Do not create or pull benchmark images during the offline evaluator slice. Before live Harbor or
SWE-bench work, verify all of the following:

- Docker Desktop is running.
- Docker has at least 8 CPUs and approximately 16 GB RAM allocated.
- At least 120 GB is available to Docker for a small evaluation slice.
- One selected SWE-bench Verified task passes an oracle/environment check.
- On Apple Silicon, the selected task works under `linux/amd64` emulation before any wider run.

## Existing DGX Spark option

The existing DGX Spark is the preferred remote host before paying for cloud compute. A read-only
preflight on 2026-08-28 found:

```text
Architecture: ARM64 (aarch64), NVIDIA GB10
CPU: 20 cores
Memory: approximately 119 GiB usable, approximately 50 GiB available during the check
Root disk: 3.7 TiB total, approximately 2.9 TiB available
Docker: 28.3.3 with NVIDIA runtime support
Python: 3.12.3
Registry access: PyPI, npm, GitHub, Hugging Face, and Docker Hub reachable
```

This is more than sufficient for the FastAPI application, React build, SQLite state, evaluator,
analytics, and remote development. The GB10 GPU is not required when Hy3 is accessed through its
hosted API, but it remains available for separate local-model experiments.

Important constraints:

- The host is ARM64 and `qemu-x86_64` binfmt emulation is not currently registered. Do not assume
  the published x86-64 SWE-bench images will run.
- `uv`, Node, and npm are not currently installed. Add them only through an approved isolated
  setup; do not modify system Python packages.
- The Docker daemon already serves other workloads. During the check it had 11 active containers
  and roughly 70 GB of images, so this project must use separate names/paths and concurrency 1.
- Validate one selected task under x86 emulation or with a task-specific ARM64 build before moving
  any full benchmark work to the machine.

Use SSH port forwarding for the UI and keep ports 8000/5173 bound to localhost. Network latency is
acceptable for batch evaluation; it mainly affects interactive page loading and shell round trips.

## Google Cloud fallback

Do not keep a benchmark VM running continuously. The offline evaluator, API, frontend, fixtures,
and Hy3 handshake run on the local Mac or DGX Spark. Create cloud compute only if both ARM64 hosts
fail the selected SWE-bench container smoke test or are prohibitively slow.

No GPU is required when Hy3 is reached through a hosted API. Prefer native x86-64 compute so the
SWE-bench images do not need Apple Silicon emulation.

### Recommended short-lived benchmark VM

```text
Provisioning: Spot VM; create only for the benchmark spike
Machine: n2-standard-8 (8 vCPU, 32 GB RAM, x86-64)
Image: Ubuntu 24.04 LTS x86-64
Boot disk: 200 GB pd-balanced, expandable
Concurrency: 1 Harbor/SWE-bench task
Network: SSH through IAP or a restricted source IP
Application ports: bind 8000/5173 to localhost and use an SSH tunnel
GPU: none
```

Spot capacity can be reclaimed, so persist the job configuration and completed artifacts after
each task. Stop compute immediately after the spike and delete the disk after exporting required
artifacts; stopped VMs do not incur compute charges, but attached persistent disks continue to
incur storage charges.

### Lower-cost smoke-test option

```text
Provisioning: Spot VM
Machine: e2-standard-4 (4 vCPU, 16 GB RAM, x86-64)
Boot disk: 150-200 GB pd-balanced
Concurrency: 1
```

This smaller machine is below the preferred 8-vCPU benchmark configuration. Use it only to test
one selected task, expect slower builds, and move to the short-lived 8-vCPU option only if the
task runs out of memory or times out. Do not reserve or commit to a monthly VM before measuring
one real task.

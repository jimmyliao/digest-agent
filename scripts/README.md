# `scripts/` — what each script does

Almost every script here has a one-line `make` wrapper (see top-level
`Makefile` or run `make` for the curated entry-points table). This
catalog exists for when you need to know **what's available** or
**what something does** before invoking it.

> Convention: each script reads env vars in this order:
> **shell env (highest)** → `.env.deploy` (gitignored, prod) → `.env` (dev).
> Empty placeholder values are skipped so a partially-filled `.env` doesn't
> mask a valid `.env.deploy` setting.

---

## 🎓 Workshop / fresh-machine setup

| Script | `make` target | Purpose |
|---|---|---|
| [`onboard-cloudshell.sh`](./onboard-cloudshell.sh) | `make onboard-cloudshell` | Install bun + uv on a fresh Cloud Shell / dev box, run `bun install` + `uv sync`, scaffold `apps/web/.env.local`. Idempotent. |
| [`smoke-cloudshell.sh`](./smoke-cloudshell.sh) | `make smoke-cloudshell` | After onboarding, boot `apps/web` dev server, curl `/api/health` + `/api/articles`, report PASS/FAIL. Auto-cleans dev server on exit. |
| — | `make workshop-verify` | Composite: onboard + smoke. **Recommended one-shot for Cloud Shell.** |

## 🧪 Local test

| Script | `make` target | Purpose |
|---|---|---|
| [`test-local-e2e.sh`](./test-local-e2e.sh) | `make test-local-e2e` | End-to-end local smoke. No LLM key, no GCS, no Cloud Run. Verifies vitest + dev server query params + agent HTTP/SQLite toggle. |
| [`test-local-api-real.sh`](./test-local-api-real.sh) | `make test-local-api-real` | Real-API smoke against an already-running dev server. Hits every `/api/*` with real RSS + real LLM calls. **Needs `GEMINI_API_KEY`.** |

## ☁️ Deploy (Cloud Run + GEAP)

| Script | `make` target | Purpose |
|---|---|---|
| [`setup-data-bucket.sh`](./setup-data-bucket.sh) | `make setup-data-bucket` | One-time: create the GCS bucket Litestream replicates `/data/digest.db` to. Idempotent. |
| [`deploy-web-to-cloud-run.sh`](./deploy-web-to-cloud-run.sh) | `make deploy-web` | Deploy `apps/web/` (Next.js + Litestream) to Cloud Run via Cloud Build. Reads `LITESTREAM_GCS_BUCKET`, `BASIC_AUTH_*`, `GEAP_RESOURCE_NAME` from env. |
| [`deploy-to-agent-engine.sh`](./deploy-to-agent-engine.sh) | `make deploy-agent-engine` | Deploy `agents/stock/` ADK agents to Vertex AI Agent Engine (GEAP). Pre-flight checks IAM, billing, ADC quota project, bucket region. |

## 🔧 GCP one-time setup

| Script | `make` target | Purpose |
|---|---|---|
| [`setup-billing-alert.sh`](./setup-billing-alert.sh) | `make setup-billing-alert` | Monthly billing budget alert (default $5 USD, notifies at 50/90/100%). |

## 🤖 Agent Engine ops

| Script | `make` target | Purpose |
|---|---|---|
| [`invoke-agent-engine.sh`](./invoke-agent-engine.sh) | `make invoke-agent-engine` | Invoke the latest deployed Reasoning Engine with a default or custom message; useful for post-deploy smoke. |
| [`list-agent-engines.sh`](./list-agent-engines.sh) | `make list-agent-engines` | List Reasoning Engines in your GCP project, filter by display name, optional JSON output. |

## 🪝 Gemini CLI hooks demo (Phase 9)

These are **workshop demo scripts** — referenced from `~/.gemini/settings.json`
hooks, not invoked directly. Kept here so the demo is self-contained when a
student clones the repo.

| Script | Hook | Purpose |
|---|---|---|
| [`deny-env-edit.sh`](./deny-env-edit.sh) | `BeforeTool` | Blocks any tool call whose args contain `.env`. Demo: "Hooks 守住敏感檔案不被 AI 改動". |
| [`sys-load.sh`](./sys-load.sh) | `BeforeModel` | Injects current top-5 CPU processes into the model's context metadata. Demo: "Hooks 把外部觀測注入 Agent". |

---

## When you don't see a `make` target

- `setup-billing-alert` accepts an `AMOUNT` env: `AMOUNT=10 make setup-billing-alert`
- `list-agent-engines` runs the script directly: `./scripts/list-agent-engines.sh --filter digest-agent`

## Adding a new script

1. Add `set -euo pipefail` at the top
2. Document **Usage** + **Required env** + **What it does** in the header comment
3. Add a `make`-target wrapper in the top-level `Makefile` (one line: `@bash scripts/your-new.sh`)
4. Update this catalog in the appropriate section
5. If it's a workshop entry point, also add a row to `make help`

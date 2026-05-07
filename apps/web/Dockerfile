# syntax=docker/dockerfile:1.6
# ─────────────────────────────────────────────────────────────────────────────
# digest-agent Next.js UI — Litestream-backed Cloud Run image.
#
# Build from the REPO ROOT so that infra/ is reachable in the build context:
#   docker build -f apps/web/Dockerfile -t digest-web .
#
# Stages:
#   builder  → install deps, run `next build` (output: 'standalone')
#   runner   → minimal node:20-alpine + litestream binary + standalone server
#
# Notes:
#   • next.config.ts sets `output: 'standalone'`, so .next/standalone contains
#     a self-contained server bundle (server.js + minimal node_modules).
#   • better-sqlite3 / bun:sqlite are in serverExternalPackages, so they stay
#     as runtime require()s. The standalone tracer copies the native addon
#     into the standalone bundle automatically.
#   • Litestream restore happens inside /entrypoint.sh on container start;
#     the final command is `litestream replicate -exec "node server.js"`.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ────────────────────────────────────────────────────────
# Uses Bun because repo root has bun.lock + workspace:* protocol in
# apps/web/package.json (npm does not resolve workspace: when running
# from a sub-package). Build artifacts are still plain Node-compatible
# (Next.js standalone output → node server.js).
FROM oven/bun:1.3-alpine AS builder
WORKDIR /app

# System deps for building better-sqlite3 (native addon)
RUN apk add --no-cache python3 make g++ libc6-compat

# Copy workspace root manifest + lockfile + per-package manifests so
# `bun install` resolves the @leapcore/iface workspace dep correctly.
COPY package.json bun.lock ./
COPY apps/web/package.json ./apps/web/
COPY packages/leapcore-iface/package.json ./packages/leapcore-iface/
COPY packages/digest-adk/package.json ./packages/digest-adk/

RUN bun install --frozen-lockfile

# Bring in the rest of the source tree
COPY apps/web ./apps/web
COPY packages ./packages

WORKDIR /app/apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN bun run build

# ── Stage 2: runner ─────────────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Install Litestream + required tooling
RUN apk add --no-cache curl ca-certificates tar \
 && curl -fsSL -o /tmp/litestream.tgz \
        https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz \
 && tar -xzf /tmp/litestream.tgz -C /usr/local/bin litestream \
 && chmod +x /usr/local/bin/litestream \
 && rm /tmp/litestream.tgz \
 && litestream version

# Litestream config + entrypoint (from repo root context)
COPY infra/litestream.yml /etc/litestream.yml
COPY infra/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Persistent data dir; Litestream restore + SQLite both target /data/digest.db
RUN mkdir -p /data

# Standalone server bundle + static assets
# (next.config.ts: output: 'standalone' — produces .next/standalone)
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

# In a monorepo build, the standalone server entry is at apps/web/server.js.
# entrypoint.sh runs `node server.js` from this WORKDIR.
WORKDIR /app/apps/web

EXPOSE 3000
ENTRYPOINT ["/entrypoint.sh"]

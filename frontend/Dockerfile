# syntax=docker/dockerfile:1.6
# Dockerfile pour le frontend Vite + React tangent
# Mode dev (hot reload). Pour la prod on ferait un multi-stage avec Caddy
# servant le build statique (cf TODO Batch 4 cleanup).

FROM node:20-alpine

WORKDIR /app

# Install deps en premier (cache layer Docker) + BuildKit cache pour npm
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --include=dev --prefer-offline

# Copie le reste du code source
COPY . .

EXPOSE 5173

# Dev hot-reload requires write access to /app/node_modules anonymous volume,
# and Vite re-optimize fails as non-root. Production frontend will be a
# static build served via Caddy (TODO #20 in SESSION_RECAP), so this dev
# Dockerfile staying as root is acceptable.
# nosemgrep: dockerfile.security.missing-user.missing-user
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

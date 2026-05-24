# Dockerfile pour le frontend Vite + React tangent
# Mode dev (hot reload). Pour la prod on ferait un multi-stage avec nginx.

FROM node:20-alpine

WORKDIR /app

# Install deps en premier (cache layer)
COPY package.json package-lock.json* ./
RUN npm ci --include=dev

# Copie le reste du code source
COPY . .

EXPOSE 5173

# nosemgrep: dockerfile.security.missing-user.missing-user
# Dev hot-reload requires write access to /app/node_modules anonymous volume,
# and Vite re-optimize fails as non-root. Production frontend will be a
# static build served via Caddy (TODO #20 in SESSION_RECAP), so this dev
# Dockerfile staying as root is acceptable.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

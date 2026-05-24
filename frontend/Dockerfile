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

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

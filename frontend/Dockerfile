# Syntax=docker/dockerfile:1
# Socle frontend ChainScope (issue #18) : build Vite puis service nginx.
# Le navigateur ne parle qu'au backend (spec §2) : nginx reverse-proxy /api/.

FROM node:22-alpine AS build
WORKDIR /app
# Cache des dépendances : on copie d'abord le lockfile.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

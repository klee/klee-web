# Build stage: compile the SPA to static assets in dist/.
FROM node:24-bookworm-slim AS build
WORKDIR /app

# Deps-only layer: cached until the lockfile changes. .npmrc carries the
# legacy-peer-deps line the clean install needs.
COPY package.json package-lock.json .npmrc ./
RUN npm ci

# Source in, tsc -b && vite build emits dist/.
COPY . .
RUN npm run build

# Serve stage: nginx serves dist/ and reverse-proxies /api. Multi-stage
# discards node and node_modules, so the image is just nginx plus static files.
FROM nginx:1.31-alpine

# Self-signed cert for local TLS. openssl is only needed at build, so it is
# dropped after. In production a real CA cert (e.g. Let's Encrypt) replaces
# these two files with no config change.
RUN apk add --no-cache --virtual .certgen openssl \
    && mkdir -p /etc/nginx/certs \
    && openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
       -keyout /etc/nginx/certs/selfsigned.key \
       -out /etc/nginx/certs/selfsigned.crt \
       -subj "/CN=localhost" \
       -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    && apk del .certgen

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

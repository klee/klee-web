# Build stage: compile the SPA to static assets in dist/.
FROM node:20-bookworm-slim AS build
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
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

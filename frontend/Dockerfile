# ══════════════════════════════════════════════════════════════════════════════
#  QueryMind Frontend — Dockerfile
#  Multi-stage build: Node (build) → Nginx (serve)
#
#  Stage 1: node:20-alpine  — builds the React/Vite production bundle
#  Stage 2: nginx:1.27-alpine — serves static files + reverse proxies the API
# ══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Cache dependency layer separately from source code
COPY package*.json ./
RUN npm ci --prefer-offline

# Build-time environment variable (Nginx handles routing so base URL is /)
ARG VITE_API_URL=/
ENV VITE_API_URL=$VITE_API_URL

# Copy source and build production bundle
COPY . .
RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx page but preserve the 50x Gateway Timeout page
RUN mv /usr/share/nginx/html/50x.html /tmp/50x.html && \
    rm -rf /usr/share/nginx/html/* && \
    mv /tmp/50x.html /usr/share/nginx/html/50x.html

# Custom nginx config (reverse proxy + SPA routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy Vite build output
COPY --from=build /app/dist /usr/share/nginx/html

# Healthcheck
HEALTHCHECK --interval=20s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

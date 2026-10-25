# Vite dev server for `make dev` (docker compose). Source is bind-mounted over /app;
# node_modules stays in the container because the host's may hold Windows binaries.
FROM node:24.22.1-bookworm-slim

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

EXPOSE 8080
CMD ["npm", "run", "dev"]

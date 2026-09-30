# Dashboard: Next.js app on port 3001, proxying /api to the backend service.
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# NEXT_PUBLIC_* values are inlined at build time; the defaults are correct
# because the browser reaches the dashboard (and its /api proxy) on 3001.
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
EXPOSE 3001
# Bind all interfaces inside the container; docker-compose publishes the port on 127.0.0.1 only.
CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3001"]

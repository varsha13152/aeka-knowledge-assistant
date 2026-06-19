# ─── Stage 1: Dependencies ──────────────────────────────────────────────────
FROM node:20-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ─── Stage 2: Build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ─── Stage 3: Production ────────────────────────────────────────────────────
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=build --chown=nextjs:nodejs /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["node", "server.js"]

# ─── Stage 4: Development ───────────────────────────────────────────────────
FROM dependencies AS development

WORKDIR /app

RUN addgroup --system --gid 1001 devgroup && \
    adduser --system --uid 1001 --ingroup devgroup devuser

COPY --chown=devuser:devgroup . .
USER devuser

EXPOSE 3000

CMD ["npm", "run", "dev"]

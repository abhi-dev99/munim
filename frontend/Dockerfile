FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json package-lock.json ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next.js telemetry is disabled
ENV NEXT_TELEMETRY_DISABLED=1

# Inject the backend API URL at build time so the frontend knows where to fetch
ARG NEXT_PUBLIC_API_URL=https://munim-backend-1051889700424.us-central1.run.app
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# AWS Ship-It build: /aws-pipeline reads real Step Functions pipeline output
# straight off DynamoDB (see src/app/aws-pipeline/page.js) via its own
# token-gated Lambda, entirely separate from the OTP/dashboard flow above.
ARG NEXT_PUBLIC_AWS_READ_API_URL=""
ENV NEXT_PUBLIC_AWS_READ_API_URL=$NEXT_PUBLIC_AWS_READ_API_URL
ARG NEXT_PUBLIC_AWS_READ_TOKEN=""
ENV NEXT_PUBLIC_AWS_READ_TOKEN=$NEXT_PUBLIC_AWS_READ_TOKEN

# The real CA dashboard (login, Money Meter, Action Queue, My Practice, etc.)
# on AWS Lambda + DynamoDB, replacing Cloud Run for those surfaces only.
# Left empty, every dashboard/login page falls back to NEXT_PUBLIC_API_URL
# above -- that fallback IS the rollback path, no code change needed, just
# rebuild with this arg unset (or redeploy the munim-frontend:pre-aws-dashboard
# ECR tag directly, which needs no rebuild at all).
ARG NEXT_PUBLIC_AWS_DASHBOARD_API_URL=""
ENV NEXT_PUBLIC_AWS_DASHBOARD_API_URL=$NEXT_PUBLIC_AWS_DASHBOARD_API_URL

# The admin-router secret is deliberately NOT built in. Anything named
# NEXT_PUBLIC_* is inlined into the client JavaScript by Next.js, so passing
# the admin key here published it: it shipped in the served bundle and was
# downloadable by anyone who opened the site, while gating DELETE
# /api/v1/admin/invoices/{id}. utils/api.js now reads it from sessionStorage
# after an operator types it in. Do not reintroduce a NEXT_PUBLIC_ secret.

RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]

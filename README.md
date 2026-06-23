# K-DenceAI

## Overview
K-DenceAI delivers superior AI-generated content with brand-guideline adherence, a sustainable freemium model, and competitive multi-platform features. Users can generate, refine, analyze, and repurpose content across LinkedIn, X/Twitter, Instagram, Email, and TikTok, with clear upgrade paths via PayPal or Stripe subscriptions.

## Architecture
- Frontend: React + Vite
- Backend: Supabase Auth/Postgres + RLS
- Edge: Supabase Edge Functions (Deno)
- Deployment: Google Cloud Run (Cloud Build)
- Security: [GCloud Infrastructure & Security Architecture](file:///d:/My%20Experiments/K-DenceAI/k-dence-clean/k-denceai/GCLOUD_SECURITY_PIPELINE.md)
- Payments: PayPal Subscriptions + Stripe Checkout

## Core Features
- AI Content Generation
  - Generate long-form posts with strong hooks, data points, examples, CTAs
  - Nudge posts: concise prompts for quick engagement
  - Improve: advanced rewriting with structure, stats, steps, CTA, hashtags
  - Ideas: niche-based content ideation
  - Analyze: sentiment, topics, tone, reading level, style notes
- Brand Voice & Guidelines
  - Brand voice and “banned topics” configurable in Settings → Brand
  - Preferences applied to generate, nudge, improve, analyze, repurpose flows
- Multi-Platform Repurposing
  - LinkedIn, X/Twitter, Instagram, Email, TikTok scripts
  - Platform-tuned prompts with voice adherence and topic bans
- Scheduling & Publishing
  - ContentCalendar for draft/scheduled/published states
  - Social publishing via LinkedIn/X adapters (Instagram/TikTok stubs in progress)
- Sustainable Freemium Model
  - Free tier monthly generation quota
  - Premium gating at Edge Function + DB layers
  - Realtime tier updates driven by payment webhooks
- Subscriptions & Billing
  - PayPal subscription modal with webhook activation
  - Stripe checkout button (card payments) with webhook activation
  - Payment history stored per user and displayed in Settings

## Data Model (Selected)
- trends_raw: source, term, niche, value, meta, collected_at
- trends_processed: term, niche, volume, velocity, recency, score, sources, updated_at
- user_usage: drafts_generated_count, last_reset_date (quota tracking)
- payment_history: provider, event_id, subscription_id, status, amount, currency, created_at
- repurposed_content (premium insert policy)
- processed_webhooks: event_id idempotency guard

## Edge Functions
- ai-writer (supabase/functions/ai-writer/index.ts)
  - Actions: generate, nudge, improve, ideas, analyze
  - Routes model selection; enforces auth, tier gating, brand voice/bans
- repurpose (supabase/functions/repurpose/index.ts)
  - Parallel repurposing via TransformationEngine
  - Enforces auth, premium gate; applies voice/bans
- social-api (supabase/functions/social-api/index.ts)
  - Actions: get_auth_url, exchange_token, post_content, init_quota, dispatch_scheduled
  - Providers: linkedin, twitter, instagram (posting implemented for linkedin/twitter; 501 for instagram/tiktok)
- paypal-webhook (supabase/functions/paypal-webhook/index.ts)
  - Verifies webhook; activates/cancels subscriptions; logs payment history; ensures idempotency
- stripe-checkout (supabase/functions/stripe-checkout/index.ts)
  - Creates Stripe Checkout sessions for card payments
- stripe-webhook (supabase/functions/stripe-webhook/index.ts)
  - Activates/cancels subscriptions; logs payment history; ensures idempotency
- trends-engine (supabase/functions/trends-engine/index.ts)
  - Actions: fetch, process, list for trends ingestion/processing
- newsletter-send, market-signals (present for newsletter and signal workflows)

## Environment & Secrets
- Supabase: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
- AI: GEMINI_API_KEY
- CORS: ALLOWED_ORIGINS
- Test bypass: TEST_PAID_EMAILS
- Social: TWITTER_BEARER, GOOGLE_TRENDS_GEO
- Scheduling: SCHEDULE_DISPATCH_SECRET (for dispatch_scheduled)
- PayPal: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_WEBHOOK_ID, PAYPAL_MODE=live|sandbox
- Stripe: STRIPE_SECRET_KEY, STRIPE_PRICE_ID_PRO, STRIPE_WEBHOOK_SECRET, CHECKOUT_SUCCESS_URL, CHECKOUT_CANCEL_URL
- Client (.env/.env.production)
  - VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
  - VITE_PAYPAL_CLIENT_ID
  - VITE_PAYPAL_PLAN_ID_PRO, VITE_PAYPAL_PLAN_ID_PRO_MONTHLY, VITE_PAYPAL_PLAN_ID_PRO_ANNUAL
  - VITE_STRIPE_PUBLISHABLE_KEY
  - VITE_GOOGLE_API_KEY

## Setup
1. Apply SQL in Supabase
   - supabase/trends_schema.sql
   - supabase/tiered_access_schema.sql
   - supabase/migrations/20260212120000_add_payment_history.sql
2. Configure Edge Runtime secrets (see Environment & Secrets)
3. Deploy Edge Functions
   - supabase functions deploy ai-writer
   - supabase functions deploy repurpose
   - supabase functions deploy social-api
   - supabase functions deploy paypal-webhook
   - supabase functions deploy stripe-checkout
   - supabase functions deploy stripe-webhook
4. Deploy Web App
   - Cloud Build: gcloud builds submit --config cloudbuild.yaml
   - Cloud Run service: web-app

## API Summary
- POST /functions/v1/ai-writer
  - { action: 'generate'|'nudge'|'improve'|'ideas'|'analyze', ... }
- POST /functions/v1/repurpose
  - { content, platforms, title }
- POST /functions/v1/social-api
  - { action, provider, ... } with Authorization
- POST /functions/v1/paypal-webhook
  - PayPal webhook target (JSON payload + verification headers)
- POST /functions/v1/stripe-checkout
  - { action: 'create_session' } → { url }
- POST /functions/v1/stripe-webhook
  - Stripe webhook target (secured by secret)
- POST /functions/v1/trends-engine
  - { action: 'fetch'|'process'|'list', ... }

## Frontend Integration
- SettingsView: manages brand voice, subscribers, payment history, connections
- SubscriptionModal: PayPal subscribe + Stripe “Pay with Card” button
- ContentEditorPage: generation, improvement, analysis, auto-save, scheduling
- RepurposingPanel: multi-platform repurposing outputs
- PricingPage: Free vs Pro tiers; upgrade flow
- PulsePanel: market signals

## Security & Policies
- RLS on repurposed_content restricts inserts to pro/premium users
- processed_webhooks table prevents duplicate webhook processing
- Quotas enforced via user_usage and Edge gate checks

## Run
- Build: npm run build
- Serve: npm run start (http://localhost:8080)
- Deploy: gcloud builds submit --config cloudbuild.yaml

## Notes
- Instagram/TikTok posting is scaffolded; repurposing outputs are available while posting flows are implemented
- Configure ALLOWED_ORIGINS for Edge Functions CORS

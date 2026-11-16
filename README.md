# AdServiceBot — Telegram-first edition (Railway)

This build removes the web admin dashboard. Customers and staff use Telegram; the admin panel is shown as a Reply Keyboard button only to the Owner and staff accounts with an assigned role.

## Runtime
- Railway runs the Deno Telegram webhook from `telegram-webhook.ts` using the Dockerfile.
- Supabase remains the database and authentication/data layer.
- No React/Vite website or web admin dashboard is included.
- Telegram updates are received by the Railway webhook; database access uses the Supabase service-role key stored only in Railway Variables.

## Apply database migrations
Run these SQL files in order in the Supabase SQL Editor:
1. `supabase__migrations__001_initial.sql`
2. `supabase__migrations__002_complete_workflows.sql`
3. `supabase__migrations__003_telegram_admin_panel.sql`

If migrations 001/002 were already applied, do not rerun them blindly on production. Review and apply only the missing additive statements from 003. Take a database backup first.

## Railway Variables
Set these in Railway → Service → Variables:
- `TELEGRAM_BOT_TOKEN`: bot token from BotFather
- `TELEGRAM_WEBHOOK_SECRET`: random secret (use letters, digits, underscore, hyphen; 20+ chars)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service-role key (secret)
- `OWNER_TELEGRAM_ID=8292338949`
- `DEVELOPER_TELEGRAM_ID=858897695`
- `TELEGRAM_PRIVATE_GROUP_ID`: optional private operations group ID
- `PREMIUM_EMOJI_DECORATION_ID`: optional single decoration emoji ID

Never put secrets in source code, GitHub, or Telegram messages.

## Configure Telegram webhook
After Railway deploys, copy the public HTTPS domain, then call this URL from a trusted terminal (replace values locally; do not paste the token into chat):

`https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<RAILWAY_DOMAIN>/&secret_token=<TELEGRAM_WEBHOOK_SECRET>`

Telegram's secret token must match `TELEGRAM_WEBHOOK_SECRET`. The root GET endpoint is a health check; Telegram sends POST updates to the same root URL.

## Admin panel
- Owner ID is configured as `8292338949` and has full access.
- Developer ID is `858897695` and receives technical-only access.
- Other admins must have a row in `public.profiles` with their `telegram_id`, `role='admin'`, and explicit `permissions` JSON keys.
- Example permission keys: `orders_read`, `orders_update`, `payments_review`, `support_read`, `packages_manage`, `wallets_manage`, `settings_read`, `technical_read`.
- Customers do not see the admin button.
- Order status changes, payment decisions, and support replies are handled inside Telegram and recorded in audit/history tables where available.

## Current Telegram admin features
- Overview counts (Owner)
- Browse recent orders and change order status (permission-gated)
- Review pending crypto payment submissions (permission-gated)
- Browse open support tickets and reply/close tickets (permission-gated)
- View configured packages and crypto payment methods (permission-gated)
- View staff roles/permissions (Owner only)
- Technical status view for Developer

Package and wallet editing/creation workflows are not included in this build yet; the current panel lists their configuration. Do not treat those sections as full CRUD management.

## Important
This is a source implementation, not proof of a successful production deployment. Test `/start`, customer order creation, TXID submission, Owner panel visibility, admin permission restrictions, payment review and notifications in a staging bot/database before production use.

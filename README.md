# BoostlyAds Bot v11

## Railway deployment
- Deploy the flat ZIP contents at repository root.
- Set `TELEGRAM_BOT_TOKEN` as a Railway environment variable.
- Keep the existing Railway persistent volume mounted at `/data`.
- The live database `/data/adservice.sqlite3` is preserved and takes precedence over the bundled backup. The bundled `boostly-backup.sqlite3` is copied only when no live database exists.
- Do not delete or recreate the `/data` volume when deploying an update.

## v11 fixes
- Mandatory join check now lets `/start` and the `عضو شدم، بررسی عضویت` callback reach their handlers. This fixes the middleware deadlock that previously blocked the membership-check button.
- A bonus deep-link payload is temporarily retained in the user's FSM state while they join; after successful membership verification the bot claims that exact bonus. Users cannot claim the bonus before membership is confirmed.
- First startup of v11 enables mandatory join when the database has at least one active mandatory channel, even if an earlier v10 migration marker exists.
- `/Notif` handler is registered before the catch-all message handler. In the management group, reply to a message and send `/Notif`; the bot copies that message to registered users and reports successful/failed counts.
- `/Notif` is available to active staff and uses Telegram `copyMessage`, preserving supported text and media.
- Withdrawal approval sends the user a payment confirmation and does not debit the reserved amount a second time.

## Mandatory channel setup
- The bot must be an administrator in each mandatory channel so Telegram can reliably return membership status.
- Confirm that the channel is active in the bot's mandatory-channel list and that its invite URL is correct.

## Environment
- `TELEGRAM_BOT_TOKEN`
- SQLite database path: `/data/adservice.sqlite3`
- Long polling; no webhook and no Supabase required.

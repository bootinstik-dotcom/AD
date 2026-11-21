# BoostlyAds Bot v14

## Railway deployment
- Upload the flat ZIP contents at the repository root.
- Set `TELEGRAM_BOT_TOKEN` as a Railway environment variable (never commit the token).
- Keep the existing Railway persistent volume mounted at `/data`.
- The live database is `/data/adservice.sqlite3`; the application preserves it and applies schema migrations in place.
- This source archive does **not** contain a user database. Do not commit SQLite databases, user records, wallet balances, or transaction history to GitHub (including private repositories where avoidable).
- For an existing Railway volume, leave it in place; no database upload is needed. For a new deployment, transfer the backup securely into the Railway volume as `/data/adservice.sqlite3` before starting the bot.
- Do not delete or recreate the `/data` volume when deploying an update.

## v14 changes
- Fixed `/Notif`: its handler is now registered before the generic management-group reply handler, which previously could consume the command first.
- `/Notif` supports `/Notif` and `/Notif@BotUsername`, must be sent in the management group as a reply to the message to broadcast, and accepts owner/developer IDs as authorized even if a staff-role row is missing.
- Existing v13 wallet minimum settings and free dice game/cooldown settings are retained.
- Dice rewards remain internal points, not TON and not withdrawable. The game is free and does not deduct wallet funds.

## Environment
- `TELEGRAM_BOT_TOKEN`
- SQLite database path: `/data/adservice.sqlite3`
- Long polling; no webhook and no Supabase required.

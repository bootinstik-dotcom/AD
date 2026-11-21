# BoostlyAds Bot v15

## Railway deployment
- Upload the flat ZIP contents at the repository root.
- Set `TELEGRAM_BOT_TOKEN` as a Railway environment variable (never commit the token).
- Keep the existing Railway persistent volume mounted at `/data`.
- The live database is `/data/adservice.sqlite3`; the application preserves it and applies schema migrations in place.
- This source archive does **not** contain a user database. Do not commit SQLite databases, user records, wallet balances, or transaction history to GitHub (including private repositories where avoidable).
- For an existing Railway volume, leave it in place; no database upload is needed. For a new deployment, transfer your backup securely into the Railway volume as `/data/adservice.sqlite3` before starting the bot. The backup is intentionally not required in the Docker build context.
- Do not delete or recreate the `/data` volume when deploying an update.

## v15 changes
- Added a points-redemption workflow. Users can submit all their current game points for review; points are reserved immediately to prevent duplicate requests.
- Pending requests appear in the admin panel and management group. Authorized managers can approve or reject them; rejection restores the reserved points.
- After approval, the bot prompts the manager to enter the free advertising/service reward details, records fulfillment, and notifies the user.
- The new `point_redemptions` table and index are created additively at startup. Existing users, wallet balances, orders, ledger entries, and game history are preserved.
- Points earned from the random dice game are not converted into withdrawable TON. The redemption workflow awards free services only.

## v14 changes
- Fixed `/Notif`: its handler is now registered before the generic management-group reply handler, which previously could consume the command first.
- `/Notif` supports `/Notif` and `/Notif@BotUsername`, must be sent in the management group as a reply to the message to broadcast, and accepts owner/developer IDs as authorized even if a staff-role row is missing.
- Existing v13 wallet minimum settings and free dice game/cooldown settings are retained.
- Dice rewards remain internal points, not TON and not withdrawable. The game is free and does not deduct wallet funds.

## Environment
- `TELEGRAM_BOT_TOKEN`
- SQLite database path: `/data/adservice.sqlite3`
- Long polling; no webhook and no Supabase required.

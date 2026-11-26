# BoostlyAds Bot v16

## Railway deployment
- Upload the flat ZIP contents at the repository root.
- Set `TELEGRAM_BOT_TOKEN` as a Railway environment variable (never commit the token).
- Keep the existing Railway persistent volume mounted at `/data`.
- The live database is `/data/adservice.sqlite3`; the application preserves it and applies schema migrations in place.
- This archive includes the SQLite backup supplied for this version as `boostly-backup.sqlite3`. It is used only when `/data/adservice.sqlite3` does not already exist.
- For an existing Railway volume, leave it in place; the live database is never overwritten by the bundled backup. For a new/empty volume, the bundled backup is copied into `/data/adservice.sqlite3` on first startup.
- This archive contains private user and transaction data because it was explicitly requested as a backup-based build. Keep the ZIP private and do not publish it in a public repository.
- Do not delete or recreate the `/data` volume when deploying an update.

## v16 changes
- Fixed mandatory-join membership checks by resolving each configured channel through Telegram before checking the user's membership.
- Added a per-bonus winner list, including user identity, amount, and claim time, in the bonus management list.
- Added automatic database backup files every hour to the reporting group and every 24 hours to the management group.
- Enforced the minimum 50-point redemption threshold in the database transaction; users with fewer than 50 points cannot submit a request, and rejection still restores reserved points.
- Bundled the supplied verified SQLite backup as the seed database. Existing Railway volume data always takes precedence and is never overwritten.

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

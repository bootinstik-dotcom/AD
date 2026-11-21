# BoostlyAds Bot v12

## Railway deployment
- Upload the flat ZIP contents at the repository root.
- Set `TELEGRAM_BOT_TOKEN` as a Railway environment variable.
- Keep the existing Railway persistent volume mounted at `/data`.
- The live database `/data/adservice.sqlite3` is preserved and takes precedence over the bundled `boostly-backup.sqlite3`.
- The bundled backup is copied only when no live database exists. Existing Railway data is never overwritten.
- Do not delete or recreate the `/data` volume when deploying an update.

## v12 additions
- Configurable minimum TON deposit and withdrawal amounts in the admin bot settings.
- Free Telegram dice game with configurable non-cash, non-transferable, non-withdrawable points for each dice result.
- Winner announcements in the reporting group and game statistics for administrators.
- Includes the latest user-provided SQLite backup as a first-deployment seed.

## Environment
- `TELEGRAM_BOT_TOKEN`
- SQLite database path: `/data/adservice.sqlite3`
- Long polling; no webhook and no Supabase required.

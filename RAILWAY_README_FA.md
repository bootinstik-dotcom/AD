# راه‌اندازی AdServiceBot در Railway — نسخه تلگرام‌محور

در این نسخه پنل وب حذف شده است. مشتریان و مدیران همه کارها را از داخل تلگرام انجام می‌دهند. دکمه «⚙️ پنل مدیریت» فقط برای Owner و افرادی که نقش و مجوز مدیریتی دارند نمایش داده می‌شود.

## فایل‌ها و اجرا
Railway با Dockerfile سرویس Deno را از `telegram-webhook.ts` اجرا می‌کند. دیتابیس همچنان Supabase است. هیچ داشبورد React یا پنل وبی در این نسخه وجود ندارد.

## مراحل نصب
۱. فایل‌ها را به یک Repository در GitHub منتقل و Repository را به Railway متصل کنید.
۲. در Supabase، ابتدا Migrationهای 001 و 002 را فقط اگر قبلاً اجرا نشده‌اند اجرا کنید؛ سپس Migration شماره 003 را اجرا کنید. پیش از هر تغییر از دیتابیس Backup بگیرید.
۳. در Railway → Variables مقادیر زیر را ثبت کنید:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OWNER_TELEGRAM_ID=8292338949`
- `DEVELOPER_TELEGRAM_ID=858897695`
- `TELEGRAM_PRIVATE_GROUP_ID` (اختیاری)
- `PREMIUM_EMOJI_DECORATION_ID` (اختیاری)
۴. بعد از Deploy دامنه HTTPS سرویس Railway را بردارید و Webhook تلگرام را تنظیم کنید:

`https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<RAILWAY_DOMAIN>/&secret_token=<WEBHOOK_SECRET>`

مقادیر واقعی Token و Secret را فقط در Railway وارد کنید؛ آن‌ها را در چت یا سورس قرار ندهید.

## پنل مدیریت تلگرام
- Owner: شناسه `8292338949` و دسترسی کامل.
- Developer: شناسه `858897695` و دسترسی فنی محدود.
- سایر مدیران باید در `public.profiles` با `telegram_id`، نقش `admin` و مجوزهای مشخص ثبت شده باشند.
- مجوزها شامل `orders_read`، `orders_update`، `payments_review`، `support_read`، `packages_manage`، `wallets_manage`، `settings_read` و `technical_read` هستند.

امکانات فعلی: مشاهده سفارش‌ها، تغییر وضعیت سفارش، بررسی پرداخت‌ها، مشاهده و پاسخ به تیکت‌ها، مشاهده پکیج‌ها و روش‌های پرداخت، گزارش کلی Owner و وضعیت فنی Developer.

**محدودیت فعلی:** افزودن و ویرایش پکیج و کیف پول از داخل تلگرام هنوز پیاده‌سازی نشده و این بخش‌ها فعلاً فقط نمایش اطلاعات دارند.

import asyncio, os, tempfile, html
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import db


import re

PREMIUM_EMOJI_IDS = [
    ("🪙", "6008043563542126167"),
    ("💪", "5823442050934116771"),
    ("😃", "5821179994738529951"),
    ("📌", "5821293029687825738"),
    ("😫", "5823513922916848442"),
    ("💎", "6006061397480315684"),
    ("📤", "6008070651900861977"),
    ("➡️", "4987769821769761823"),
    ("❌", "4987991119959688124"),
    ("✅", "4990068230568543199"),
    ("‼️", "4990298741463319592"),
    ("🟢", "5823310053704208766"),
    ("🔥", "5823551254772586211"),
    ("🗣", "5823539211684287784"),
    ("🤑", "5823698361697440934"),
    ("💪", "5823338018236272848"),
    ("😎", "5823392736119624565"),
    ("😍", "5823310053704208766"),
    ("🔥", "5823678145286382134"),
    ("🔥", "5823551254772586211"),
    ("🗣", "5823513922916848442"),
    ("😫", "5821293029687825738"),
    ("📌", "5823338018236272848"),
    ("😎", "5823698361697440934"),
    ("💪", "5823678145286382134"),
    ("🔥", "5823392736119624565"),
    ("😍", "5823513922916848442"),
    ("😫", "4990298741463319592"),
    ("🟢", "4990075566372685240"),
    ("🟡", "4990203285815166156"),
    ("⏳", "4987991119959688124"),
    ("✅", "4990533856563036953"),
    ("🟢", "4988012783774729470"),
    ("✅", "4987775237723522533"),
    ("❤️", "4990519099055408115"),
    ("❌", "6005892472121597245"),
    ("🏦", "6006061397480315684"),
    ("💎", "6008043563542126167"),
    ("🪙", "6032888897082497570"),
    ("💎", "6030704695759084316"),
    ("🪙", "6032952342339395168"),
    ("🤑", "6032818979309888002"),
    ("💱", "6032888897082497570"),
    ("🟢", "6008124493610885197"),
    ("🔗", "6007923248623263109"),
    ("📤", "6007814255238192870"),
    ("🗓", "6005892472121597245"),
    ("💎", "4990038389135770641"),
    ("⭐️", "4990036306076632013"),
    ("💪", "5823338018236272848"),
    ("😎", "4990262169816794201"),
    ("⬇️", "4990226723451699964"),
    ("😫", "5823678145286382134"),
    ("🔥", "5821179994738529951"),
    ("😃", "5823442050934116771"),
    ("💪", "5823430231184118947"),
    ("💪", "5823612273372959359"),
    ("😈", "5823310053704208766"),
    ("🔥", "5823551254772586211"),
    ("🗣", "5823513922916848442"),
    ("😫", "5823548789461357623"),
    ("👋", "6006061397480315684"),
    ("🔗", "6007923248623263109"),
    ("📥", "4990533856563036953"),
    ("🟢", "5823442050934116771"),
    ("💪", "5823338018236272848"),
    ("😎", "5823310053704208766"),
    ("🔥", "5821179994738529951"),
    ("😍", "5823551254772586211"),
    ("📌", "5823349206626079506"),
    ("😎", "5823513922916848442"),
    ("😱", "5823310053704208766"),
    ("😫", "6006061397480315684"),
    ("💎", "6007944173703929511"),
    ("💎", "6032666885927999842"),
    ("🪙", "6032888897082497570"),
    ("🔴", "4990182601252668309"),
    ("🔴", "4990163033381667840"),
    ("🔴", "4987817392827532337"),
    ("🔴", "4987837622123496389"),
    ("🔴", "4988267960666686268"),
    ("⏳", "4990412201614378299"),
    ("😫", "4990298741463319592"),
    ("🔵", "5823392736119624565")
]
PREMIUM_EMOJI_BY_GLYPH = {'🪙': '6008043563542126167', '💪': '5823442050934116771', '😃': '5821179994738529951', '📌': '5821293029687825738', '😫': '5823513922916848442', '💎': '6006061397480315684', '📤': '6008070651900861977', '➡️': '4987769821769761823', '❌': '4987991119959688124', '✅': '4990068230568543199', '‼️': '4990298741463319592', '🟢': '5823310053704208766', '🔥': '5823551254772586211', '🗣': '5823539211684287784', '🤑': '5823698361697440934', '😎': '5823392736119624565', '😍': '5823310053704208766', '🟡': '4990203285815166156', '⏳': '4987991119959688124', '❤️': '4990519099055408115', '🏦': '6006061397480315684', '💱': '6032888897082497570', '🔗': '6007923248623263109', '🗓': '6005892472121597245', '⭐️': '4990036306076632013', '⬇️': '4990226723451699964', '😈': '5823310053704208766', '👋': '6006061397480315684', '📥': '4990533856563036953', '😱': '5823310053704208766', '🔴': '4990182601252668309', '🔵': '5823392736119624565'}

def premium_text(value):
    """Convert known emoji glyphs in message text to Telegram custom-emoji HTML."""
    text = str(value)
    for glyph, emoji_id in PREMIUM_EMOJI_BY_GLYPH.items():
        text = text.replace(glyph, f'<tg-emoji emoji-id="{emoji_id}">{glyph}</tg-emoji>')
    return text


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
OWNER_ID = 8292338949
DEVELOPER_ID = 858897695
BOT_NAME = "Boostly Ads"

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

bot=Bot(TOKEN)
# All normal text replies use Telegram Premium custom-emoji entities where IDs were supplied.
_original_send_message = bot.send_message
async def _premium_send_message(chat_id, text, *args, **kwargs):
    if isinstance(text, str):
        text = premium_text(text)
        kwargs.setdefault("parse_mode", "HTML")
    return await _original_send_message(chat_id, text, *args, **kwargs)
bot.send_message = _premium_send_message
dp=Dispatcher(storage=MemoryStorage())

# Telegram Bot API 9.4+: ReplyKeyboard buttons support custom emoji icons and colors.
# Keys are the old visible labels; values are (new text, custom_emoji_id, style).
BUTTON_CONFIG = {
    "📢 تبلیغات گروه": ("تبلیغات گروه", "5823310053704208766", "primary"),
    "📣 تبلیغات چنل": ("تبلیغ کانال", "5823392736119624565", "primary"),
    "📦 سفارش‌های من": ("سفارش‌های من", "4990298741463319592", "primary"),
    "👤 حساب کاربری": ("حساب کاربری", "5821179994738529951", "primary"),
    "💬 پشتیبانی": ("پشتیبانی", "5821179994738529951", "primary"),
    "📖 راهنما": ("راهنما", "5823513922916848442", "primary"),
    "⚙️ پنل مدیریت": ("پنل مدیریت", "5823338018236272848", "success"),
    "📋 سفارش‌ها": ("همه سفارش‌ها", "4990298741463319592", "primary"),
    "💳 بررسی پرداخت‌ها": ("بررسی پرداخت‌ها", "6005892472121597245", "success"),
    "📦 مدیریت پکیج‌ها": ("مدیریت خدمات", "5821179994738529951", "primary"),
    "👛 روش‌های پرداخت": ("روش‌های پرداخت", "6032818979309888002", "primary"),
    "🎫 تیکت‌های پشتیبانی": ("تیکت‌های پشتیبانی", "5821179994738529951", "primary"),
    "📊 گزارش کلی": ("گزارش کلی", "5823442050934116771", "primary"),
    "👥 مدیریت مدیران": ("مدیریت مدیران", "5823678145286382134", "primary"),
    "🏠 منوی اصلی": ("منوی اصلی", "5823442050934116771", "primary"),
    "🔙 بازگشت": ("بازگشت", "4987769821769761823", "danger"),
    "✅ ثبت سفارش": ("ثبت سفارش", "4990068230568543199", "success"),
}

def kb(rows):
    keyboard = []
    for row in rows:
        buttons = []
        for label in row:
            text, emoji_id, style = BUTTON_CONFIG.get(label, (label, None, "primary"))
            payload = {"text": text, "style": style}
            if emoji_id:
                payload["icon_custom_emoji_id"] = emoji_id
            buttons.append(KeyboardButton(**payload))
        keyboard.append(buttons)
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)

def home(uid):
    rows=[["📢 تبلیغات گروه","📣 تبلیغات چنل"],["📦 سفارش‌های من","👤 حساب کاربری"],["💬 پشتیبانی","📖 راهنما"]]
    if db.is_staff(uid): rows.append(["⚙️ پنل مدیریت"])
    return kb(rows)

def admin_kb():
    return kb([["📋 سفارش‌ها","💳 بررسی پرداخت‌ها"],["📦 مدیریت پکیج‌ها","👛 روش‌های پرداخت"],
               ["🎫 تیکت‌های پشتیبانی","📊 گزارش کلی"],["👥 مدیریت مدیران"],["🏠 منوی اصلی"]])

def esc(x): return html.escape(str(x or ""))

class Flow(StatesGroup):
    choose_product=State()
    choose_package=State()
    destination=State()
    join_target=State()
    banner=State()
    ad_text=State()
    notes=State()
    confirm=State()
    choose_payment=State()
    txid=State()
    receipt=State()
    support=State()
    add_package_product=State()
    add_package_title=State()
    add_package_desc=State()
    add_package_price=State()
    add_package_currency=State()
    add_package_duration=State()
    add_wallet_currency=State()
    add_wallet_network=State()
    add_wallet_address=State()
    add_admin_id=State()
    remove_admin_id=State()
    order_status=State()

async def notify_staff(text):
    with db.conn() as c:
        staff=c.execute("SELECT id FROM users WHERE active=1 AND role IN ('owner','admin')").fetchall()
    for row in staff:
        try: await bot.send_message(row["id"],text)
        except Exception: pass
    group_id=db.setting("management_group_id","")
    if group_id:
        try: await bot.send_message(int(group_id),text)
        except Exception: pass

async def start_order(message:Message,state:FSMContext,category_slug:str):
    with db.conn() as c:
        cat=c.execute("SELECT * FROM categories WHERE slug=? AND active=1",(category_slug,)).fetchone()
    if not cat:
        await message.answer("این دسته‌بندی فعلاً فعال نیست.",reply_markup=home(message.from_user.id)); return
    items=db.products(cat["id"])
    if not items:
        await message.answer("در حال حاضر خدمتی در این دسته فعال نیست.",reply_markup=home(message.from_user.id)); return
    await state.update_data(category_id=cat["id"],category_title=cat["title"])
    await state.set_state(Flow.choose_product)
    await message.answer("خدمت موردنظر را انتخاب کنید:",reply_markup=kb([[p["title"]] for p in items]+[["🔙 بازگشت","🏠 منوی اصلی"]]))

@dp.message(CommandStart())
async def start(m:Message,state:FSMContext):
    db.upsert_user(m.from_user); await state.clear()
    await m.answer(f"به <b>{BOT_NAME}</b> خوش آمدید.\nاز منوی زیر خدمات موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=home(m.from_user.id))

@dp.message(Command("id"))
async def get_id(m:Message):
    await m.answer(f"شناسه عددی شما: <code>{m.from_user.id}</code>",parse_mode="HTML")

@dp.message(F.text=="منوی اصلی")
async def main_menu(m:Message,state:FSMContext):
    await state.clear(); db.upsert_user(m.from_user)
    await m.answer("منوی اصلی:",reply_markup=home(m.from_user.id))

@dp.message(F.text=="تبلیغات گروه")
async def group_ads(m:Message,state:FSMContext): await start_order(m,state,"group_ads")

@dp.message(F.text=="تبلیغ کانال")
async def channel_ads(m:Message,state:FSMContext): await start_order(m,state,"channel_ads")

@dp.message(Flow.choose_product)
async def product_chosen(m:Message,state:FSMContext):
    d=await state.get_data()
    with db.conn() as c:
        p=c.execute("SELECT * FROM products WHERE category_id=? AND title=? AND active=1",(d["category_id"],m.text)).fetchone()
    if not p:
        await m.answer("لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید."); return
    packs=db.packages(p["id"])
    if not packs:
        await m.answer("برای این خدمت هنوز پکیجی تعریف نشده است. لطفاً بعداً مراجعه کنید.",reply_markup=home(m.from_user.id)); await state.clear(); return
    await state.update_data(product_id=p["id"],product_title=p["title"],product_kind=p["kind"])
    await state.set_state(Flow.choose_package)
    await m.answer("پکیج موردنظر را انتخاب کنید:",reply_markup=kb([[f'{x["title"]} | {x["price"]} {x["currency"]}'] for x in packs]+[["🔙 بازگشت","🏠 منوی اصلی"]]))

@dp.message(Flow.choose_package)
async def package_chosen(m:Message,state:FSMContext):
    d=await state.get_data()
    with db.conn() as c: packs=c.execute("SELECT * FROM packages WHERE product_id=? AND active=1",(d["product_id"],)).fetchall()
    chosen=None
    for p in packs:
        if m.text==f'{p["title"]} | {p["price"]} {p["currency"]}': chosen=p; break
    if not chosen:
        await m.answer("لطفاً یکی از پکیج‌ها را انتخاب کنید."); return
    await state.update_data(package_id=chosen["id"],package_title=chosen["title"],price=chosen["price"],currency=chosen["currency"],duration=chosen["duration"],description=chosen["description"],details={})
    await state.set_state(Flow.destination)
    await m.answer("لینک یا آیدی مقصد تبلیغ را ارسال کنید:")

@dp.message(Flow.destination)
async def destination(m:Message,state:FSMContext):
    await state.update_data(destination=m.text or "")
    d=await state.get_data()
    if d["product_kind"]=="force_join":
        await state.set_state(Flow.join_target)
        await m.answer("لینک یا آیدی کانال/گروهی که کاربران باید ابتدا عضو آن شوند را ارسال کنید:")
    else:
        await state.set_state(Flow.banner)
        await m.answer("تصویر بنر را ارسال کنید (یا اگر فعلاً فایل ندارید، «ندارم» بنویسید):")

@dp.message(Flow.join_target)
async def join_target(m:Message,state:FSMContext):
    await state.update_data(join_target=m.text or "")
    await state.set_state(Flow.ad_text)
    await m.answer("متن تبلیغ یا توضیحات انتشار را ارسال کنید:")

@dp.message(Flow.banner)
async def banner(m:Message,state:FSMContext):
    fid=m.photo[-1].file_id if m.photo else (m.document.file_id if m.document else "")
    if not fid and (m.text or "").strip()!="ندارم":
        await m.answer("لطفاً تصویر را ارسال کنید یا «ندارم» بنویسید."); return
    await state.update_data(banner_file_id=fid)
    await state.set_state(Flow.ad_text)
    await m.answer("متن تبلیغ یا توضیحات انتشار را ارسال کنید:")

@dp.message(Flow.ad_text)
async def ad_text(m:Message,state:FSMContext):
    await state.update_data(ad_text=m.text or m.caption or "")
    await state.set_state(Flow.notes)
    await m.answer("توضیحات تکمیلی (در صورت نداشتن، «ندارم» بنویسید):")

@dp.message(Flow.notes)
async def notes(m:Message,state:FSMContext):
    await state.update_data(notes=m.text or "")
    d=await state.get_data()
    details={k:d.get(k,"") for k in ("destination","join_target","banner_file_id","ad_text","notes")}
    summary=(f"<b>پیش‌نمایش سفارش</b>\nخدمت: {esc(d['product_title'])}\nپکیج: {esc(d['package_title'])}\n"
             f"مبلغ: <b>{esc(d['price'])} {esc(d['currency'])}</b>\nمقصد: {esc(details['destination'])}\n"
             f"کانال عضویت: {esc(details.get('join_target','-'))}\nمتن تبلیغ: {esc(details['ad_text'])}\n"
             f"توضیحات: {esc(details['notes'])}\n\nسفارش را ثبت می‌کنید؟")
    await state.update_data(details=details)
    await state.set_state(Flow.confirm)
    await m.answer(summary,parse_mode="HTML",reply_markup=kb([["✅ ثبت سفارش"],["🔙 بازگشت","🏠 منوی اصلی"]]))

@dp.message(Flow.confirm,F.text=="ثبت سفارش")
async def confirm_order(m:Message,state:FSMContext):
    d=await state.get_data()
    product={"id":d["product_id"],"title":d["product_title"]}
    pack={"id":d["package_id"],"title":d["package_title"],"price":d["price"],"currency":d["currency"]}
    order=db.create_order(m.from_user.id,product,pack,d["details"])
    db.audit(m.from_user.id,"order_created","order",order["order_no"])
    await notify_staff(f"🆕 سفارش جدید\nشماره: <code>{order['order_no']}</code>\nکاربر: <code>{m.from_user.id}</code>\nمبلغ: {order['price']} {order['currency']}")
    methods=db.methods()
    if not methods:
        await state.clear()
        await m.answer(f"سفارش <b>{order['order_no']}</b> ثبت شد؛ اما هنوز روش پرداختی فعال نشده است. پشتیبانی به‌زودی راهنمایی می‌کند.",parse_mode="HTML",reply_markup=home(m.from_user.id)); return
    await state.update_data(order_no=order["order_no"],order_id=order["id"])
    await state.set_state(Flow.choose_payment)
    await m.answer(f"سفارش <b>{order['order_no']}</b> ثبت شد.\nروش پرداخت را انتخاب کنید:",parse_mode="HTML",
                   reply_markup=kb([[f'{x["currency"]} | {x["network"]}'] for x in methods]+[["🏠 منوی اصلی"]]))

@dp.message(Flow.choose_payment)
async def payment_chosen(m:Message,state:FSMContext):
    methods=db.methods(); chosen=None
    for x in methods:
        if m.text==f'{x["currency"]} | {x["network"]}': chosen=x; break
    if not chosen: await m.answer("یکی از روش‌های پرداخت را انتخاب کنید."); return
    d=await state.get_data()
    await state.update_data(method_id=chosen["id"])
    await state.set_state(Flow.txid)
    await m.answer(f"ارز: {esc(chosen['currency'])}\nشبکه: {esc(chosen['network'])}\nآدرس کیف پول:\n<code>{esc(chosen['address'])}</code>\n\nمبلغ سفارش: {esc(d['price'])} {esc(d['currency'])}\nپس از پرداخت، TXID را ارسال کنید.",parse_mode="HTML")

@dp.message(Flow.txid)
async def txid(m:Message,state:FSMContext):
    if not m.text or len(m.text.strip())<8:
        await m.answer("لطفاً TXID معتبر را به‌صورت متنی ارسال کنید."); return
    await state.update_data(txid=m.text.strip())
    await state.set_state(Flow.receipt)
    await m.answer("اگر رسید پرداخت دارید، تصویر آن را ارسال کنید؛ در غیر این صورت «ندارم» بنویسید.")

@dp.message(Flow.receipt)
async def receipt(m:Message,state:FSMContext):
    d=await state.get_data()
    fid=m.photo[-1].file_id if m.photo else ""
    if not fid and (m.text or "").strip()!="ندارم":
        await m.answer("تصویر رسید یا عبارت «ندارم» را ارسال کنید."); return
    db.order_payment(d["order_id"],d["method_id"],d["txid"],fid)
    db.audit(m.from_user.id,"payment_submitted","order",d["order_no"])
    await notify_staff(f"💳 پرداخت برای بررسی\nسفارش: <code>{d['order_no']}</code>\nکاربر: <code>{m.from_user.id}</code>\nTXID: <code>{esc(d['txid'])}</code>")
    await state.clear()
    await m.answer("اطلاعات پرداخت ثبت شد و در انتظار بررسی مدیر است. تأیید پرداخت به‌صورت دستی انجام می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="سفارش‌ها")
async def my_orders(m:Message):
    rows=db.user_orders(m.from_user.id)
    if not rows: await m.answer("هنوز سفارشی ثبت نکرده‌اید.",reply_markup=home(m.from_user.id)); return
    txt="\n\n".join([f"#{x['order_no']} | {x['product_title']}\n{x['package_title']} — {x['price']} {x['currency']}\nوضعیت: {x['status']}" for x in rows])
    await m.answer(txt,reply_markup=home(m.from_user.id))

@dp.message(F.text=="حساب کاربری")
async def profile(m:Message):
    u=db.user(m.from_user.id)
    await m.answer(f"شناسه: <code>{m.from_user.id}</code>\nنام: {esc(m.from_user.full_name)}\nنام کاربری: @{esc(m.from_user.username or '-')}\nنقش: {esc(u['role'] if u else 'customer')}",parse_mode="HTML",reply_markup=home(m.from_user.id))

@dp.message(F.text=="راهنما")
async def help_user(m:Message):
    await m.answer("۱) دسته تبلیغ را انتخاب کنید.\n۲) خدمت و پکیج را انتخاب کنید.\n۳) اطلاعات تبلیغ را وارد و سفارش را ثبت کنید.\n۴) پرداخت رمزارزی را انجام دهید و TXID را ارسال کنید.\n۵) پرداخت پس از بررسی دستی مدیر تأیید می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="پشتیبانی")
async def support_start(m:Message,state:FSMContext):
    await state.set_state(Flow.support); await m.answer("پیام خود برای پشتیبانی را ارسال کنید:")

@dp.message(Flow.support)
async def support_save(m:Message,state:FSMContext):
    tid=db.add_ticket(m.from_user.id,"درخواست پشتیبانی",m.text or m.caption or "[رسانه]")
    await notify_staff(f"🎫 تیکت جدید #{tid}\nکاربر: <code>{m.from_user.id}</code>\n{esc(m.text or m.caption or 'رسانه')}")
    await state.clear(); await m.answer(f"تیکت شماره {tid} ثبت شد.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="پنل مدیریت")
async def admin_panel(m:Message):
    if not db.is_staff(m.from_user.id): return
    await m.answer("پنل مدیریت Boostly Ads",reply_markup=admin_kb())

@dp.message(F.text=="گزارش کلی")
async def report(m:Message):
    if not db.is_staff(m.from_user.id): return
    s=db.stats()
    await m.answer(f"📊 گزارش کلی\nکاربران: {s['users']}\nسفارش‌ها: {s['orders']}\nپرداخت‌های در انتظار: {s['pending']}\nمجموع مبالغ پرداخت‌شده ثبت‌شده: {s['revenue']}",reply_markup=admin_kb())

@dp.message(F.text=="همه سفارش‌ها")
async def admin_orders(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.all_orders()
    if not rows: await m.answer("سفارشی ثبت نشده است."); return
    for x in rows[:15]:
        await m.answer(f"#{x['order_no']}\nکاربر: {x['user_id']}\n{x['product_title']} / {x['package_title']}\nمبلغ: {x['price']} {x['currency']}\nوضعیت: {x['status']}",
                       reply_markup=kb([[f"وضعیت {x['order_no']}"]]))

@dp.message(F.text=="بررسی پرداخت‌ها")
async def admin_payments(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.pending_payments()
    if not rows: await m.answer("پرداخت در انتظار بررسی وجود ندارد."); return
    for x in rows:
        await m.answer(f"پرداخت #{x['id']}\nسفارش: {x['order_no']}\nکاربر: {x['user_id']}\nمبلغ: {x['price']} {x['currency']}\nTXID: <code>{esc(x['txid'])}</code>",
            parse_mode="HTML",reply_markup=kb([[f"تأیید پرداخت {x['id']}",f"رد پرداخت {x['id']}"]]))

@dp.message(F.text.startswith("تأیید پرداخت "))
async def approve_payment(m:Message):
    if not db.is_staff(m.from_user.id): return
    try: pid=int(m.text.rsplit(" ",1)[1])
    except: return
    with db.conn() as c: p=c.execute("SELECT order_id FROM payments WHERE id=?",(pid,)).fetchone()
    if not p: await m.answer("پرداخت پیدا نشد."); return
    order=db.review_payment(pid,True,m.from_user.id)
    if not order: await m.answer("این پرداخت قبلاً بررسی شده است."); return
    db.audit(m.from_user.id,"payment_approved","payment",pid)
    await bot.send_message(order["user_id"],f"پرداخت سفارش {order['order_no']} توسط مدیر تأیید شد. سفارش در صف اجرا قرار گرفت.")
    await m.answer("پرداخت تأیید شد.")

@dp.message(F.text.startswith("رد پرداخت "))
async def reject_payment(m:Message):
    if not db.is_staff(m.from_user.id): return
    try: pid=int(m.text.rsplit(" ",1)[1])
    except: return
    with db.conn() as c: p=c.execute("SELECT order_id FROM payments WHERE id=?",(pid,)).fetchone()
    if not p: await m.answer("پرداخت پیدا نشد."); return
    order=db.review_payment(pid,False,m.from_user.id)
    if not order: await m.answer("این پرداخت قبلاً بررسی شده است."); return
    db.audit(m.from_user.id,"payment_rejected","payment",pid)
    await bot.send_message(order["user_id"],f"پرداخت سفارش {order['order_no']} رد شد. برای پیگیری با پشتیبانی تماس بگیرید.")
    await m.answer("پرداخت رد شد.")

@dp.message(F.text=="مدیریت خدمات")
async def package_admin(m:Message,state:FSMContext):
    if not db.is_owner(m.from_user.id): await m.answer("فقط مالک اجازه مدیریت پکیج‌ها را دارد."); return
    with db.conn() as c: ps=c.execute("SELECT p.id,p.title,c.title category FROM products p JOIN categories c ON c.id=p.category_id ORDER BY c.id,p.id").fetchall()
    await state.set_state(Flow.add_package_product)
    await m.answer("برای افزودن پکیج، شماره محصول را ارسال کنید:\n"+"\n".join(f"{p['id']}) {p['category']} — {p['title']}" for p in ps))

@dp.message(Flow.add_package_product)
async def pack_product(m:Message,state:FSMContext):
    if not db.is_owner(m.from_user.id): return
    try:
        pid=int(m.text)
        with db.conn() as c: p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
        if not p: raise ValueError()
    except: await m.answer("شماره محصول معتبر نیست."); return
    await state.update_data(new_product_id=pid); await state.set_state(Flow.add_package_title)
    await m.answer("عنوان پکیج را بفرستید:")

@dp.message(Flow.add_package_title)
async def pack_title(m:Message,state:FSMContext):
    await state.update_data(new_title=m.text); await state.set_state(Flow.add_package_desc); await m.answer("توضیحات پکیج را بفرستید یا «-»:")

@dp.message(Flow.add_package_desc)
async def pack_desc(m:Message,state:FSMContext):
    await state.update_data(new_desc="" if m.text=="-" else m.text); await state.set_state(Flow.add_package_price); await m.answer("قیمت را فقط به‌صورت عدد وارد کنید:")

@dp.message(Flow.add_package_price)
async def pack_price(m:Message,state:FSMContext):
    try: float(m.text.replace(",",""))
    except: await m.answer("قیمت باید عددی باشد."); return
    await state.update_data(new_price=m.text); await state.set_state(Flow.add_package_currency); await m.answer("واحد قیمت را وارد کنید؛ مثلاً USDT یا تومان:")

@dp.message(Flow.add_package_currency)
async def pack_currency(m:Message,state:FSMContext):
    await state.update_data(new_currency=m.text.upper()); await state.set_state(Flow.add_package_duration); await m.answer("مدت/شرایط پکیج را وارد کنید یا «-»:")

@dp.message(Flow.add_package_duration)
async def pack_duration(m:Message,state:FSMContext):
    d=await state.get_data()
    pid=db.add_package(d["new_product_id"],d["new_title"],d["new_desc"],d["new_price"],d["new_currency"],"" if m.text=="-" else m.text)
    db.audit(m.from_user.id,"package_created","package",pid)
    await state.clear(); await m.answer(f"پکیج با شناسه {pid} ساخته شد.",reply_markup=admin_kb())

@dp.message(F.text=="روش‌های پرداخت")
async def wallet_admin(m:Message,state:FSMContext):
    if not db.is_owner(m.from_user.id): await m.answer("فقط مالک اجازه مدیریت کیف پول‌ها را دارد."); return
    await state.set_state(Flow.add_wallet_currency); await m.answer("ارز را وارد کنید؛ مثلاً USDT:")

@dp.message(Flow.add_wallet_currency)
async def wallet_currency(m:Message,state:FSMContext):
    await state.update_data(wallet_currency=m.text.upper()); await state.set_state(Flow.add_wallet_network); await m.answer("نام شبکه را وارد کنید؛ مثلاً TRC20:")

@dp.message(Flow.add_wallet_network)
async def wallet_network(m:Message,state:FSMContext):
    await state.update_data(wallet_network=m.text); await state.set_state(Flow.add_wallet_address); await m.answer("آدرس کیف پول را ارسال کنید:")

@dp.message(Flow.add_wallet_address)
async def wallet_address(m:Message,state:FSMContext):
    d=await state.get_data(); mid=db.add_method(d["wallet_currency"],d["wallet_network"],m.text.strip())
    db.audit(m.from_user.id,"wallet_added","payment_method",mid)
    await state.clear(); await m.answer(f"روش پرداخت با شناسه {mid} اضافه شد.",reply_markup=admin_kb())

@dp.message(F.text=="تیکت‌های پشتیبانی")
async def admin_tickets(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.tickets()
    if not rows: await m.answer("تیکت بازی وجود ندارد."); return
    for t in rows:
        await m.answer(f"تیکت #{t['id']} | کاربر {t['user_id']}\n{t['subject']}")

@dp.message(F.text=="مدیریت مدیران")
async def manage_admins(m:Message,state:FSMContext):
    if not db.is_owner(m.from_user.id): await m.answer("فقط مالک."); return
    await state.set_state(Flow.add_admin_id)
    await m.answer("برای افزودن مدیر، شناسه عددی تلگرام او را ارسال کنید. برای حذف مدیر، دستور /removeadmin را بزنید.")

@dp.message(Command("removeadmin"))
async def remove_admin_start(m:Message,state:FSMContext):
    if not db.is_owner(m.from_user.id): return
    await state.set_state(Flow.remove_admin_id); await m.answer("شناسه عددی مدیر برای غیرفعال‌سازی را ارسال کنید:")

@dp.message(Flow.add_admin_id)
async def add_admin_handler(m:Message,state:FSMContext):
    if not db.is_owner(m.from_user.id): return
    try: uid=int(m.text)
    except: await m.answer("شناسه باید عددی باشد."); return
    if uid in (OWNER_ID,DEVELOPER_ID): await m.answer("این شناسه از قبل نقش ویژه دارد."); return
    db.add_admin(uid,"admin"); db.audit(m.from_user.id,"admin_added","user",uid)
    await state.clear(); await m.answer(f"مدیر {uid} اضافه شد.",reply_markup=admin_kb())

@dp.message(Flow.remove_admin_id)
async def remove_admin_handler(m:Message,state:FSMContext):
    if not db.is_owner(m.from_user.id): return
    try: uid=int(m.text)
    except: await m.answer("شناسه باید عددی باشد."); return
    db.remove_admin(uid); db.audit(m.from_user.id,"admin_removed","user",uid)
    await state.clear(); await m.answer(f"مدیر {uid} غیرفعال شد.",reply_markup=admin_kb())

@dp.message(F.text.startswith("وضعیت "))
async def status_prompt(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    order_no=m.text.replace("وضعیت ","",1).strip()
    if not db.get_order(order_no): await m.answer("سفارش پیدا نشد."); return
    await state.update_data(status_order=order_no); await state.set_state(Flow.order_status)
    await m.answer("وضعیت جدید را دقیقاً از این فهرست انتخاب کنید:\nqueued\nin_progress\ncompleted\ncancelled")

@dp.message(Flow.order_status)
async def status_change(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    allowed={"queued","in_progress","completed","cancelled"}
    if m.text not in allowed: await m.answer("وضعیت نامعتبر است."); return
    d=await state.get_data(); o=db.set_order_status(d["status_order"],m.text)
    db.audit(m.from_user.id,"order_status_changed","order",o["order_no"],{"status":m.text})
    await bot.send_message(o["user_id"],f"وضعیت سفارش {o['order_no']} تغییر کرد: {m.text}")
    await state.clear(); await m.answer("وضعیت سفارش به‌روزرسانی شد.",reply_markup=admin_kb())

@dp.message(Command("backup"))
async def backup(m:Message):
    if not db.is_owner(m.from_user.id): await m.answer("فقط مالک اجازه تهیه بکاپ دارد."); return
    path=db.backup_file()
    try: await m.answer_document(FSInputFile(path,filename="adservice-backup.sqlite3"),caption="نسخه پشتیبان دیتابیس")
    finally:
        try: os.unlink(path)
        except OSError: pass

@dp.message(Command("setgroup"))
async def set_group(m:Message):
    if not db.is_owner(m.from_user.id): return
    parts=(m.text or "").split(maxsplit=1)
    if len(parts)!=2: await m.answer("استفاده: /setgroup -100123456789"); return
    try: int(parts[1])
    except: await m.answer("شناسه گروه باید عددی باشد."); return
    db.set_setting("management_group_id",parts[1]); await m.answer("گروه گزارش‌دهی ذخیره شد.")

@dp.message()
async def fallback(m:Message):
    await m.answer("لطفاً از دکمه‌های منو استفاده کنید یا /start را بزنید.",reply_markup=home(m.from_user.id))

async def main():
    db.init_db(OWNER_ID,DEVELOPER_ID)
    await bot.delete_webhook(drop_pending_updates=False)
    print("Boostly Ads bot started with long polling")
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__":
    asyncio.run(main())

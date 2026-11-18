import asyncio, os, tempfile, html, json, logging, traceback
import aiohttp
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import db
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("boostly")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_ID = 8292338949
DEVELOPER_ID = 858897695
MANAGEMENT_GROUP_ID = -1003987452469
REQUIRED_ADMIN_ACCOUNT = "@Parsa_0102"
BOT_NAME = "Boostly Ads"
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Button icons use the custom emoji IDs supplied by the owner. ReplyKeyboard only.
ICONS = {
    "خانه": "5823442050934116771", "حساب کاربری": "5821179994738529951",
    "تنظیمات": "5821293029687825738", "راهنما": "5823513922916848442",
    "اطلاعات": "6006061397480315684", "اعلان‌ها": "6008070651900861977",
    "بازگشت": "4987769821769761823", "بستن": "4987991119959688124",
    "تأیید": "4990068230568543199", "هشدار": "4990298741463319592",
    "جستجو": "5823310053704208766", "بروزرسانی": "5823551254772586211",
    "خدمات تبلیغاتی": "5823539211684287784", "ثبت سفارش": "5823698361697440934",
    "تبلیغات": "5823338018236272848", "تبلیغ کانال": "5823392736119624565",
    "تبلیغات گروه": "5823310053704208766", "تبلیغات گیووای": "5823678145286382134",
    "سفارش‌های من": "4990298741463319592", "سفارش جدید": "4990075566372685240",
    "در انتظار پرداخت": "4990203285815166156", "در انتظار بررسی": "4987991119959688124",
    "تأیید شده": "4990533856563036953", "در حال انجام": "4988012783774729470",
    "تکمیل شده": "4987775237723522533", "لغو شده": "4990519099055408115",
    "رد شده": "6005892472121597245", "امور مالی": "6032888897082497570",
    "پرداخت": "6006061397480315684", "ارز دیجیتال": "6030704695759084316",
    "کیف پول": "6032818979309888002", "شبکه انتقال": "6008124493610885197",
    "تراکنش": "6007923248623263109", "ارسال رسید": "6007814255238192870",
    "پنل مدیریت": "5823338018236272848", "گزارشات": "5823442050934116771",
    "پشتیبان‌گیری": "5823430231184118947", "پشتیبانی": "5821179994738529951",
    "تیکت جدید": "5823551254772586211", "پیام": "5823551254772586211",
    "پیوست": "5823349206626079506", "ویژه": "5823392736119624565",
    "ثبت کانال": "4990226723451699964", "ادمین کردم": "4990226723451699964",
    "شارژ کیف پول": "6032818979309888002", "تاریخچه کیف پول": "6006061397480315684",
    "درخواست‌های کانال": "5823513922916848442", "کانال‌های تأییدشده": "5823392736119624565",
    "همه سفارش‌ها": "4990298741463319592", "بررسی پرداخت‌ها": "6005892472121597245",
    "تیکت‌های پشتیبانی": "5821179994738529951", "مدیریت خدمات": "5821179994738529951",
    "روش‌های پرداخت": "6032818979309888002", "مدیریت کاربران": "5823678145286382134",
    "مدیریت مدیران": "4990036306076632013", "افزودن ادمین": "4990226723451699964",
    "حذف ادمین": "5823513922916848442", "افزودن خدمت": "5823338018236272848",
    "افزودن پکیج": "5823698361697440934", "منوی مدیریت": "5823442050934116771",
}

BUTTON_STYLE = {
    "ثبت سفارش": "success", "ادمین کردم": "success", "تأیید": "success",
    "تأیید کانال": "success", "رد کانال": "danger", "لغو": "danger",
    "تبلیغات گروه": "primary", "تبلیغ کانال": "primary", "تبلیغات گیووای": "primary",
    "در حال انجام": "primary", "تکمیل شده": "success", "لغو شده": "danger",
}

def kb(rows):
    keyboard=[]
    for row in rows:
        buttons=[]
        for label in row:
            text=str(label)
            # Dynamic labels inherit icon from their leading semantic token.
            icon = ICONS.get(text)
            if not icon:
                for key, value in ICONS.items():
                    if text.startswith(key + " ") or text.startswith(key + " | "):
                        icon=value; break
            style=BUTTON_STYLE.get(text, "primary")
            kwargs={"text":text, "style":style}
            if icon: kwargs["icon_custom_emoji_id"]=icon
            buttons.append(KeyboardButton(**kwargs))
        keyboard.append(buttons)
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)

def esc(x): return html.escape(str(x if x is not None else ""))

async def send_rich_table(chat_id, title, headers, rows, reply_markup=None, fallback_text=None):
    """Send a native structured table using Telegram Bot API 10.1+ Rich Messages."""
    cells = [[{"text": str(h), "is_header": True, "align": "right"} for h in headers]]
    for row in rows:
        cells.append([{"text": str(value), "align": "right"} for value in row])
    rich_message = {
        "is_rtl": True,
        "blocks": [
            {"type": "heading", "text": str(title), "size": 2},
            {"type": "table", "cells": cells, "is_bordered": True, "is_striped": True, "is_compact": True}
        ]
    }
    payload = {"chat_id": chat_id, "rich_message": rich_message}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup.model_dump(exclude_none=True) if hasattr(reply_markup, "model_dump") else reply_markup
    try:
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"https://api.telegram.org/bot{TOKEN}/sendRichMessage", json=payload) as response:
                data = await response.json(content_type=None)
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "sendRichMessage failed"))
        return data.get("result")
    except Exception as exc:
        log.warning("Rich table failed; falling back to formatted text: %s", exc)
        if fallback_text is None:
            fallback_text = title + "\n" + " | ".join(headers) + "\n" + "\n".join(" | ".join(map(str, r)) for r in rows)
        return await bot.send_message(chat_id, f"<b>{esc(title)}</b>\n<pre>{esc(fallback_text)}</pre>", reply_markup=reply_markup)

def custom_emoji(emoji_id, fallback):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
def role_label(uid):
    u=db.user(uid); role=u["role"] if u else "customer"
    return {"owner":"مالک", "developer":"توسعه‌دهنده", "admin":"ادمین", "customer":"کاربر"}.get(role,role)
def home(uid):
    rows=[["تبلیغات گروه", "تبلیغ کانال"], ["تبلیغات گیووای", "ثبت کانال"],
          ["سفارش‌های من", "حساب کاربری"], ["پشتیبانی", "راهنما"]]
    if db.is_staff(uid): rows.append(["پنل مدیریت"])
    return kb(rows)
def admin_kb():
    return kb([["درخواست‌های کانال", "همه سفارش‌ها"], ["بررسی پرداخت‌ها", "تیکت‌های پشتیبانی"],
               ["مدیریت خدمات", "روش‌های پرداخت"], ["کانال‌های تأییدشده", "مدیریت کاربران"], ["مدیریت مدیران"],
               ["گزارش کلی", "پشتیبان‌گیری"], ["منوی اصلی"]])

class Flow(StatesGroup):
    choose_target=State(); choose_product=State(); choose_package=State(); destination=State(); join_target=State()
    banner=State(); ad_text=State(); notes=State(); confirm=State(); choose_payment=State(); txid=State(); receipt=State()
    channel_admin_confirm=State(); channel_link=State(); support=State(); followup=State()
    wallet_deposit_amount=State(); wallet_deposit_method=State(); wallet_deposit_txid=State(); wallet_deposit_receipt=State()
    add_package_product=State(); add_package_title=State(); add_package_desc=State(); add_package_price=State()
    add_package_currency=State(); add_package_duration=State(); add_product_category=State(); add_product_title=State()
    add_product_kind=State(); add_product_desc=State(); add_wallet_currency=State(); add_wallet_network=State()
    add_wallet_address=State(); add_admin_id=State(); remove_admin_id=State(); order_status=State();
    user_lookup=State(); user_action_amount=State(); user_block_reason=State(); custom_channel_link=State()
    giveaway_duration=State(); giveaway_prize_type=State(); giveaway_prize_amount=State(); giveaway_channels=State()

async def send_group(text, reply_markup=None):
    try:
        msg=await bot.send_message(MANAGEMENT_GROUP_ID, text, parse_mode="HTML", reply_markup=reply_markup)
        return msg
    except Exception as e:
        log.exception("Cannot send to management group")
        return None

async def notify_staff(text):
    return await send_group(text)

async def group_notice(kind, ref_id, uid, text, reply_markup=None):
    msg=await send_group(text, reply_markup=reply_markup)
    if msg: db.add_group_link(msg.message_id, kind, ref_id, uid)
    return msg

def group_action_keyboard(kind, ref_id):
    actions = {
        "channel": [[InlineKeyboardButton(text="✅ تأیید کانال", callback_data=f"mg:{kind}:{ref_id}:approve"), InlineKeyboardButton(text="❌ رد درخواست", callback_data=f"mg:{kind}:{ref_id}:reject")]],
        "custom_channel": [[InlineKeyboardButton(text="🔎 شروع رایزنی", callback_data=f"mg:{kind}:{ref_id}:contact"), InlineKeyboardButton(text="❌ رد درخواست", callback_data=f"mg:{kind}:{ref_id}:reject")]],
        "payment": [[InlineKeyboardButton(text="✅ تأیید پرداخت", callback_data=f"mg:{kind}:{ref_id}:approve"), InlineKeyboardButton(text="❌ رد پرداخت", callback_data=f"mg:{kind}:{ref_id}:reject")]],
        "wallet": [[InlineKeyboardButton(text="✅ تأیید شارژ", callback_data=f"mg:{kind}:{ref_id}:approve"), InlineKeyboardButton(text="❌ رد شارژ", callback_data=f"mg:{kind}:{ref_id}:reject")]],
        "order": [[InlineKeyboardButton(text="🔵 شروع اجرا", callback_data=f"mg:{kind}:{ref_id}:progress"), InlineKeyboardButton(text="🟢 تکمیل", callback_data=f"mg:{kind}:{ref_id}:complete"), InlineKeyboardButton(text="🔴 لغو", callback_data=f"mg:{kind}:{ref_id}:cancel")]],
    }
    return InlineKeyboardMarkup(inline_keyboard=actions.get(kind, []))

def channel_label(row, index):
    link = str(row["invite_link"] or "")
    if link.startswith("@"):
        handle = link
    else:
        path = urlparse(link).path.strip("/")
        handle = "@" + path.split("/")[0] if path and not path.startswith("+") and path != "joinchat" else row["target_type"]
    return f"{handle} #{index}"

async def show_target_list(message, state, selected=None):
    targets = db.approved_channels()
    rows = [[channel_label(x, i)] for i, x in enumerate(targets, 1)]
    if selected:
        rows = [["➕ افزودن کانال دیگر"], ["اتمام انتخاب کانال‌ها"]] + rows
    await message.answer("<b>فهرست کانال‌ها و گروه‌های تأییدشده:</b>\nبرای مشاهده و انتخاب، روی نام کانال بزنید.", parse_mode="HTML", reply_markup=kb(rows + [["کانال مدنظر من در لیست نیست"], ["بازگشت", "منوی اصلی"]]))

async def start_order(message:Message, state:FSMContext, slug:str):
    with db.conn() as c: cat=c.execute("SELECT * FROM categories WHERE slug=? AND active=1",(slug,)).fetchone()
    if not cat:
        await message.answer("این دسته خدمات فعلاً فعال نیست.", reply_markup=home(message.from_user.id)); return
    targets=db.approved_channels()
    await state.clear(); await state.update_data(category_id=cat["id"], category_title=cat["title"], category_slug=slug)
    if not targets:
        await state.set_state(Flow.choose_target)
        await message.answer("<b>هنوز کانال تأییدشده‌ای در فهرست نیست.</b>\nمی‌توانید کانال مدنظر خود را برای بررسی و رایزنی ارسال کنید.",parse_mode="HTML",reply_markup=kb([["کانال مدنظر من در لیست نیست"],["بازگشت","منوی اصلی"]]))
        return
    await state.set_state(Flow.choose_target)
    await message.answer("<b>ابتدا فهرست کانال‌ها و گروه‌های مقصد را باز کنید.</b>", parse_mode="HTML", reply_markup=kb([["نمایش لیست کانال‌ها"],["کانال مدنظر من در لیست نیست"],["بازگشت","منوی اصلی"]]))

@dp.message(CommandStart())
async def start(m:Message,state:FSMContext):
    db.upsert_user(m.from_user); await state.clear()
    await m.answer(f"{custom_emoji('5823539211684287784', '👋')} <b>به {BOT_NAME} خوش آمدید</b>\n\n{custom_emoji('5823392736119624565', '🚀')} <b>توسعه چنل و گروهتون را به ما بسپارید</b>\n\n{custom_emoji('5821179994738529951', '💬')} <b>درصورت ایجاد هرگونه مشکل در سفارشات با تیم پشتیبانی ما در ارتباط باشید</b>\n\nاز منوی زیر خدمات موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=home(m.from_user.id))

@dp.message(Command("id"))
async def get_id(m:Message): await m.answer(f"شناسه عددی شما: <code>{m.from_user.id}</code>",parse_mode="HTML")

@dp.message(F.text.in_({"منوی اصلی","بازگشت"}))
async def main_menu(m:Message,state:FSMContext):
    await state.clear(); db.upsert_user(m.from_user); await m.answer("منوی اصلی:",reply_markup=home(m.from_user.id))

@dp.message(F.text=="تبلیغات گروه")
async def group_ads(m:Message,state:FSMContext): await start_order(m,state,"group_ads")
@dp.message(F.text=="تبلیغ کانال")
async def channel_ads(m:Message,state:FSMContext): await start_order(m,state,"channel_ads")
@dp.message(F.text=="تبلیغات گیووای")
async def giveaway_ads(m:Message,state:FSMContext): await start_order(m,state,"giveaway_ads")

@dp.message(F.text=="ثبت کانال")
async def channel_register(m:Message,state:FSMContext):
    await state.set_state(Flow.channel_admin_confirm)
    await m.answer(f"{custom_emoji('5823551254772586211','📢')} <b>ثبت کانال یا گروه</b>\n\nابتدا اکانت <b>{REQUIRED_ADMIN_ACCOUNT}</b> را در کانال یا گروه خود ادمین کنید.\n\n{custom_emoji('6007944173703929511','🔔')} پس از انجام، دکمه «ادمین کردم» را بزنید.",parse_mode="HTML",reply_markup=kb([["ادمین کردم"],["بازگشت"]]))

@dp.message(Flow.channel_admin_confirm,F.text=="ادمین کردم")
async def channel_admin_done(m:Message,state:FSMContext):
    await state.set_state(Flow.channel_link)
    await m.answer("حالا لینک عمومی یا لینک دعوت کانال/گروه خود را ارسال کنید:",reply_markup=kb([["بازگشت"]]))

@dp.message(Flow.channel_link)
async def channel_link(m:Message,state:FSMContext):
    link=(m.text or "").strip()
    if not (link.startswith("https://t.me/") or link.startswith("http://t.me/") or link.startswith("@")):
        await m.answer("لطفاً لینک معتبر تلگرام مثل https://t.me/channel را ارسال کنید."); return
    cid=db.submit_channel(m.from_user.id,"channel/group",link)
    await group_notice("channel",cid,m.from_user.id,
        f"<b>درخواست ثبت کانال/گروه</b>\nشناسه درخواست: <code>#{cid}</code>\nکاربر: <code>{m.from_user.id}</code> (@{esc(m.from_user.username or '-')})\nلینک: {esc(link)}\n\nاز دکمه‌های زیر برای بررسی درخواست استفاده کنید.", group_action_keyboard("channel", cid))
    await state.clear()
    await m.answer("درخواست ثبت کانال یا گروه شما دریافت شد. پس از بررسی مدیریت، نتیجه از همین ربات اطلاع‌رسانی می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(Flow.choose_target)
async def choose_target(m:Message,state:FSMContext):
    if m.text == "نمایش لیست کانال‌ها":
        await show_target_list(m,state)
        return
    if m.text == "کانال مدنظر من در لیست نیست":
        await state.set_state(Flow.custom_channel_link)
        await m.answer("<b>لینک یا آیدی کانال مدنظرتان را ارسال کنید.</b> درخواست شما برای رایزنی به مدیریت ارسال می‌شود.", parse_mode="HTML")
        return
    targets=db.approved_channels(); chosen=None
    for i,x in enumerate(targets,1):
        if m.text==channel_label(x,i): chosen=x; break
    if not chosen: await m.answer("یکی از کانال‌ها یا گروه‌های فهرست را انتخاب کنید."); return
    d=await state.get_data(); await state.update_data(target_id=chosen["id"],target_link=chosen["invite_link"])
    items=[]
    with db.conn() as c: items=c.execute("SELECT * FROM products WHERE category_id=? AND active=1 ORDER BY sort_order,id",(d["category_id"],)).fetchall()
    if not items: await m.answer("برای این دسته هنوز خدمتی تعریف نشده است.",reply_markup=home(m.from_user.id)); await state.clear(); return
    await state.set_state(Flow.choose_product)
    await m.answer("خدمت موردنظر را انتخاب کنید:",reply_markup=kb([[p["title"]] for p in items]+[["بازگشت","منوی اصلی"]]))

@dp.message(Flow.custom_channel_link)
async def custom_channel_link_save(m:Message,state:FSMContext):
    link=(m.text or "").strip()
    if not (link.startswith("https://t.me/") or link.startswith("http://t.me/") or link.startswith("@")):
        await m.answer("لطفاً لینک معتبر یا آیدی عمومی کانال را بفرستید."); return
    rid=db.submit_custom_channel(m.from_user.id,link)
    await group_notice("custom_channel",rid,m.from_user.id,
        f"<b>درخواست کانال خارج از فهرست</b>\nشناسه: <code>#{rid}</code>\nکاربر: <code>{m.from_user.id}</code>\nلینک: {esc(link)}\n\nبرای بررسی از دکمه‌های زیر استفاده کنید.", group_action_keyboard("custom_channel", rid))
    await state.clear()
    await m.answer(f"{custom_emoji('5823392736119624565','📨')} <b>درخواست شما دریافت شد.</b>\n\n{custom_emoji('6007944173703929511','🔔')} تیم ما کانال موردنظر را بررسی و برای هماهنگی اقدام می‌کند. نتیجه را از همین ربات به شما اطلاع می‌دهیم.",parse_mode="HTML",reply_markup=home(m.from_user.id))

@dp.message(Flow.choose_product)
async def product_chosen(m:Message,state:FSMContext):
    d=await state.get_data()
    with db.conn() as c: p=c.execute("SELECT * FROM products WHERE category_id=? AND title=? AND active=1",(d["category_id"],m.text)).fetchone()
    if not p: await m.answer("لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید."); return
    packs=db.packages(p["id"])
    if not packs: await m.answer("برای این خدمت هنوز پکیجی تعریف نشده است.",reply_markup=home(m.from_user.id)); await state.clear(); return
    await state.update_data(product_id=p["id"],product_title=p["title"],product_kind=p["kind"])
    await state.set_state(Flow.choose_package)
    await m.answer("پکیج موردنظر را انتخاب کنید:",reply_markup=kb([[f"{x['title']} | {x['price']} {x['currency']}"] for x in packs]+[["بازگشت","منوی اصلی"]]))

@dp.message(Flow.choose_package)
async def package_chosen(m:Message,state:FSMContext):
    d=await state.get_data()
    with db.conn() as c: packs=c.execute("SELECT * FROM packages WHERE product_id=? AND active=1",(d["product_id"],)).fetchall()
    chosen=next((p for p in packs if m.text==f"{p['title']} | {p['price']} {p['currency']}"),None)
    if not chosen: await m.answer("لطفاً یکی از پکیج‌ها را انتخاب کنید."); return
    await state.update_data(package_id=chosen["id"],package_title=chosen["title"],price=float(chosen["price"]),base_price=float(chosen["price"]),currency=chosen["currency"],duration=chosen["duration"],description=chosen["description"],details={})
    if d.get("category_slug") == "giveaway_ads":
        await state.set_state(Flow.giveaway_duration)
        await m.answer("<b>مدت زمان برگزاری گیووای را مشخص کنید.</b>\nمثال: ۲۴ ساعت، ۳ روز یا ۷ روز",parse_mode="HTML",reply_markup=kb([["۲۴ ساعت","۳ روز"],["۷ روز","۱۴ روز"],["بازگشت","منوی اصلی"]]))
        return
    await state.set_state(Flow.destination)
    await m.answer("توضیحات یا لینک موردنیاز سفارش را ارسال کنید:")

@dp.message(Flow.giveaway_duration)
async def giveaway_duration(m:Message,state:FSMContext):
    value=(m.text or "").strip()
    if not value or len(value)>40:
        await m.answer("مدت زمان را به‌صورت کوتاه وارد کنید؛ مثلاً ۲۴ ساعت یا ۳ روز."); return
    await state.update_data(giveaway_duration=value)
    await state.set_state(Flow.giveaway_prize_type)
    await m.answer("<b>نوع جایزه گیووای را انتخاب کنید:</b>",parse_mode="HTML",reply_markup=kb([["🎁 گیفت","⭐ استارز"],["💎 تون"],["بازگشت","منوی اصلی"]]))

@dp.message(Flow.giveaway_prize_type)
async def giveaway_prize_type(m:Message,state:FSMContext):
    kinds={"🎁 گیفت":"Gift","⭐ استارز":"Stars","💎 تون":"TON"}
    if m.text not in kinds:
        await m.answer("یکی از گزینه‌های گیفت، استارز یا تون را انتخاب کنید."); return
    kind=kinds[m.text]
    await state.update_data(giveaway_prize_type=kind)
    await state.set_state(Flow.giveaway_prize_amount)
    if kind=="Gift":
        try:
            owner=await bot.get_chat(OWNER_ID)
            recipient=("@"+owner.username) if owner.username else f"شناسه عددی <code>{OWNER_ID}</code>"
        except Exception:
            recipient=f"شناسه عددی <code>{OWNER_ID}</code>"
        await m.answer(f"<b>جایزه گیفت</b>\nگیفت موردنظر را مشخص کنید. جایزه باید برای حساب مالک ارسال شود: {recipient}\n\nنام یا مدل گیفت را وارد کنید:",parse_mode="HTML")
    elif kind=="Stars":
        try:
            owner=await bot.get_chat(OWNER_ID)
            recipient=("@"+owner.username) if owner.username else f"پروفایل مالک با شناسه <code>{OWNER_ID}</code>"
        except Exception:
            recipient=f"پروفایل مالک با شناسه <code>{OWNER_ID}</code>"
        await m.answer(f"<b>جایزه استارز</b>\nاستارز را به حساب مالک ارسال کنید: {recipient}\n\nتعداد استارز را وارد کنید:",parse_mode="HTML")
    else:
        methods=[x for x in db.methods() if str(x["currency"]).upper()=="TON"]
        address=methods[0]["address"] if methods else "آدرس کیف پول هنوز توسط مدیریت ثبت نشده است؛ قبل از پرداخت با مالک هماهنگ کنید."
        await m.answer(f"<b>جایزه تون</b>\nکیف پول دریافت جایزه:\n<code>{esc(address)}</code>\n\nمقدار جایزه را به TON وارد کنید:",parse_mode="HTML")

@dp.message(Flow.giveaway_prize_amount)
async def giveaway_prize_amount(m:Message,state:FSMContext):
    value=(m.text or "").strip()
    if not value or len(value)>80:
        await m.answer("مقدار یا مشخصات جایزه را وارد کنید."); return
    d=await state.get_data()
    if d.get("giveaway_prize_type") in ("Stars","TON"):
        try:
            amount=float(value.replace(",",""))
            if amount<=0: raise ValueError()
            if d["giveaway_prize_type"]=="Stars" and not amount.is_integer(): raise ValueError()
        except Exception:
            await m.answer("مقدار جایزه باید عددی و بیشتر از صفر باشد."); return
    await state.update_data(giveaway_prize_amount=value)
    targets=db.approved_channels()
    selected=[int(d["target_id"])] if d.get("target_id") else []
    await state.update_data(giveaway_channel_ids=selected)
    await state.set_state(Flow.giveaway_channels)
    await show_giveaway_channels(m,state)

async def show_giveaway_channels(m,state):
    d=await state.get_data(); targets=db.approved_channels(); selected=set(d.get("giveaway_channel_ids",[]))
    rows=[]
    for i,x in enumerate(targets,1):
        label=channel_label(x,i)
        rows.append([("✅ " if x["id"] in selected else "")+label])
    rows.append(["اتمام انتخاب کانال‌ها"])
    await m.answer(f"<b>کانال‌های شرکت‌کننده در گیووای</b>\nحداکثر ۴ کانال می‌توانید انتخاب کنید.\nتعداد انتخاب‌شده: <b>{len(selected)}/4</b>\nهزینه هر کانال: <b>۰٫۵ TON</b>\nبرای افزودن یا حذف، روی نام کانال بزنید.",parse_mode="HTML",reply_markup=kb(rows+[["منوی اصلی"]]))

@dp.message(Flow.giveaway_channels)
async def giveaway_channels(m:Message,state:FSMContext):
    d=await state.get_data(); selected=list(d.get("giveaway_channel_ids",[])); targets=db.approved_channels()
    if m.text=="اتمام انتخاب کانال‌ها":
        if not selected:
            await m.answer("حداقل یک کانال باید انتخاب کنید."); return
        total=float(d["base_price"])+0.5*len(selected)
        selected_rows=[x for x in targets if x["id"] in selected]
        links=[x["invite_link"] for x in selected_rows]
        await state.update_data(price=f"{total:.3f}",currency="TON",giveaway_channel_links=links,
            target_link=", ".join(links),target_id=selected[0],
            giveaway_extra_fee=f"{0.5*len(selected):.3f}")
        await state.set_state(Flow.destination)
        await m.answer(f"<b>تنظیمات گیووای ثبت شد.</b>\nمدت: {esc(d['giveaway_duration'])}\nنوع جایزه: {esc(d['giveaway_prize_type'])}\nمقدار/مشخصات جایزه: {esc(d['giveaway_prize_amount'])}\nتعداد کانال: {len(selected)}\nهزینه کانال‌ها: {0.5*len(selected):.3f} TON\n<b>مبلغ پایه + هزینه کانال‌ها: {total:.3f} TON</b>\n\nحالا توضیحات تکمیلی سفارش را ارسال کنید:",parse_mode="HTML")
        return
    label=m.text or ""
    if label.startswith("✅ "): label=label[2:]
    chosen=next((x for i,x in enumerate(targets,1) if channel_label(x,i)==label),None)
    if not chosen:
        await m.answer("یک کانال از فهرست را انتخاب کنید یا «اتمام انتخاب کانال‌ها» را بزنید."); return
    if chosen["id"] in selected:
        selected.remove(chosen["id"])
    else:
        if len(selected)>=4:
            await m.answer("حداکثر ۴ کانال قابل انتخاب است."); return
        selected.append(chosen["id"])
    await state.update_data(giveaway_channel_ids=selected)
    await show_giveaway_channels(m,state)

@dp.message(Flow.destination)
async def destination(m:Message,state:FSMContext):
    await state.update_data(destination=m.text or m.caption or "")
    d=await state.get_data()
    if d["product_kind"]=="force_join":
        await state.set_state(Flow.join_target); await m.answer("لینک کانال/گروه جوین اجباری را ارسال کنید:")
    else:
        await state.set_state(Flow.banner); await m.answer("اگر بنر دارید تصویر را ارسال کنید؛ در غیر این صورت «ندارم» بنویسید:")

@dp.message(Flow.join_target)
async def join_target(m:Message,state:FSMContext):
    await state.update_data(join_target=m.text or ""); await state.set_state(Flow.ad_text); await m.answer("متن تبلیغ را ارسال کنید:")
@dp.message(Flow.banner)
async def banner(m:Message,state:FSMContext):
    fid=m.photo[-1].file_id if m.photo else (m.document.file_id if m.document else "")
    if not fid and (m.text or "").strip()!="ندارم": await m.answer("تصویر بنر یا عبارت «ندارم» را ارسال کنید."); return
    await state.update_data(banner_file_id=fid); await state.set_state(Flow.ad_text); await m.answer("متن تبلیغ را ارسال کنید:")
@dp.message(Flow.ad_text)
async def ad_text(m:Message,state:FSMContext):
    await state.update_data(ad_text=m.text or m.caption or ""); await state.set_state(Flow.notes); await m.answer("توضیحات تکمیلی (در صورت نداشتن «ندارم»):")
@dp.message(Flow.notes)
async def notes(m:Message,state:FSMContext):
    await state.update_data(notes=m.text or ""); d=await state.get_data()
    details={k:d.get(k,"") for k in ("destination","target_id","target_link","join_target","banner_file_id","ad_text","notes","giveaway_duration","giveaway_prize_type","giveaway_prize_amount","giveaway_channel_links","giveaway_extra_fee")}
    preview=(f"<b>پیش‌نمایش سفارش</b>\nدسته: {esc(d['category_title'])}\nمقصد: {esc(d.get('target_link','-'))}\n"
             f"خدمت: {esc(d['product_title'])}\nپکیج: {esc(d['package_title'])}\nمبلغ: <b>{esc(d['price'])} {esc(d['currency'])}</b>\n"
             f"توضیحات: {esc(details['destination'])}\nمتن تبلیغ: {esc(details['ad_text'])}\n\nسفارش را ثبت می‌کنید؟")
    await state.update_data(details=details); await state.set_state(Flow.confirm)
    await m.answer(preview,parse_mode="HTML",reply_markup=kb([["ثبت سفارش"],["بازگشت","منوی اصلی"]]))

@dp.message(Flow.confirm,F.text=="ثبت سفارش")
async def confirm_order(m:Message,state:FSMContext):
    d=await state.get_data()
    if str(d.get("currency", "")).upper() != "TON":
        await m.answer("این پکیج با واحد قیمت قدیمی ذخیره شده است. مدیریت باید آن را با تعرفه TON دوباره تعریف کند؛ هنوز سفارشی ثبت نشده است.",reply_markup=home(m.from_user.id))
        await state.clear(); return
    order=db.create_order(m.from_user.id,{"id":d["product_id"],"title":d["product_title"]},
        {"id":d["package_id"],"title":d["package_title"],"price":d["price"],"currency":d["currency"]},d["details"])
    db.audit(m.from_user.id,"order_created","order",order["order_no"])
    await group_notice("order",order["order_no"],m.from_user.id,
        f"<b>سفارش جدید</b>\nشناسه: <code>{order['order_no']}</code>\nکاربر: <code>{m.from_user.id}</code>\nخدمت: {esc(order['product_title'])}\nمبلغ: {esc(order['price'])} {esc(order['currency'])}\nمقصد: {esc(d['details'].get('target_link','-'))}", group_action_keyboard("order", order["order_no"]))
    methods=[x for x in db.methods() if x['currency'].upper() in ("TON","GRAM")]
    if not methods:
        await state.clear(); await m.answer(f"سفارش <b>{order['order_no']}</b> ثبت شد. روش پرداخت TON هنوز تنظیم نشده است؛ برای هماهنگی با <a href=\"tg://user?id={OWNER_ID}\">مالک</a> ارتباط بگیرید.",parse_mode="HTML",reply_markup=home(m.from_user.id)); return
    await state.update_data(order_no=order["order_no"],order_id=order["id"]); await state.set_state(Flow.choose_payment)
    await m.answer(f"سفارش <b>{order['order_no']}</b> ثبت شد.\nروش پرداخت را انتخاب کنید:",parse_mode="HTML",
        reply_markup=kb([[f"{x['currency']} | {x['network']}"] for x in methods]+[["منوی اصلی"]]))

@dp.message(Flow.choose_payment)
async def payment_chosen(m:Message,state:FSMContext):
    methods=db.methods(); chosen=next((x for x in methods if m.text==f"{x['currency']} | {x['network']}"),None)
    if not chosen: await m.answer("یکی از روش‌های پرداخت را انتخاب کنید."); return
    d=await state.get_data(); await state.update_data(method_id=chosen["id"]); await state.set_state(Flow.txid)
    await m.answer(f"ارز: {esc(chosen['currency'])}\nشبکه: {esc(chosen['network'])}\nآدرس کیف پول:\n<code>{esc(chosen['address'])}</code>\n\nمبلغ سفارش: {esc(d['price'])} {esc(d['currency'])}\nپس از پرداخت TXID را ارسال کنید.",parse_mode="HTML")
@dp.message(Flow.txid)
async def txid(m:Message,state:FSMContext):
    if not m.text or len(m.text.strip())<8: await m.answer("لطفاً TXID معتبر را ارسال کنید."); return
    await state.update_data(txid=m.text.strip()); await state.set_state(Flow.receipt); await m.answer("تصویر رسید را ارسال کنید یا «ندارم» بنویسید:")
@dp.message(Flow.receipt)
async def receipt(m:Message,state:FSMContext):
    d=await state.get_data(); fid=m.photo[-1].file_id if m.photo else ""
    if not fid and (m.text or "").strip()!="ندارم": await m.answer("تصویر رسید یا «ندارم» را ارسال کنید."); return
    db.order_payment(d["order_id"],d["method_id"],d["txid"],fid); db.audit(m.from_user.id,"payment_submitted","order",d["order_no"])
    gmsg=await group_notice("payment",d["order_no"],m.from_user.id,
        f"<b>پرداخت برای بررسی</b>\nسفارش: <code>{d['order_no']}</code>\nکاربر: <code>{m.from_user.id}</code>\nTXID: <code>{esc(d['txid'])}</code>", group_action_keyboard("payment", d["order_no"]))
    if fid and gmsg:
        try: await bot.send_photo(MANAGEMENT_GROUP_ID,fid,caption=f"رسید پرداخت سفارش {d['order_no']}",reply_to_message_id=gmsg.message_id)
        except Exception: log.exception("receipt forward failed")
    await state.clear(); await m.answer("رسید و اطلاعات پرداخت ثبت شد و پس از بررسی دستی نتیجه اعلام می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="سفارش‌های من")
async def my_orders(m:Message):
    rows=db.user_orders(m.from_user.id)
    if not rows: await m.answer("هنوز سفارشی ثبت نکرده‌اید.",reply_markup=home(m.from_user.id)); return
    labels=[]; table_rows=[]
    status_names={"cancelled":"لغو شده","completed":"تکمیل شده","in_progress":"در حال انجام","awaiting_payment":"در انتظار پرداخت","payment_under_review":"در انتظار بررسی","queued":"در صف اجرا","payment_rejected":"پرداخت رد شده"}
    for x in rows:
        status={"cancelled":"🔴","completed":"🟢","in_progress":"🔵","awaiting_payment":"⚪","payment_under_review":"🟡","queued":"🔵","payment_rejected":"🔴"}.get(x["status"],"⚪")
        labels.append([f"{status} {x['order_no']}"])
        table_rows.append([x['order_no'],x['product_title'],f"{x['price']} {x['currency']}",status_names.get(x['status'],x['status'])])
    await send_rich_table(m.chat.id,"سفارش‌های من",["شماره سفارش","خدمت","مبلغ","وضعیت"],table_rows,reply_markup=kb(labels+[["منوی اصلی"]]))

@dp.message(F.text.regexp(r"^(?:🔴 |🟢 |🔵 |⚪ |🟡 )?BA\d+"))
async def order_detail(m:Message,state:FSMContext):
    order_no=m.text.split()[-1]
    o=db.get_order(order_no)
    if not o or o["user_id"]!=m.from_user.id: return
    try: details=json.loads(o["details"])
    except: details={}
    status_map={"awaiting_payment":"در انتظار پرداخت","payment_under_review":"در انتظار بررسی پرداخت","queued":"تأیید شده / در صف اجرا","in_progress":"در حال انجام","completed":"تکمیل شده","cancelled":"لغو شده","payment_rejected":"پرداخت رد شده"}
    detail_rows=[["شماره سفارش",o['order_no']],["خدمت",o['product_title']],["پکیج",o['package_title']],
                 ["مبلغ",f"{o['price']} {o['currency']}"],["وضعیت",status_map.get(o['status'],o['status'])],
                 ["مقصد",details.get('target_link','-')],["توضیحات",details.get('destination','-')]]
    if o["status"]=="cancelled": detail_rows.append(["علت لغو",details.get('cancel_reason','ثبت نشده')])
    await send_rich_table(m.chat.id,f"جزئیات سفارش {o['order_no']}",["عنوان","مقدار"],detail_rows,reply_markup=kb([[f"پیگیری {o['order_no']}"] ,["سفارش‌های من","منوی اصلی"]]))

@dp.message(F.text.startswith("پیگیری BA"))
async def followup_start(m:Message,state:FSMContext):
    order_no=m.text.replace("پیگیری ","",1).strip(); o=db.get_order(order_no)
    if not o or o["user_id"]!=m.from_user.id: await m.answer("سفارش پیدا نشد."); return
    await state.update_data(followup_order=order_no); await state.set_state(Flow.followup)
    await m.answer("لطفاً مشکل یا درخواست پیگیری خود درباره این سفارش را بنویسید:")
@dp.message(Flow.followup)
async def followup_save(m:Message,state:FSMContext):
    d=await state.get_data(); order_no=d["followup_order"]; fid=db.create_followup(order_no,m.from_user.id,m.text or m.caption or "پیام")
    await group_notice("followup",fid,m.from_user.id,f"<b>پیگیری سفارش</b>\nسفارش: <code>{order_no}</code>\nکاربر: <code>{m.from_user.id}</code>\nپیام مشتری:\n{esc(m.text or m.caption or 'رسانه')}\n\nبرای پاسخ به مشتری، روی همین پیام Reply کنید و پاسخ را ارسال کنید.")
    await state.clear(); await m.answer("درخواست شما به کارشناسان ما ارسال شد. پاسخ از همین ربات برایتان فرستاده می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="حساب کاربری")
async def profile(m:Message):
    u=db.user(m.from_user.id); balance=float(u["balance_ton"] or 0) if u else 0
    rows=[["شناسه تلگرام",m.from_user.id],["نام",m.from_user.full_name],
          ["نام کاربری",("@"+m.from_user.username) if m.from_user.username else "ندارد"],
          ["نقش",role_label(m.from_user.id)],["موجودی کیف پول",f"{balance:.3f} TON"]]
    if u and float(u["balance"] or 0)>0:
        rows.append(["موجودی قدیمی (USDT)",f"{float(u['balance']):.2f} USDT"])
    markup=kb([["شارژ کیف پول","تاریخچه کیف پول"],["منوی اصلی"]])
    await send_rich_table(m.chat.id,"👤 حساب کاربری",["عنوان","مقدار"],rows,reply_markup=markup)

@dp.message(F.text=="تاریخچه کیف پول")
async def wallet_history(m:Message):
    rows=db.wallet_history(m.from_user.id)
    if not rows: await m.answer("هنوز تراکنشی در کیف پول شما ثبت نشده است.",reply_markup=home(m.from_user.id)); return
    data=[[f"#{x['id']}",x['kind'],f"{x['amount']} {x['currency']}",x['status'],x['created_at'][:16]] for x in rows]
    await send_rich_table(m.chat.id,"تاریخچه کیف پول",["شناسه","نوع","مبلغ","وضعیت","تاریخ"],data,reply_markup=home(m.from_user.id))

@dp.message(F.text=="شارژ کیف پول")
async def wallet_deposit_start(m:Message,state:FSMContext):
    await state.set_state(Flow.wallet_deposit_amount); await m.answer("<b>مبلغ شارژ را به TON وارد کنید:</b>",parse_mode="HTML")
@dp.message(Flow.wallet_deposit_amount)
async def wallet_deposit_amount(m:Message,state:FSMContext):
    try: amount=float(m.text.replace(",","")); assert amount>0
    except: await m.answer("مبلغ باید عددی و بیشتر از صفر باشد."); return
    await state.update_data(deposit_amount=amount); await state.set_state(Flow.wallet_deposit_method)
    await m.answer("<b>روش شارژ کیف پول را انتخاب کنید:</b>",parse_mode="HTML",reply_markup=kb([["پرداخت با تون (گرام)"],["پرداخت با سایر رمزارزها"],["بازگشت"]]))
@dp.message(Flow.wallet_deposit_method)
async def wallet_deposit_method(m:Message,state:FSMContext):
    d=await state.get_data()
    if d.get("deposit_ton_methods"):
        methods=[x for x in db.methods() if x['id'] in d["deposit_ton_methods"]]
        chosen=next((x for x in methods if m.text==f"{x['currency']} | {x['network']}"),None)
        if chosen:
            await state.update_data(deposit_method=chosen["id"]); await state.set_state(Flow.wallet_deposit_txid)
            await m.answer(f"<b>آدرس پرداخت TON:</b>\n<code>{esc(chosen['address'])}</code>\n<b>مبلغ:</b> {d['deposit_amount']} TON\nپس از پرداخت، TXID را ارسال کنید.",parse_mode="HTML")
            return
    if m.text == "پرداخت با سایر رمزارزها":
        await state.clear()
        await m.answer(f"برای پرداخت با سایر رمزارزها، مبلغ <b>{d['deposit_amount']} TON</b> یا معادل توافق‌شده را با مالک هماهنگ کنید: <a href=\"tg://user?id={OWNER_ID}\">ارتباط با مالک</a>",parse_mode="HTML",reply_markup=home(m.from_user.id))
        return
    if m.text != "پرداخت با تون (گرام)":
        await m.answer("یکی از دو روش نمایش‌داده‌شده را انتخاب کنید."); return
    methods=[x for x in db.methods() if x['currency'].upper() in ("TON","GRAM")]
    if not methods:
        await state.clear(); await m.answer(f"روش پرداخت TON هنوز تنظیم نشده است. برای هماهنگی با <a href=\"tg://user?id={OWNER_ID}\">مالک</a> ارتباط بگیرید.",parse_mode="HTML",reply_markup=home(m.from_user.id)); return
    await state.update_data(deposit_ton_methods=[x['id'] for x in methods]); await state.set_state(Flow.wallet_deposit_method)
    await m.answer("<b>شبکه پرداخت TON را انتخاب کنید:</b>",parse_mode="HTML",reply_markup=kb([[f"{x['currency']} | {x['network']}"] for x in methods]+[["بازگشت"]]))
@dp.message(Flow.wallet_deposit_txid)
async def wallet_deposit_txid(m:Message,state:FSMContext):
    if not m.text or len(m.text.strip())<8: await m.answer("TXID معتبر ارسال کنید."); return
    await state.update_data(deposit_txid=m.text.strip()); await state.set_state(Flow.wallet_deposit_receipt); await m.answer("رسید پرداخت را بفرستید یا «ندارم» بنویسید:")
@dp.message(Flow.wallet_deposit_receipt)
async def wallet_deposit_receipt(m:Message,state:FSMContext):
    d=await state.get_data(); fid=m.photo[-1].file_id if m.photo else ""
    if not fid and (m.text or "").strip()!="ندارم": await m.answer("رسید یا «ندارم» ارسال کنید."); return
    entry=db.add_wallet_entry(m.from_user.id,d["deposit_amount"],"TON","deposit","pending",f"TXID:{d['deposit_txid']} method:{d['deposit_method']} receipt:{fid}")
    gmsg=await group_notice("wallet",entry,m.from_user.id,f"<b>درخواست شارژ کیف پول</b>\nشناسه: #{entry}\nکاربر: <code>{m.from_user.id}</code>\nمبلغ: {d['deposit_amount']} TON\nTXID: <code>{esc(d['deposit_txid'])}</code>", group_action_keyboard("wallet", entry))
    if fid and gmsg:
        try: await bot.send_photo(MANAGEMENT_GROUP_ID,fid,caption=f"رسید شارژ کیف پول #{entry}",reply_to_message_id=gmsg.message_id)
        except Exception: log.exception("wallet receipt forward failed")
    await state.clear(); await m.answer("درخواست شارژ ثبت شد و پس از بررسی دستی به موجودی اضافه می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="راهنما")
async def help_user(m:Message):
    await m.answer("۱) یکی از دسته‌های تبلیغ را انتخاب کنید.\n۲) مقصد تبلیغ را از فهرست کانال‌های تأییدشده انتخاب کنید.\n۳) خدمت و پکیج را انتخاب و سفارش را ثبت کنید.\n۴) پرداخت را انجام دهید و TXID و رسید را بفرستید.\nتمام تبلیغات به‌صورت دستی توسط تیم انجام می‌شود.",reply_markup=home(m.from_user.id))
@dp.message(F.text=="پشتیبانی")
async def support_start(m:Message,state:FSMContext):
    await state.set_state(Flow.support)
    intro=(f"{custom_emoji('5821179994738529951','💬')} <b>ارتباط با پشتیبانی بوستلی اد</b>\n\n"
           "برای پیگیری سفارش، مشکل پرداخت یا دریافت راهنمایی، پیام خود را با جزئیات بنویسید.\n\n"
           "در صورت ارتباط با سفارش، شماره سفارش را هم ارسال کنید تا سریع‌تر بررسی شود.\n\n"
           "<b>پیام شما مستقیماً برای تیم پشتیبانی ارسال می‌شود و پاسخ را همین‌جا دریافت می‌کنید.</b>")
    await m.answer(intro,parse_mode="HTML",reply_markup=kb([["بازگشت","منوی اصلی"]]))
@dp.message(Flow.support)
async def support_save(m:Message,state:FSMContext):
    if m.text in ("پنل مدیریت", "منوی اصلی", "بازگشت"):
        await state.clear()
        if m.text == "پنل مدیریت" and db.is_staff(m.from_user.id):
            await m.answer("<b>پنل مدیریت Boostly Ads</b>",parse_mode="HTML",reply_markup=admin_kb())
        else:
            await m.answer("<b>منوی اصلی</b>",parse_mode="HTML",reply_markup=home(m.from_user.id))
        return
    body=m.text or m.caption or "رسانه"
    tid=db.add_ticket(m.from_user.id,"درخواست پشتیبانی",body)
    group_msg=await group_notice("support",tid,m.from_user.id,
        f"{custom_emoji('5821179994738529951','💬')} <b>درخواست جدید پشتیبانی — Boostly Ads</b>\n\n<b>مشخصات کاربر</b>\nشناسه: <code>{m.from_user.id}</code>\nنام: {esc(m.from_user.full_name)}\nنام کاربری: @{esc(m.from_user.username or '-')}\n\n<b>پیام مشتری</b>\n{esc(body)}\n\n<b>راهنمای پاسخ:</b> روی همین پیام Reply کنید و پاسخ را بفرستید.")
    if m.photo and group_msg:
        try: await bot.send_photo(MANAGEMENT_GROUP_ID,m.photo[-1].file_id,reply_to_message_id=group_msg.message_id)
        except Exception: pass
    await state.clear(); await m.answer("پیام شما به کارشناسان ما ارسال شد. از همراهی شما سپاسگزاریم.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="پنل مدیریت")
async def admin_panel(m:Message):
    if not db.is_staff(m.from_user.id): return
    await m.answer("<b>پنل مدیریت Boostly Ads</b>\nبخش موردنظر را انتخاب کنید:",parse_mode="HTML",reply_markup=admin_kb())

@dp.message(F.text=="درخواست‌های کانال")
async def channel_admin_list(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.pending_channels()
    if not rows: await m.answer("درخواست تأییدنشده‌ای وجود ندارد.",reply_markup=admin_kb()); return
    for x in rows:
        await m.answer(f"درخواست #{x['id']}\nکاربر: {x['user_id']}\nلینک: {esc(x['invite_link'])}\nوضعیت: در انتظار بررسی\nبرای بررسی به پیام درخواست در گروه مدیریت Reply کنید.",parse_mode="HTML")

@dp.message(F.text=="کانال‌های تأییدشده")
async def approved_channels_admin(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.approved_channels()
    if not rows: await m.answer("کانال یا گروه تأییدشده‌ای ثبت نشده است."); return
    await m.answer("\n".join(f"#{x['id']} | کاربر {x['user_id']} | {esc(x['invite_link'])}" for x in rows)+"\n\nبرای حذف، دستور /removechannel شناسه را ارسال کنید.",parse_mode="HTML")

@dp.message(Command("removechannel"))
async def remove_channel_cmd(m:Message):
    if not db.is_privileged(m.from_user.id): return
    parts=(m.text or '').split(maxsplit=1)
    if len(parts)!=2 or not parts[1].isdigit(): await m.answer("استفاده: /removechannel شناسه"); return
    db.deactivate_channel(int(parts[1])); db.audit(m.from_user.id,"channel_removed","channel",parts[1]); await m.answer("کانال از فهرست مقصدهای تبلیغاتی خارج شد.")

@dp.message(F.text=="گزارش کلی")
async def report(m:Message):
    if not db.is_staff(m.from_user.id): return
    s=db.stats()
    with db.conn() as c:
        active_users=c.execute("SELECT COUNT(*) n FROM users WHERE blocked=0 AND active=1").fetchone()['n']
        blocked_users=c.execute("SELECT COUNT(*) n FROM users WHERE blocked=1").fetchone()['n']
        completed=c.execute("SELECT COUNT(*) n FROM orders WHERE status='completed'").fetchone()['n']
        cancelled=c.execute("SELECT COUNT(*) n FROM orders WHERE status='cancelled'").fetchone()['n']
    await send_rich_table(m.chat.id,"گزارش کلی Boostly Ads",["شاخص","مقدار"],[["کل کاربران",s['users']],["کاربران فعال",active_users],["کاربران مسدود",blocked_users],["کل سفارش‌ها",s['orders']],["سفارش تکمیل‌شده",completed],["سفارش لغوشده",cancelled],["پرداخت‌های در انتظار",s['pending']],["مجموع فروش ثبت‌شده",f"{s['revenue']} TON"]],reply_markup=admin_kb())

@dp.message(F.text=="همه سفارش‌ها")
async def admin_orders(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.all_orders()
    if not rows: await m.answer("سفارشی ثبت نشده است."); return
    table_rows=[[x['order_no'],x['user_id'],x['product_title'],f"{x['price']} {x['currency']}",x['status']] for x in rows[:40]]
    await send_rich_table(m.chat.id,"همه سفارش‌ها",["شماره","کاربر","خدمت","مبلغ","وضعیت"],table_rows,reply_markup=admin_kb())
    await m.answer("برای تغییر وضعیت هر سفارش، دستور زیر را بفرستید:\n<code>وضعیت BA... </code>\nو سپس یکی از وضعیت‌های مجاز را وارد کنید.",parse_mode="HTML")

@dp.message(F.text=="بررسی پرداخت‌ها")
async def admin_payments(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.pending_payments()
    if not rows: await m.answer("پرداخت در انتظار بررسی وجود ندارد."); return
    await send_rich_table(m.chat.id,"پرداخت‌های در انتظار بررسی",["شناسه","سفارش","کاربر","مبلغ","TXID"],[[x['id'],x['order_no'],x['user_id'],f"{x['price']} {x['currency']}",x['txid']] for x in rows],reply_markup=admin_kb())
    for x in rows:
        await m.answer(f"<b>بررسی پرداخت #{x['id']}</b>\nبرای تأیید یا رد از دکمه‌های زیر استفاده کنید.",parse_mode="HTML",reply_markup=kb([[f"تأیید پرداخت {x['id']}",f"رد پرداخت {x['id']}"]]))

@dp.message(F.text.startswith("تأیید پرداخت "))
async def approve_payment(m:Message):
    if not db.is_staff(m.from_user.id): return
    try: pid=int(m.text.rsplit(" ",1)[1])
    except: return
    order=db.review_payment(pid,True,m.from_user.id)
    if not order: await m.answer("پرداخت پیدا نشد یا قبلاً بررسی شده است."); return
    db.audit(m.from_user.id,"payment_approved","payment",pid)
    await bot.send_message(order["user_id"],f"پرداخت سفارش {order['order_no']} تأیید شد و سفارش در صف اجرا قرار گرفت.")
    await m.answer("پرداخت تأیید شد.")
@dp.message(F.text.startswith("رد پرداخت "))
async def reject_payment(m:Message):
    if not db.is_staff(m.from_user.id): return
    try: pid=int(m.text.rsplit(" ",1)[1])
    except: return
    order=db.review_payment(pid,False,m.from_user.id)
    if not order: await m.answer("پرداخت پیدا نشد یا قبلاً بررسی شده است."); return
    db.audit(m.from_user.id,"payment_rejected","payment",pid)
    await bot.send_message(order["user_id"],f"پرداخت سفارش {order['order_no']} رد شد. برای راهنمایی با پشتیبانی تماس بگیرید.")
    await m.answer("پرداخت رد شد.")

@dp.message(F.text.startswith("تأیید شارژ "))
async def approve_deposit(m:Message):
    if not db.is_privileged(m.from_user.id): return
    try: eid=int(m.text.rsplit(" ",1)[1])
    except: return
    row=db.review_wallet_entry(eid,True,m.from_user.id)
    if not row: await m.answer("درخواست پیدا نشد یا بررسی شده است."); return
    await bot.send_message(row["user_id"],f"{custom_emoji('5823338018236272848','🎉')} <b>با تشکر از اعتماد شما، موجودی کیف پول با موفقیت افزایش یافت.</b>\n\n{custom_emoji('5872872125169146997','➕')} <b>+{row['amount']} {row['currency']}</b>",parse_mode="HTML")
    await m.answer("شارژ تأیید و به موجودی اضافه شد.")
@dp.message(F.text.startswith("رد شارژ "))
async def reject_deposit(m:Message):
    if not db.is_privileged(m.from_user.id): return
    try: eid=int(m.text.rsplit(" ",1)[1])
    except: return
    row=db.review_wallet_entry(eid,False,m.from_user.id)
    if not row: await m.answer("درخواست پیدا نشد یا بررسی شده است."); return
    await bot.send_message(row["user_id"],"درخواست شارژ کیف پول شما رد شد. برای بررسی بیشتر با پشتیبانی تماس بگیرید.")
    await m.answer("درخواست شارژ رد شد.")

@dp.message(F.text=="مدیریت خدمات")
async def package_admin(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    await state.clear()
    await m.answer("مدیریت خدمات: از این بخش می‌توانید خدمت یا پکیج جدید بسازید.",reply_markup=kb([["افزودن خدمت","افزودن پکیج"],["منوی مدیریت"]]))

@dp.message(F.text=="افزودن خدمت")
async def product_admin_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    cats=db.categories()
    await state.set_state(Flow.add_product_category)
    await m.answer("شناسه دسته را ارسال کنید:\n"+"\n".join(f"{x['id']}) {x['title']}" for x in cats))

@dp.message(Flow.add_product_category)
async def product_category(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    try:
        cid=int(m.text)
        with db.conn() as c: cat=c.execute("SELECT * FROM categories WHERE id=? AND active=1",(cid,)).fetchone()
        if not cat: raise ValueError()
    except: await m.answer("شناسه دسته معتبر نیست."); return
    await state.update_data(new_category_id=cid); await state.set_state(Flow.add_product_title); await m.answer("نام خدمت جدید را وارد کنید:")

@dp.message(Flow.add_product_title)
async def product_title(m:Message,state:FSMContext):
    await state.update_data(new_product_title=m.text.strip()); await state.set_state(Flow.add_product_kind)
    await m.answer("نوع خدمت را به‌صورت یک شناسه انگلیسی کوتاه وارد کنید؛ مثلاً manual_ads:")

@dp.message(Flow.add_product_kind)
async def product_kind(m:Message,state:FSMContext):
    kind=(m.text or '').strip().lower()
    if not kind.replace('_','').isalnum(): await m.answer("نوع خدمت فقط حروف انگلیسی، عدد و زیرخط باشد."); return
    await state.update_data(new_product_kind=kind); await state.set_state(Flow.add_product_desc); await m.answer("توضیحات خدمت یا «-»:")

@dp.message(Flow.add_product_desc)
async def product_desc(m:Message,state:FSMContext):
    d=await state.get_data(); pid=db.add_product(d['new_category_id'],d['new_product_title'],d['new_product_kind'],'' if m.text=='-' else (m.text or ''))
    db.audit(m.from_user.id,'product_created','product',pid)
    await state.clear(); await m.answer(f"خدمت با شناسه {pid} ساخته شد. حالا از بخش افزودن پکیج برای آن قیمت تعریف کنید.",reply_markup=admin_kb())

@dp.message(F.text=="افزودن پکیج")
async def package_add_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    with db.conn() as c: ps=c.execute("SELECT p.id,p.title,c.title category FROM products p JOIN categories c ON c.id=p.category_id ORDER BY c.id,p.id").fetchall()
    await state.set_state(Flow.add_package_product)
    await m.answer("برای افزودن پکیج، شناسه محصول را ارسال کنید:\n"+"\n".join(f"{p['id']}) {p['category']} — {p['title']}" for p in ps))
@dp.message(Flow.add_package_product)
async def pack_product(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    try:
        pid=int(m.text)
        with db.conn() as c: p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
        if not p: raise ValueError()
    except: await m.answer("شناسه محصول معتبر نیست."); return
    await state.update_data(new_product_id=pid); await state.set_state(Flow.add_package_title); await m.answer("عنوان پکیج را بفرستید:")
@dp.message(Flow.add_package_title)
async def pack_title(m:Message,state:FSMContext):
    await state.update_data(new_title=m.text); await state.set_state(Flow.add_package_desc); await m.answer("توضیحات پکیج یا «-»:")
@dp.message(Flow.add_package_desc)
async def pack_desc(m:Message,state:FSMContext):
    await state.update_data(new_desc="" if m.text=="-" else m.text); await state.set_state(Flow.add_package_price); await m.answer("قیمت عددی:")
@dp.message(Flow.add_package_price)
async def pack_price(m:Message,state:FSMContext):
    try: float(m.text.replace(",",""))
    except: await m.answer("قیمت باید عددی باشد."); return
    await state.update_data(new_price=m.text,new_currency="TON"); await state.set_state(Flow.add_package_duration); await m.answer("<b>واحد قیمت همه خدمات TON است.</b>\nمدت/شرایط پکیج یا «-» را وارد کنید:",parse_mode="HTML")
@dp.message(Flow.add_package_duration)
async def pack_duration(m:Message,state:FSMContext):
    d=await state.get_data(); pid=db.add_package(d["new_product_id"],d["new_title"],d["new_desc"],d["new_price"],d["new_currency"],"" if m.text=="-" else m.text)
    db.audit(m.from_user.id,"package_created","package",pid); await state.clear(); await m.answer(f"پکیج با شناسه {pid} ساخته شد.",reply_markup=admin_kb())

@dp.message(F.text=="روش‌های پرداخت")
async def wallet_admin(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    await state.set_state(Flow.add_wallet_currency); await m.answer("ارز را وارد کنید؛ مثلاً USDT:")
@dp.message(Flow.add_wallet_currency)
async def wallet_currency(m:Message,state:FSMContext):
    await state.update_data(wallet_currency=m.text.upper()); await state.set_state(Flow.add_wallet_network); await m.answer("نام شبکه؛ مثلاً TRC20:")
@dp.message(Flow.add_wallet_network)
async def wallet_network(m:Message,state:FSMContext):
    await state.update_data(wallet_network=m.text); await state.set_state(Flow.add_wallet_address); await m.answer("آدرس کیف پول را ارسال کنید:")
@dp.message(Flow.add_wallet_address)
async def wallet_address(m:Message,state:FSMContext):
    d=await state.get_data(); mid=db.add_method(d["wallet_currency"],d["wallet_network"],m.text.strip()); db.audit(m.from_user.id,"wallet_added","payment_method",mid)
    await state.clear(); await m.answer(f"روش پرداخت با شناسه {mid} اضافه شد.",reply_markup=admin_kb())

@dp.message(F.text=="تیکت‌های پشتیبانی")
async def admin_tickets(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.tickets()
    if not rows: await m.answer("درخواست پشتیبانی بازی وجود ندارد."); return
    for t in rows: await m.answer(f"پیام پشتیبانی | کاربر {t['user_id']}\nموضوع: {t['subject']}\nبرای پاسخ به پیام مربوط در گروه مدیریت Reply کنید.")

@dp.message(F.text=="مدیریت مدیران")
async def manage_admins(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    await state.clear(); await m.answer("مدیریت دسترسی مدیران:",reply_markup=kb([["افزودن ادمین","حذف ادمین"],["منوی مدیریت"]]))

@dp.message(F.text=="افزودن ادمین")
async def add_admin_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.set_state(Flow.add_admin_id); await m.answer("شناسه عددی تلگرام مدیر جدید را ارسال کنید:")

@dp.message(F.text=="حذف ادمین")
async def remove_admin_button(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.set_state(Flow.remove_admin_id); await m.answer("شناسه عددی مدیر برای غیرفعال‌سازی را ارسال کنید:")

@dp.message(Command("removeadmin"))
async def remove_admin_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.set_state(Flow.remove_admin_id); await m.answer("شناسه عددی مدیر برای غیرفعال‌سازی را ارسال کنید:")
@dp.message(Flow.add_admin_id)
async def add_admin_handler(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    try: uid=int(m.text)
    except: await m.answer("شناسه باید عددی باشد."); return
    if uid in (OWNER_ID,DEVELOPER_ID): await m.answer("این شناسه از قبل نقش ویژه دارد."); return
    db.add_admin(uid,"admin"); db.audit(m.from_user.id,"admin_added","user",uid)
    await state.clear(); await m.answer(f"مدیر {uid} اضافه شد.",reply_markup=admin_kb())
@dp.message(Flow.remove_admin_id)
async def remove_admin_handler(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    try: uid=int(m.text)
    except: await m.answer("شناسه باید عددی باشد."); return
    db.remove_admin(uid); db.audit(m.from_user.id,"admin_removed","user",uid)
    await state.clear(); await m.answer(f"مدیر {uid} غیرفعال شد.",reply_markup=admin_kb())

@dp.message(F.text=="مدیریت کاربران")
async def user_admin_start(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    await state.set_state(Flow.user_lookup); await m.answer("شناسه عددی یا نام کاربری کاربر را ارسال کنید:")
@dp.message(Flow.user_lookup)
async def user_admin_lookup(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    u=db.find_user((m.text or '').strip())
    if not u: await m.answer("کاربر با این شناسه یا نام کاربری پیدا نشد."); return
    uid=u['id']
    await state.clear()
    await state.update_data(managed_user_id=uid)
    await send_rich_table(m.chat.id,"مدیریت کاربر",["عنوان","مقدار"],[["شناسه",uid],["نام",u['first_name'] or '-'],["نام کاربری",('@'+u['username']) if u['username'] else '-'],["نقش",u['role']],["موجودی TON",f"{float(u['balance_ton'] or 0):.3f}"],["وضعیت حساب",'مسدود' if u['blocked'] else 'فعال'],["علت مسدودی",u['block_reason'] or '-']],reply_markup=kb([["افزایش موجودی","کاهش موجودی"],["مسدودسازی","رفع مسدودسازی"],["سفارش‌های کاربر","تراکنش‌های کاربر"],["مدیریت کاربران","منوی مدیریت"]]))

@dp.message(Command("add"))
async def command_add_balance(m:Message):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    parts=(m.text or "").split()
    if len(parts)!=3: await m.answer("فرمت صحیح: <code>/add 10 5269896</code>",parse_mode="HTML"); return
    try: amount=float(parts[1].replace(",","")); assert amount>0
    except Exception: await m.answer("مبلغ باید عددی و بیشتر از صفر باشد."); return
    target=db.find_user(parts[2])
    if not target: await m.answer("کاربر پیدا نشد. کاربر باید حداقل یک‌بار ربات را Start کرده باشد."); return
    result=db.adjust_ton_balance(target['id'],amount,'adjustment',m.from_user.id,'افزایش موجودی توسط مدیریت')
    db.audit(m.from_user.id,'balance_added','user',target['id'],{'amount':amount,'currency':'TON'})
    try: await bot.send_message(target['id'],f"<b>موجودی کیف پول شما افزایش یافت.</b>\nمبلغ: <b>+{amount:g} TON</b>",parse_mode="HTML")
    except Exception: pass
    await m.answer(f"موجودی کاربر <code>{target['id']}</code> به میزان <b>{amount:g} TON</b> افزایش یافت.",parse_mode="HTML")

@dp.message(Command("sub"))
async def command_sub_balance(m:Message):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    parts=(m.text or "").split()
    if len(parts)!=3: await m.answer("فرمت صحیح: <code>/sub 10 5269896</code>",parse_mode="HTML"); return
    try: amount=float(parts[1].replace(",","")); assert amount>0
    except Exception: await m.answer("مبلغ باید عددی و بیشتر از صفر باشد."); return
    target=db.find_user(parts[2])
    if not target: await m.answer("کاربر پیدا نشد."); return
    result=db.adjust_ton_balance(target['id'],amount,'deduction',m.from_user.id,'کاهش موجودی توسط مدیریت')
    if result is False: await m.answer("موجودی TON کاربر برای این کاهش کافی نیست."); return
    db.audit(m.from_user.id,'balance_deducted','user',target['id'],{'amount':amount,'currency':'TON'})
    try: await bot.send_message(target['id'],f"<b>از موجودی کیف پول شما کسر شد.</b>\nمبلغ: <b>-{amount:g} TON</b>",parse_mode="HTML")
    except Exception: pass
    await m.answer(f"مبلغ <b>{amount:g} TON</b> از موجودی کاربر کسر شد.",parse_mode="HTML")

@dp.message(Command("block"))
async def command_block_user(m:Message):
    if not db.is_privileged(m.from_user.id): return
    parts=(m.text or "").split(maxsplit=2)
    if len(parts)<2: await m.answer("فرمت: /block 5269896 [علت]"); return
    u=db.find_user(parts[1])
    if not u: await m.answer("کاربر پیدا نشد."); return
    if u['id'] in (OWNER_ID,DEVELOPER_ID): await m.answer("امکان مسدودسازی مالک یا توسعه‌دهنده وجود ندارد."); return
    db.set_user_blocked(u['id'],True,parts[2] if len(parts)>2 else 'مسدودسازی توسط مدیریت')
    db.audit(m.from_user.id,'user_blocked','user',u['id'])
    await m.answer(f"کاربر {u['id']} مسدود شد.")

@dp.message(Command("unblock"))
async def command_unblock_user(m:Message):
    if not db.is_privileged(m.from_user.id): return
    parts=(m.text or "").split()
    if len(parts)!=2: await m.answer("فرمت: /unblock 5269896"); return
    u=db.find_user(parts[1])
    if not u: await m.answer("کاربر پیدا نشد."); return
    db.set_user_blocked(u['id'],False)
    db.audit(m.from_user.id,'user_unblocked','user',u['id'])
    await m.answer(f"کاربر {u['id']} رفع مسدودسازی شد.")

@dp.message(F.text.in_({"افزایش موجودی","کاهش موجودی"}))
async def user_balance_action(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    d=await state.get_data(); uid=d.get('managed_user_id')
    if not uid: await m.answer("ابتدا کاربر را از بخش مدیریت کاربران جست‌وجو کنید."); return
    await state.update_data(balance_action='add' if m.text=='افزایش موجودی' else 'sub')
    await state.set_state(Flow.user_action_amount)
    await m.answer(f"مبلغ به TON را برای {'افزایش' if m.text=='افزایش موجودی' else 'کاهش'} موجودی کاربر {uid} وارد کنید:")

@dp.message(Flow.user_action_amount)
async def user_balance_action_amount(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    d=await state.get_data()
    try: amount=float((m.text or '').replace(',','')); assert amount>0
    except: await m.answer("مبلغ معتبر نیست."); return
    uid=d['managed_user_id']; kind='adjustment' if d['balance_action']=='add' else 'deduction'
    result=db.adjust_ton_balance(uid,amount,kind,m.from_user.id,'تغییر موجودی از پنل مدیریت')
    if result is False: await m.answer("موجودی کاربر کافی نیست."); return
    db.audit(m.from_user.id,'user_balance_changed','user',uid,{'amount':amount,'kind':kind})
    await state.clear(); await m.answer("موجودی با موفقیت به‌روزرسانی شد.",reply_markup=admin_kb())
    try: await bot.send_message(uid,f"موجودی کیف پول شما به میزان {amount:g} TON {'افزایش' if kind=='adjustment' else 'کاهش'} یافت.")
    except Exception: pass

@dp.message(F.text.in_({"مسدودسازی","رفع مسدودسازی"}))
async def user_block_action(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    d=await state.get_data(); uid=d.get('managed_user_id')
    if not uid: await m.answer("ابتدا کاربر را جست‌وجو کنید."); return
    if uid in (OWNER_ID,DEVELOPER_ID): await m.answer("این حساب قابل مسدودسازی نیست."); return
    blocked=m.text=='مسدودسازی'; db.set_user_blocked(uid,blocked,'مسدودسازی از پنل مدیریت' if blocked else '')
    db.audit(m.from_user.id,'user_blocked' if blocked else 'user_unblocked','user',uid)
    await m.answer("کاربر مسدود شد." if blocked else "کاربر رفع مسدودسازی شد.",reply_markup=admin_kb())
    try: await bot.send_message(uid,"دسترسی شما به ربات توسط مدیریت مسدود شد." if blocked else "دسترسی شما به ربات دوباره فعال شد.")
    except Exception: pass

@dp.message(F.text=="سفارش‌های کاربر")
async def admin_user_orders(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    uid=(await state.get_data()).get('managed_user_id')
    if not uid: await m.answer("کاربر انتخاب نشده است."); return
    rows=db.user_order_history(uid)
    if not rows: await m.answer("این کاربر سفارشی ندارد."); return
    await send_rich_table(m.chat.id,f"سفارش‌های کاربر {uid}",["شماره","خدمت","مبلغ","وضعیت"],[[x['order_no'],x['product_title'],f"{x['price']} {x['currency']}",x['status']] for x in rows],reply_markup=admin_kb())

@dp.message(F.text=="تراکنش‌های کاربر")
async def admin_user_wallet(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    uid=(await state.get_data()).get('managed_user_id')
    if not uid: await m.answer("کاربر انتخاب نشده است."); return
    rows=db.wallet_history(uid,50)
    if not rows: await m.answer("تراکنشی ثبت نشده است."); return
    await send_rich_table(m.chat.id,f"تراکنش‌های کاربر {uid}",["شناسه","نوع","مبلغ","واحد","وضعیت"],[[x['id'],x['kind'],x['amount'],x['currency'],x['status']] for x in rows],reply_markup=admin_kb())

@dp.message(F.text.startswith("وضعیت "))
async def status_prompt(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    order_no=m.text.replace("وضعیت ","",1).strip()
    if not db.get_order(order_no): await m.answer("سفارش پیدا نشد."); return
    await state.update_data(status_order=order_no); await state.set_state(Flow.order_status)
    await m.answer("وضعیت جدید را دقیقاً ارسال کنید:\nqueued\nin_progress\ncompleted\ncancelled")
@dp.message(Flow.order_status)
async def status_change(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    allowed={"queued","in_progress","completed","cancelled"}
    reason=None; new_status=m.text
    if m.text.startswith("لغو:"):
        new_status="cancelled"; reason=m.text.split(":",1)[1].strip() or "علت توسط مدیریت ثبت نشده است"
    if new_status not in allowed: await m.answer("وضعیت نامعتبر است. برای لغو همراه علت بنویسید: لغو: علت لغو"); return
    d=await state.get_data(); o=db.set_order_status(d["status_order"],new_status,reason)
    db.audit(m.from_user.id,"order_status_changed","order",o["order_no"],{"status":new_status,"reason":reason})
    notice=f"وضعیت سفارش {o['order_no']} تغییر کرد: {new_status}"
    if reason: notice += f"\nعلت لغو: {reason}"
    await bot.send_message(o["user_id"],notice)
    await state.clear(); await m.answer("وضعیت سفارش به‌روزرسانی شد.",reply_markup=admin_kb())

@dp.message(Command("backup"))
async def backup(m:Message):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    path=db.backup_file()
    try: await m.answer_document(FSInputFile(path,filename="boostly-backup.sqlite3"),caption="نسخه پشتیبان دیتابیس")
    finally:
        try: os.unlink(path)
        except OSError: pass

@dp.callback_query(F.data.startswith("mg:"))
async def management_action_buttons(c:CallbackQuery):
    if not c.message or c.message.chat.id != MANAGEMENT_GROUP_ID:
        await c.answer("این دکمه فقط در گروه مدیریت قابل استفاده است.",show_alert=True); return
    uid=c.from_user.id
    if uid not in (OWNER_ID,DEVELOPER_ID):
        try:
            member=await bot.get_chat_member(MANAGEMENT_GROUP_ID,uid)
            if member.status not in ("administrator","creator"):
                await c.answer("فقط مدیران گروه مجاز هستند.",show_alert=True); return
        except Exception:
            await c.answer("بررسی دسترسی ناموفق بود.",show_alert=True); return
    try: _,kind,ref,action=c.data.split(":",3)
    except Exception:
        await c.answer("درخواست نامعتبر است.",show_alert=True); return
    ref_id=int(ref) if ref.isdigit() else ref
    if kind=="channel":
        row=db.review_channel(ref_id,action=="approve",uid)
        if not row: await c.answer("این درخواست قبلاً بررسی شده است.",show_alert=True); return
        result="تأیید شد" if action=="approve" else "رد شد"
        await bot.send_message(row["user_id"],f"درخواست ثبت کانال/گروه شما {result}.")
    elif kind=="custom_channel":
        row=db.review_custom_channel(ref_id,uid,"rejected" if action=="reject" else "contacted",action)
        if not row: await c.answer("این درخواست قبلاً بررسی شده است.",show_alert=True); return
        text="درخواست کانال شما امکان پیگیری ندارد و بسته شد." if action=="reject" else "درخواست شما بررسی شد؛ تیم ما رایزنی با کانال موردنظر را آغاز می‌کند و نتیجه را اطلاع می‌دهد."
        await bot.send_message(row["user_id"],text)
    elif kind=="payment":
        with db.conn() as con: pay=con.execute("SELECT id FROM payments WHERE order_id=(SELECT id FROM orders WHERE order_no=?) AND status='under_review' ORDER BY id DESC LIMIT 1",(ref,)).fetchone()
        if not pay: await c.answer("پرداخت در انتظار بررسی پیدا نشد.",show_alert=True); return
        order=db.review_payment(pay["id"],action=="approve",uid)
        if not order: await c.answer("پرداخت قبلاً بررسی شده است.",show_alert=True); return
        await bot.send_message(order["user_id"],f"پرداخت سفارش {order['order_no']} {'تأیید شد و در صف اجرا قرار گرفت' if action=='approve' else 'رد شد؛ برای راهنمایی با پشتیبانی تماس بگیرید'}.")
    elif kind=="wallet":
        if not db.is_privileged(uid): await c.answer("فقط مالک یا توسعه‌دهنده مجاز است.",show_alert=True); return
        row=db.review_wallet_entry(ref_id,action=="approve",uid)
        if not row: await c.answer("درخواست شارژ قبلاً بررسی شده است.",show_alert=True); return
        if action=="approve":
            await bot.send_message(row["user_id"],f"{custom_emoji('5823338018236272848','🎉')} <b>با تشکر از اعتماد شما، موجودی کیف پول با موفقیت افزایش یافت.</b>\n\n{custom_emoji('5872872125169146997','➕')} <b>+{row['amount']} {row['currency']}</b>",parse_mode="HTML")
        else:
            await bot.send_message(row["user_id"],"درخواست شارژ کیف پول شما رد شد. برای بررسی بیشتر با پشتیبانی تماس بگیرید.")
    elif kind=="order":
        status={"progress":"in_progress","complete":"completed","cancel":"cancelled"}.get(action)
        if not status: await c.answer("عملیات نامعتبر است.",show_alert=True); return
        reason="لغو توسط مدیریت" if status=="cancelled" else None
        order=db.set_order_status(ref,status,reason)
        if not order: await c.answer("سفارش پیدا نشد.",show_alert=True); return
        label={"in_progress":"در حال انجام","completed":"تکمیل شد","cancelled":"لغو شد"}[status]
        await bot.send_message(order["user_id"],f"وضعیت سفارش <code>{esc(order['order_no'])}</code> به‌روزرسانی شد: <b>{label}</b>.",parse_mode="HTML")
    else:
        await c.answer("نوع درخواست پشتیبانی نمی‌شود.",show_alert=True); return
    try: await c.message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    await c.answer("عملیات با موفقیت انجام شد.")
    await c.message.reply("<b>عملیات ثبت شد.</b>",parse_mode="HTML")

# Reply-to workflows inside the management group: channel review, customer support, order follow-up.
@dp.message(F.chat.id==MANAGEMENT_GROUP_ID, F.reply_to_message)
async def management_group_reply(m:Message):
    if not m.from_user or m.from_user.is_bot: return
    if m.from_user.id not in (OWNER_ID, DEVELOPER_ID):
        try:
            member=await bot.get_chat_member(MANAGEMENT_GROUP_ID,m.from_user.id)
            if member.status not in ("administrator","creator"):
                await m.reply("فقط ادمین‌های گروه مدیریت می‌توانند این عملیات را انجام دهند."); return
        except Exception:
            await m.reply("امکان بررسی دسترسی مدیر گروه وجود ندارد."); return
    link=db.group_link(m.reply_to_message.message_id)
    if not link: return
    body=(m.text or m.caption or "").strip()
    kind=link["kind"]
    if kind in ("channel", "custom_channel", "payment", "wallet", "order"):
        await m.reply("برای این درخواست از دکمه‌های روی پیام اصلی استفاده کنید؛ بررسی با تایپ متن انجام نمی‌شود.")
        return
    if kind=="custom_channel":
        if body not in ("بررسی شد", "در حال رایزنی", "رد"):
            await m.reply("برای این درخواست «بررسی شد»، «در حال رایزنی» یا «رد» را Reply کنید."); return
        row=db.review_custom_channel(int(link["ref_id"]),m.from_user.id,"rejected" if body=="رد" else "contacted",body)
        if not row: await m.reply("این درخواست قبلاً بررسی شده یا وجود ندارد."); return
        user_text="درخواست کانال شما رد شد." if body=="رد" else "درخواست شما بررسی شد؛ تیم ما در حال رایزنی است و نتیجه را به شما اطلاع می‌دهد."
        try: await bot.send_message(row['user_id'],user_text)
        except Exception: pass
        await m.reply("وضعیت درخواست کانال به‌روزرسانی شد."); return
    if kind=="channel":
        if body not in ("تأیید","تایید","رد","رد کانال","تأیید کانال"):
            await m.reply("برای بررسی درخواست، فقط «تأیید» یا «رد» را Reply کنید."); return
        approved=body in ("تأیید","تایید","تأیید کانال")
        row=db.review_channel(int(link["ref_id"]),approved,m.from_user.id)
        if not row: await m.reply("این درخواست قبلاً بررسی شده یا وجود ندارد."); return
        result="تأیید شد" if approved else "رد شد"
        try: await bot.send_message(row["user_id"],f"درخواست ثبت کانال/گروه شما {result}.")
        except Exception: pass
        await m.reply(f"درخواست #{link['ref_id']} {result}.")
        db.audit(m.from_user.id,"channel_reviewed","channel",link["ref_id"],{"result":result})
        return
    if kind=="payment":
        if body not in ("تأیید","تایید","رد"):
            await m.reply("برای بررسی پرداخت، «تأیید» یا «رد» را Reply کنید."); return
        with db.conn() as c: pay=c.execute("SELECT id FROM payments WHERE order_id=(SELECT id FROM orders WHERE order_no=?) AND status='under_review' ORDER BY id DESC LIMIT 1",(link["ref_id"],)).fetchone()
        if not pay: await m.reply("پرداخت در انتظار بررسی پیدا نشد."); return
        approved=body in ("تأیید","تایید")
        order=db.review_payment(pay["id"],approved,m.from_user.id)
        if not order: await m.reply("پرداخت قبلاً بررسی شده است."); return
        try: await bot.send_message(order["user_id"],f"پرداخت سفارش {order['order_no']} {'تأیید شد و در صف اجرا قرار گرفت' if approved else 'رد شد؛ برای راهنمایی با پشتیبانی تماس بگیرید'}.")
        except Exception: pass
        await m.reply("پرداخت بررسی و نتیجه برای مشتری ارسال شد.")
        db.audit(m.from_user.id,"payment_reviewed","payment",pay["id"],{"approved":approved})
        return
    if kind=="wallet":
        if body not in ("تأیید","تایید","رد"):
            await m.reply("برای بررسی شارژ، «تأیید» یا «رد» را Reply کنید."); return
        if not db.is_privileged(m.from_user.id): await m.reply("فقط مالک یا توسعه‌دهنده می‌تواند شارژ کیف پول را تأیید کند."); return
        approved=body in ("تأیید","تایید")
        row=db.review_wallet_entry(int(link["ref_id"]),approved,m.from_user.id)
        if not row: await m.reply("این درخواست قبلاً بررسی شده است."); return
        try: await bot.send_message(row["user_id"],f"درخواست شارژ کیف پول شما {'تأیید شد' if approved else 'رد شد'}.")
        except Exception: pass
        await m.reply("درخواست شارژ بررسی شد.")
        return
    if kind=="order":
        status_map={"درحال انجام":"in_progress","در حال انجام":"in_progress","تکمیل":"completed","تکمیل شد":"completed","لغو":"cancelled"}
        cancel_reason=None
        if body.startswith("لغو:"):
            status_map[body]="cancelled"
            cancel_reason=body.split(":",1)[1].strip() or "علت توسط مدیریت ثبت نشده است"
        if body not in status_map:
            await m.reply("برای تغییر وضعیت، یکی از این عبارت‌ها را Reply کنید: «در حال انجام»، «تکمیل» یا «لغو: علت لغو»."); return
        order=db.set_order_status(link["ref_id"],status_map[body],cancel_reason)
        if not order: await m.reply("سفارش پیدا نشد."); return
        try: await bot.send_message(order["user_id"],f"وضعیت سفارش {order['order_no']} به‌روزرسانی شد: {body}.")
        except Exception: pass
        await m.reply("وضعیت سفارش تغییر کرد و به مشتری اطلاع داده شد.")
        db.audit(m.from_user.id,"order_status_changed","order",order["order_no"],{"status":status_map[body]})
        return
    # For support and follow-up messages, any text reply is sent to the customer.
    if not body:
        await m.reply("متن پاسخ خالی است."); return
    try: await bot.send_message(link["user_id"],f"<b>پاسخ کارشناسان Boostly Ads</b>\n{esc(body)}",parse_mode="HTML")
    except Exception:
        await m.reply("ارسال پاسخ به کاربر ناموفق بود؛ احتمالاً کاربر ربات را Start نکرده است."); return
    await m.reply("پاسخ برای مشتری ارسال شد.")
    if kind=="support": db.add_ticket_message(int(link["ref_id"]),m.from_user.id,body)

async def hourly_report():
    while True:
        await asyncio.sleep(3600)
        try:
            s=db.stats(); r=db.report_snapshot()
            await send_group(f"<b>گزارش یک‌ساعته Boostly Ads</b>\nکاربران: {s['users']}\nکل سفارش‌ها: {s['orders']}\nسفارش‌های ثبت‌شده در ساعت اخیر: {r['orders']}\nتکمیل‌شده در ساعت اخیر: {r['completed']}\nدرخواست‌های پشتیبانی جدید: {r['tickets']}\nواریزی تأییدشده ساعت اخیر: {r['deposits']} TON\nبرداشت تأییدشده ساعت اخیر: {r['withdrawals']} TON\nپرداخت‌های در انتظار: {s['pending']}")
        except Exception: log.exception("Hourly report failed")

@dp.errors()
async def global_error_handler(event):
    exc=event.exception
    log.error("Unhandled bot error",exc_info=exc)
    short=esc(str(exc))[:1200]
    await send_group(f"<b>خطای سیستمی Boostly Ads</b>\n<code>{short}</code>\nمسئول پیگیری: @ircryptoking")
    return True

@dp.message()
async def fallback(m:Message):
    if m.chat.id==MANAGEMENT_GROUP_ID: return
    await m.answer("لطفاً از دکمه‌های منو استفاده کنید یا /start را بزنید.",reply_markup=home(m.from_user.id))

class BlockedUserMiddleware:
    async def __call__(self, handler, event, data):
        user_obj=getattr(event,"from_user",None)
        if user_obj and not user_obj.is_bot:
            u=db.user(user_obj.id)
            if u and u["blocked"]:
                if hasattr(event,"answer"):
                    await event.answer("دسترسی شما به این ربات مسدود شده است. در صورت اعتراض با مدیریت تماس بگیرید.")
                return None
        return await handler(event,data)

dp.message.outer_middleware(BlockedUserMiddleware())

async def main():
    db.init_db(OWNER_ID,DEVELOPER_ID)
    db.set_setting("management_group_id",str(MANAGEMENT_GROUP_ID))
    await bot.delete_webhook(drop_pending_updates=False)
    asyncio.create_task(hourly_report())
    log.info("Boostly Ads started with long polling")
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__": asyncio.run(main())

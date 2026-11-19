import asyncio, os, tempfile, html, json, logging, traceback, random, uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import quote
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

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("boostly")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_ID = 8292338949
DEVELOPER_ID = 858897695
MANAGEMENT_GROUP_ID = -1003987452469
REPORT_GROUP_ID = -1004330961547
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
    "کمپین": "5823678145286382134", "وضعیت من": "5823612273372959359",
    "لیدربورد": "5823551254772586211", "مدیریت کمپین": "5821179994738529951",
    "مدیریت بونوس": "4990247536863216681", "ایجاد بونوس": "4990247536863216681", "فهرست بونوس‌ها": "6008124493610885197",
    "ایجاد کمپین": "5823539211684287784", "جوین اجباری": "5823442050934116771",
    "افزودن کانال اجباری": "5823513922916848442", "فهرست کمپین‌ها": "5823430231184118947",
    "اعلام نتایج کمپین": "5823664203822536260",
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

def display_channel_link(link):
    link=str(link or "")
    if "t.me/+" in link or "joinchat/" in link:
        return link
    if link.startswith("https://t.me/") or link.startswith("http://t.me/"):
        return "@" + link.split("t.me/",1)[1].strip("/")
    return link

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

async def send_rich_markdown(chat_id, markdown, reply_markup=None, fallback_html=None):
    """Send Bot API Rich Message markdown; fallback to classic HTML message."""
    payload = {"chat_id": chat_id, "rich_message": {"is_rtl": True, "markdown": markdown}}
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
        log.warning("Rich markdown failed; falling back to sendMessage: %s", exc)
        return await bot.send_message(chat_id, fallback_html or esc(markdown), parse_mode="HTML", reply_markup=reply_markup)

async def send_wallet_balance_notice(user_id, amount, added=True):
    sign = "+" if added else "-"
    amount_text = f"{sign}{float(amount):g} TON"
    if added:
        body = (
            f"{custom_emoji('5823338018236272848', '💎')} "
            "با تشکر از اعتماد شما موجودی کیف پول با موفقیت افزایش یافت"
        )
    else:
        body = f"{custom_emoji('5823338018236272848', '💎')} موجودی کیف پول شما کسر شد."
    body += f"\n\n<b>{esc(amount_text)}</b> {custom_emoji('5872872125169146997', '💎')}"
    # Use classic HTML entities so Premium custom emoji IDs are preserved and
    # no literal HTML entities such as &#x20; leak into the visible message.
    return await bot.send_message(user_id, body, parse_mode="HTML")

def custom_emoji(emoji_id, fallback):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

async def send_report(text):
    """Operational event reports go to the dedicated reporting group."""
    try:
        return await bot.send_message(REPORT_GROUP_ID, text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        log.exception("Cannot send event report to reporting group")
        return None

def user_mention(user_id, first_name="", username=""):
    label = first_name or ("@" + username if username else str(user_id))
    return f'<a href="tg://user?id={int(user_id)}">{esc(label)}</a>'

def tonkeeper_url(address, amount, memo):
    # Tonkeeper transfer link: amount is expressed in nanotons (1 TON = 1e9 nanotons).
    nanotons = int((Decimal(str(amount)) * Decimal("1000000000")).to_integral_value())
    return f"https://app.tonkeeper.com/transfer/{quote(str(address), safe='')}?amount={nanotons}&text={quote(str(memo), safe='')}"

def receipt_choice_keyboard(kind):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 ارسال تصویر رسید", callback_data=f"ba:receipt:photo:{kind}")],
        [InlineKeyboardButton(text="رسید ندارم", callback_data=f"ba:receipt:skip:{kind}")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"ba:receipt:back:{kind}")]
    ])

def role_label(uid):
    u=db.user(uid); role=u["role"] if u else "customer"
    return {"owner":"مالک", "developer":"توسعه‌دهنده", "admin":"ادمین", "customer":"کاربر"}.get(role,role)
def home(uid):
    rows=[["تبلیغات گروه", "تبلیغ کانال"], ["تبلیغات گیووای", "ثبت کانال"],
          ["سفارش‌های من", "حساب کاربری"], ["کمپین", "پشتیبانی"], ["راهنما"]]
    if db.is_staff(uid): rows.append(["پنل مدیریت"])
    return kb(rows)
def admin_kb():
    return kb([["درخواست‌های کانال", "همه سفارش‌ها"], ["بررسی پرداخت‌ها", "مدیریت خدمات"],
               ["کیف پول TON", "مدیریت کاربران"], ["مدیریت مدیران", "مدیریت کمپین"],
               ["جوین اجباری", "کانال‌های تأییدشده"], ["مدیریت بونوس", "گزارش کلی"], ["پشتیبان‌گیری"], ["منوی اصلی"]])

class Flow(StatesGroup):
    choose_target=State(); choose_product=State(); choose_package=State(); destination=State(); join_target=State()
    banner=State(); ad_text=State(); notes=State(); confirm=State(); choose_payment=State(); txid=State(); receipt=State()
    channel_admin_confirm=State(); channel_link=State(); support=State(); followup=State()
    wallet_deposit_amount=State(); wallet_deposit_method=State(); wallet_deposit_txid=State(); wallet_deposit_receipt=State()
    add_package_product=State(); add_package_title=State(); add_package_desc=State(); add_package_price=State()
    add_package_currency=State(); add_package_duration=State(); add_product_category=State(); add_product_title=State()
    add_product_kind=State(); add_product_desc=State(); add_wallet_currency=State(); add_wallet_network=State()
    add_wallet_address=State(); add_admin_id=State(); remove_admin_id=State(); order_status=State();
    user_lookup=State(); user_action_amount=State(); user_block_reason=State(); custom_channel_link=State(); giveaway_prize_type=State(); giveaway_prize_value=State(); giveaway_duration=State(); giveaway_channel_count=State(); giveaway_channels=State(); campaign_title=State(); campaign_prize=State(); campaign_winners=State(); campaign_captcha=State(); campaign_winner_ids=State(); campaign_winner_prizes=State(); campaign_winner_confirm=State(); campaign_rank_prizes=State(); referral_captcha=State(); mandatory_chat=State(); mandatory_title=State(); mandatory_url=State(); wallet_address=State(); channel_reject_reason=State(); bonus_title=State(); bonus_amount=State(); bonus_capacity=State(); bonus_start=State(); bonus_end=State()

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

async def start_order(message:Message, state:FSMContext, slug:str):
    with db.conn() as c: cat=c.execute("SELECT * FROM categories WHERE slug=? AND active=1",(slug,)).fetchone()
    if not cat:
        await message.answer("این دسته خدمات فعلاً فعال نیست.", reply_markup=home(message.from_user.id)); return
    targets=db.available_channels(message.from_user.id)
    await state.clear(); await state.update_data(category_id=cat["id"], category_title=cat["title"], category_slug=slug)
    await state.set_state(Flow.choose_target)
    await message.answer("<b>ابتدا فهرست کانال‌ها و گروه‌های موجود را باز کنید.</b>\nپس از مشاهده فهرست، مقصد موردنظر را انتخاب کنید.", parse_mode="HTML", reply_markup=kb([["نمایش لیست کانال‌ها"],["کانال مدنظر من در لیست نیست"],["بازگشت","منوی اصلی"]]))

@dp.message(CommandStart())
async def start(m:Message,state:FSMContext):
    existing = db.user(m.from_user.id)
    db.upsert_user(m.from_user); await state.clear()
    if not existing:
        await send_report(f"{custom_emoji('5823678145286382134','👤')} <b>ثبت‌نام کاربر جدید</b>\nکاربر: {user_mention(m.from_user.id,m.from_user.first_name,m.from_user.username)}\nشناسه: <code>{m.from_user.id}</code>")
    # Bonus deep links are independent of referral links.
    if m.text and "bonus_" in m.text:
        try:
            payload=m.text.split("bonus_",1)[1].split()[0]
            bid,token=payload.split("_",1)
            ok,reason,bonus=db.claim_bonus(int(bid),token,m.from_user.id)
            if ok:
                await m.answer(f"{custom_emoji('5823539211684287784','🎁')} <b>بونوس با موفقیت به کیف پول شما اضافه شد!</b>\nمبلغ: <b>+{float(bonus['amount']):g} TON</b>",parse_mode="HTML",reply_markup=home(m.from_user.id))
                await send_report(f"{custom_emoji('5823539211684287784','🎁')} <b>دریافت بونوس</b>\nکاربر: {user_mention(m.from_user.id,m.from_user.first_name,m.from_user.username)}\nبونوس: <b>{esc(bonus['title'])}</b>\nمبلغ: <b>{float(bonus['amount']):g} TON</b>\nشناسه: <code>{m.from_user.id}</code>")
            else:
                messages={"invalid":"لینک بونوس معتبر نیست.","inactive":"این بونوس غیرفعال شده است.","not_started":"زمان شروع این بونوس هنوز نرسیده است.","expired":"مهلت دریافت این بونوس به پایان رسیده است.","already":"شما قبلاً این بونوس را دریافت کرده‌اید.","exhausted":"ظرفیت دریافت این بونوس تکمیل شده است."}
                await m.answer(messages.get(reason,"امکان دریافت بونوس وجود ندارد."),reply_markup=home(m.from_user.id))
            return
        except Exception:
            await m.answer("لینک بونوس نامعتبر است.",reply_markup=home(m.from_user.id)); return
    if m.text and "ref_" in m.text:
        try:
            inviter=int(m.text.split("ref_",1)[1].split()[0])
            if inviter != m.from_user.id:
                camp=db.active_campaign()
                pending=bool(camp and camp["captcha_required"])
                prior=db.referral_by_invitee(m.from_user.id)
                created=False
                if not prior and not existing:
                    created=db.referral_link_user(inviter,m.from_user.id,not pending)
                    prior=db.referral_by_invitee(m.from_user.id)
                if prior and prior['inviter_id'] != inviter:
                    prior=None
                if created:
                    display=user_mention(m.from_user.id,m.from_user.first_name,m.from_user.username)
                    await bot.send_message(inviter, f"{custom_emoji('5823539211684287784','👤')} کاربر {display} با لینک تو ثبت نام کرد", parse_mode="HTML")
                if prior and not prior['valid'] and pending:
                    a,b=random.randint(2,9),random.randint(1,8); correct=str(a+b)
                    options=list({correct,str(a+b+1),str(max(0,a+b-1)),str(a+b+2)})
                    random.shuffle(options)
                    await state.update_data(ref_inviter=inviter,ref_answer=correct)
                    await state.set_state(Flow.referral_captcha)
                    await m.answer(f"برای ثبت دعوت معتبر، این محاسبه ساده را حل کنید: {a} + {b} = ؟",reply_markup=kb([[x] for x in options]))
                    return
                if created and prior and prior['valid']:
                    await bot.send_message(inviter, f"{custom_emoji('5823678145286382134','🎉')} تبریک میگم به عنوان رفرال تو ثبت شد", parse_mode="HTML")
        except Exception: log.exception("referral attribution failed")
    await m.answer(f"{custom_emoji('5823539211684287784', '👋')} <b>به {BOT_NAME} خوش آمدید</b>\n\n{custom_emoji('5823392736119624565', '🚀')} <b>توسعه چنل و گروهتون را به ما بسپارید</b>\n\n{custom_emoji('5821179994738529951', '💬')} <b>درصورت ایجاد هرگونه مشکل در سفارشات با تیم پشتیبانی ما در ارتباط باشید</b>\n\nاز منوی زیر خدمات موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=home(m.from_user.id))

@dp.message(Command("id"))
async def get_id(m:Message): await m.answer(f"شناسه عددی شما: <code>{m.from_user.id}</code>",parse_mode="HTML")

@dp.message(F.text=="منوی مدیریت")
async def back_admin_menu(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    await state.clear(); await m.answer("پنل مدیریت BoostlyAds:",reply_markup=admin_kb())

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
    await m.answer(f"{custom_emoji('5823551254772586211','📌')} <b>ثبت کانال یا گروه</b>\n\nابتدا اکانت <b>{REQUIRED_ADMIN_ACCOUNT}</b> را در کانال یا گروه خود ادمین کنید.\n\n{custom_emoji('6007944173703929511','✅')} پس از انجام، دکمه «ادمین کردم» را بزنید.",parse_mode="HTML",reply_markup=kb([["ادمین کردم"],["بازگشت","منوی اصلی"]]))

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
        f"<b>درخواست ثبت کانال/گروه</b>\nشناسه درخواست: <code>#{cid}</code>\nکاربر: <code>{m.from_user.id}</code> (@{esc(m.from_user.username or '-')})\nلینک: {esc(link)}\n\nاز دکمه‌های زیر برای بررسی درخواست استفاده کنید.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تأیید کانال",callback_data=f"ba:channel:yes:{cid}"),InlineKeyboardButton(text="رد کانال",callback_data=f"ba:channel:no:{cid}")]]))
    await state.clear()
    await m.answer(f"{custom_emoji('5823338018236272848','✅')} <b>درخواست ثبت شد.</b> پس از بررسی مدیریت، نتیجه از همین ربات به شما اطلاع داده می‌شود.",parse_mode="HTML",reply_markup=home(m.from_user.id))

@dp.message(Flow.choose_target)
async def choose_target(m:Message,state:FSMContext):
    if m.text == "نمایش لیست کانال‌ها":
        targets=db.available_channels(m.from_user.id)
        rows=[]
        for x in targets:
            link=x['invite_link']
            shown=display_channel_link(link)
            rows.append([f"{shown}  #{x['id']}"])
        if not rows:
            await m.answer("هنوز مقصد تأییدشده‌ای در فهرست نیست. می‌توانید کانال مدنظر خود را برای بررسی ارسال کنید.",reply_markup=kb([["کانال مدنظر من در لیست نیست"],["بازگشت","منوی اصلی"]])); return
        await m.answer("<b>فهرست کانال‌ها و گروه‌های تأییدشده</b>\nبرای انتخاب، روی نام مقصد بزنید.",parse_mode="HTML",reply_markup=kb(rows+[["کانال مدنظر من در لیست نیست"],["بازگشت","منوی اصلی"]]))
        return
    if m.text == "کانال مدنظر من در لیست نیست":
        await state.set_state(Flow.custom_channel_link)
        await m.answer("<b>لینک یا آیدی کانال مدنظرتان را ارسال کنید.</b> درخواست شما برای رایزنی به مدیریت ارسال می‌شود.", parse_mode="HTML")
        return
    targets=db.available_channels(m.from_user.id); chosen=None
    for x in targets:
        link=x['invite_link']
        shown=display_channel_link(link)
        label=f"{shown}  #{x['id']}"
        if m.text==label: chosen=x; break
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
        f"<b>درخواست کانال خارج از فهرست</b>\nشناسه: <code>#{rid}</code>\nکاربر: <code>{m.from_user.id}</code>\nلینک: {esc(link)}\n\nوضعیت درخواست را با دکمه‌های زیر مشخص کنید.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تأیید خصوصی",callback_data=f"ba:custom:private:{rid}"),InlineKeyboardButton(text="تأیید عمومی",callback_data=f"ba:custom:public:{rid}"),InlineKeyboardButton(text="رد درخواست",callback_data=f"ba:custom:no:{rid}")]]))
    await state.clear()
    await m.answer(f"{custom_emoji('5823392736119624565','📨')} <b>درخواست شما دریافت شد.</b>\n\n{custom_emoji('6007944173703929511','🔎')} تیم ما کانال موردنظر را بررسی و برای هماهنگی اقدام می‌کند. نتیجه را از همین ربات به شما اطلاع می‌دهیم.",parse_mode="HTML",reply_markup=home(m.from_user.id))

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
    await state.update_data(package_id=chosen["id"],package_title=chosen["title"],price=chosen["price"],currency=chosen["currency"],duration=chosen["duration"],description=chosen["description"],details={})
    if d.get("category_slug") == "giveaway_ads":
        await state.set_state(Flow.giveaway_prize_type)
        await m.answer("<b>نوع جایزه گیووای را انتخاب کنید:</b>",parse_mode="HTML",reply_markup=kb([["گیفت تلگرام","استارز"],["TON"],["بازگشت","منوی اصلی"]]))
        return
    await state.set_state(Flow.destination)
    await m.answer("توضیحات یا لینک موردنیاز سفارش را ارسال کنید:")

@dp.message(Flow.giveaway_prize_type)
async def giveaway_prize_type(m:Message,state:FSMContext):
    prize_type=(m.text or "").strip()
    if prize_type not in ("گیفت تلگرام","استارز","TON"):
        await m.answer("یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کنید."); return
    await state.update_data(giveaway_prize_type=prize_type)
    await state.set_state(Flow.giveaway_prize_value)
    if prize_type=="گیفت تلگرام":
        try:
            owner=await bot.get_chat(OWNER_ID); owner_label=f"@{owner.username}" if owner.username else f"شناسه: {OWNER_ID}"
        except Exception: owner_label=f"شناسه مالک: {OWNER_ID}"
        await m.answer(f"<b>جایزه گیفت</b>\nبرای هماهنگی و ارسال گیفت، حساب مالک: <a href=\"tg://user?id={OWNER_ID}\">{esc(owner_label)}</a>\n\nنام یا لینک گیفت موردنظر را وارد کنید:",parse_mode="HTML")
    elif prize_type=="استارز":
        try:
            owner=await bot.get_chat(OWNER_ID); owner_label=f"@{owner.username}" if owner.username else f"شناسه: {OWNER_ID}"
        except Exception: owner_label=f"شناسه مالک: {OWNER_ID}"
        await m.answer(f"<b>جایزه استارز</b>\nبرای هماهنگی ارسال استارز، حساب مالک: <a href=\"tg://user?id={OWNER_ID}\">{esc(owner_label)}</a>\n\nتعداد استارز را وارد کنید:",parse_mode="HTML")
    else:
        ton_methods=[x for x in db.methods() if x['currency'].upper()=="TON"]
        if ton_methods:
            await m.answer(f"<b>جایزه TON</b>\nآدرس کیف پول دریافت جایزه: <code>{esc(ton_methods[0]['address'])}</code>\n\nمقدار جایزه به TON را وارد کنید:",parse_mode="HTML")
        else:
            await m.answer(f"<b>جایزه TON</b>\nبرای دریافت آدرس کیف پول با <a href=\"tg://user?id={OWNER_ID}\">مالک</a> هماهنگ کنید.\n\nمقدار جایزه به TON را وارد کنید:",parse_mode="HTML")

@dp.message(Flow.giveaway_prize_value)
async def giveaway_prize_value(m:Message,state:FSMContext):
    value=(m.text or "").strip()
    if not value or len(value)>120:
        await m.answer("مقدار یا نام جایزه را به‌صورت معتبر وارد کنید."); return
    d=await state.get_data()
    if d.get('giveaway_prize_type') in ("استارز","TON"):
        try:
            number=float(value.replace(',','.'))
            if number<=0 or (d.get('giveaway_prize_type')=="استارز" and not number.is_integer()): raise ValueError()
        except ValueError:
            await m.answer("برای استارز تعداد صحیح و برای TON مقدار عددی بیشتر از صفر وارد کنید."); return
    await state.update_data(giveaway_prize_value=value)
    await state.set_state(Flow.giveaway_duration)
    await m.answer("<b>مدت‌زمان اجرای گیووای را وارد کنید.</b>\nمثلاً: ۳ روز یا ۷ روز",parse_mode="HTML")

@dp.message(Flow.giveaway_duration)
async def giveaway_duration(m:Message,state:FSMContext):
    duration=(m.text or "").strip()
    if not duration or len(duration)>40:
        await m.answer("مدت‌زمان را به‌صورت معتبر وارد کنید."); return
    await state.update_data(giveaway_duration=duration)
    await state.set_state(Flow.giveaway_channel_count)
    await m.answer("<b>گیووای در چند کانال برگزار شود؟</b>\nحداکثر ۴ کانال مجاز است. هزینه اضافه هر کانال: ۰٫۵ TON.",parse_mode="HTML",reply_markup=kb([["۱ کانال","۲ کانال"],["۳ کانال","۴ کانال"],["بازگشت","منوی اصلی"]]))

@dp.message(Flow.giveaway_channel_count)
async def giveaway_channel_count(m:Message,state:FSMContext):
    counts={"۱ کانال":1,"۲ کانال":2,"۳ کانال":3,"۴ کانال":4}
    count=counts.get((m.text or "").strip())
    if not count:
        await m.answer("تعداد کانال را از گزینه‌های ۱ تا ۴ انتخاب کنید."); return
    targets=db.approved_channels()
    if len(targets)<count:
        await m.answer(f"در حال حاضر فقط {len(targets)} کانال یا گروه تأییدشده وجود دارد. تعداد کمتری انتخاب کنید."); return
    d=await state.get_data()
    first=int(d.get('target_id') or 0)
    selected=[first] if first else []
    await state.update_data(giveaway_channel_count=count,giveaway_selected_channels=selected)
    await state.set_state(Flow.giveaway_channels)
    rows=[]
    for x in targets:
        link=x['invite_link']; shown=display_channel_link(link)
        mark='✓ ' if x['id'] in selected else ''
        rows.append([f"{mark}{shown}  #{x['id']}"])
    rows.append(["پایان انتخاب کانال‌ها"]); rows.append(["بازگشت","منوی اصلی"])
    await m.answer(f"<b>کانال‌های موردنظر را انتخاب کنید.</b>\nتعداد انتخاب‌شده: {len(selected)} از {count}\nبرای انتخاب یا برداشتن انتخاب، روی نام کانال بزنید.",parse_mode="HTML",reply_markup=kb(rows))

@dp.message(Flow.giveaway_channels)
async def giveaway_channels(m:Message,state:FSMContext):
    d=await state.get_data(); targets=db.approved_channels(); selected=list(d.get('giveaway_selected_channels',[])); count=int(d.get('giveaway_channel_count',1))
    if m.text=="پایان انتخاب کانال‌ها":
        if len(selected)!=count:
            await m.answer(f"باید دقیقاً {count} کانال انتخاب کنید. اکنون {len(selected)} کانال انتخاب شده است."); return
        lookup={x['id']:x for x in targets}
        selected_rows=[lookup[x] for x in selected if x in lookup]
        base=float(str(d['price']).replace(',','.')); final=base+(0.5*count)
        details={"target_id":selected_rows[0]['id'],"target_link":selected_rows[0]['invite_link'],"giveaway":True,
                 "prize_type":d['giveaway_prize_type'],"prize_value":d['giveaway_prize_value'],
                 "giveaway_duration":d['giveaway_duration'],"giveaway_channels":[{"id":x['id'],"link":x['invite_link']} for x in selected_rows],
                 "channel_extra_ton":0.5*count,"base_price_ton":base,"destination":"، ".join(x['invite_link'] for x in selected_rows)}
        await state.update_data(price=f"{final:.3f}",currency="TON",details=details)
        rows=[[x['invite_link'],f"#{x['id']}"] for x in selected_rows]
        preview=(f"<b>پیش‌نمایش گیووای</b>\nنوع جایزه: {esc(d['giveaway_prize_type'])}\nمقدار/نام جایزه: {esc(d['giveaway_prize_value'])}\nمدت‌زمان: {esc(d['giveaway_duration'])}\nتعداد کانال: {count}\nهزینه کانال‌ها: {0.5*count:.3f} TON\nمبلغ پایه: {base:.3f} TON\n<b>مبلغ نهایی: {final:.3f} TON</b>\n\nسفارش را ثبت می‌کنید؟")
        await state.set_state(Flow.confirm)
        await m.answer(preview,parse_mode="HTML",reply_markup=kb([["ثبت سفارش"],["منوی اصلی"]]))
        return
    chosen=None
    for x in targets:
        link=x['invite_link']; shown=display_channel_link(link)
        label=f"{'✓ ' if x['id'] in selected else ''}{shown}  #{x['id']}"
        # Accept both marked and unmarked button labels for reliable toggling.
        if m.text in (label, f"{shown}  #{x['id']}", f"✓ {shown}  #{x['id']}"):
            chosen=x; break
    if not chosen:
        await m.answer("یک کانال از فهرست را انتخاب کنید یا «پایان انتخاب کانال‌ها» را بزنید."); return
    if chosen['id'] in selected: selected.remove(chosen['id'])
    elif len(selected)<count: selected.append(chosen['id'])
    else: await m.answer(f"حداکثر {count} کانال می‌توانید انتخاب کنید."); return
    await state.update_data(giveaway_selected_channels=selected)
    rows=[]
    for x in targets:
        link=x['invite_link']; shown=display_channel_link(link)
        rows.append([f"{'✓ ' if x['id'] in selected else ''}{shown}  #{x['id']}"])
    rows += [["پایان انتخاب کانال‌ها"],["بازگشت","منوی اصلی"]]
    await m.answer(f"انتخاب ثبت شد: {len(selected)} از {count}",reply_markup=kb(rows))

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
    details={k:d.get(k,"") for k in ("destination","target_id","target_link","join_target","banner_file_id","ad_text","notes")}
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
    await send_report(f"{custom_emoji('6007944173703929511','🛍️')} <b>سفارش جدید ثبت شد</b>\nکاربر: {user_mention(m.from_user.id,m.from_user.first_name,m.from_user.username)}\nخدمت: <b>{esc(order['product_title'])}</b>\nپکیج: <b>{esc(order['package_title'])}</b>\nمبلغ: <b>{esc(order['price'])} {esc(order['currency'])}</b>\nشماره سفارش: <code>{esc(order['order_no'])}</code>")
    giveaway_summary=""
    if d.get('details',{}).get('giveaway'):
        gd=d['details']
        giveaway_summary=(f"\n<b>نوع جایزه:</b> {esc(gd.get('prize_type'))}\n<b>مقدار/نام جایزه:</b> {esc(gd.get('prize_value'))}\n<b>مدت:</b> {esc(gd.get('giveaway_duration'))}\n<b>کانال‌ها:</b> {esc(gd.get('destination'))}\n<b>هزینه اضافه کانال‌ها:</b> {float(gd.get('channel_extra_ton',0)):.3f} TON")
    await group_notice("order",order["order_no"],m.from_user.id,
        f"<b>سفارش جدید</b>\nشناسه: <code>{order['order_no']}</code>\nکاربر: <code>{m.from_user.id}</code>\nخدمت: {esc(order['product_title'])}\nمبلغ: {esc(order['price'])} {esc(order['currency'])}\nمقصد: {esc(d['details'].get('target_link','-'))}{giveaway_summary}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="در حال انجام",callback_data=f"ba:order:doing:{order['order_no']}"),InlineKeyboardButton(text="تکمیل",callback_data=f"ba:order:done:{order['order_no']}"),InlineKeyboardButton(text="لغو",callback_data=f"ba:order:cancel:{order['order_no']}")]]))
    methods=[x for x in db.methods() if x['currency'].upper() == "TON" and x['network'].lower().replace(" ","") in ("tonmainnet","ton")]
    if not methods:
        await state.clear(); await m.answer(f"سفارش <b>{order['order_no']}</b> ثبت شد. روش پرداخت TON هنوز تنظیم نشده است؛ برای هماهنگی با <a href=\"tg://user?id={OWNER_ID}\">مالک</a> ارتباط بگیرید.",parse_mode="HTML",reply_markup=home(m.from_user.id)); return
    await state.update_data(order_no=order["order_no"],order_id=order["id"]); await state.set_state(Flow.choose_payment)
    await m.answer(f"سفارش <b>{order['order_no']}</b> ثبت شد.\nروش پرداخت را انتخاب کنید:",parse_mode="HTML",
        reply_markup=kb([[f"{x['currency']} | {x['network']}"] for x in methods]+[["منوی اصلی"]]))

@dp.message(Flow.choose_payment)
async def payment_chosen(m:Message,state:FSMContext):
    methods=db.methods(); chosen=next((x for x in methods if m.text==f"{x['currency']} | {x['network']}"),None)
    if not chosen: await m.answer("یکی از روش‌های پرداخت را انتخاب کنید."); return
    d=await state.get_data(); memo=f"BA{uuid.uuid4().hex[:10].upper()}"; await state.update_data(method_id=chosen["id"],payment_memo=memo,payment_deadline=(datetime.now().astimezone().strftime('%H:%M'))); await state.set_state(Flow.txid)
    invoice = (
        f"{custom_emoji('5769403330761593044','🧾')} <b>فاکتور پرداخت سفارش {esc(d['order_no'])}</b>\n"
        f"{custom_emoji('5872872125169146997','💎')} عنوان: پرداخت سفارش BoostlyAds\n"
        f"{custom_emoji('5447410659077661506','🌐')} شبکه: TON Mainnet\n"
        f"{custom_emoji('5873230707693723886','📥')} آدرس دریافت TON:\n<code>{esc(chosen['address'])}</code>\n"
        f"{custom_emoji('6008341333624758856','💰')} مبلغ دقیق: <b>{esc(d['price'])} TON</b>\n"
        f"{custom_emoji('5933929504803134783','📝')} Memo / Comment: <code>{memo}</code>\n"
        f"{custom_emoji('5933850636318678448','⏳')} مهلت: ۳۰ دقیقه\n\n"
        f"{custom_emoji('6032666885927999842','⚠️')} Memo را دقیقاً وارد کنید. پس از پرداخت، TXID را ارسال کنید؛ تأیید نهایی دستی است."
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 پرداخت با Tonkeeper", url=tonkeeper_url(chosen['address'], d['price'], memo))]])
    await m.answer(invoice, parse_mode="HTML", reply_markup=markup)
@dp.message(Flow.txid)
async def txid(m:Message,state:FSMContext):
    if not m.text or len(m.text.strip())<8:
        await m.answer("لطفاً TXID معتبر را ارسال کنید.")
        return
    await state.update_data(txid=m.text.strip())
    await state.set_state(Flow.receipt)
    await m.answer("اگر رسید پرداخت دارید، دکمه ارسال تصویر رسید را بزنید؛ در غیر این صورت «رسید ندارم» را انتخاب کنید.", reply_markup=receipt_choice_keyboard("order"))

async def finalize_order_payment(user_id, data, fid=""):
    db.order_payment(data["order_id"],data["method_id"],data["txid"],fid,data.get("payment_memo",""))
    db.audit(user_id,"payment_submitted","order",data["order_no"])
    gmsg=await group_notice("payment",data["order_no"],user_id,
        f"<b>پرداخت برای بررسی</b>\nسفارش: <code>{data['order_no']}</code>\nکاربر: <code>{user_id}</code>\nمبلغ: {esc(data.get('price'))} TON\nMemo: <code>{esc(data.get('payment_memo',''))}</code>\nTXID: <code>{esc(data['txid'])}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تأیید پرداخت",callback_data=f"ba:payment:yes:{data['order_no']}"),InlineKeyboardButton(text="رد پرداخت",callback_data=f"ba:payment:no:{data['order_no']}")]]))
    if fid and gmsg:
        try: await bot.send_photo(MANAGEMENT_GROUP_ID,fid,caption=f"رسید پرداخت سفارش {data['order_no']}",reply_to_message_id=gmsg.message_id)
        except Exception: log.exception("receipt forward failed")

@dp.message(Flow.receipt)
async def receipt(m:Message,state:FSMContext):
    if not m.photo:
        await m.answer("برای ثبت رسید، ابتدا دکمه «ارسال تصویر رسید» را بزنید یا گزینه «رسید ندارم» را انتخاب کنید.", reply_markup=receipt_choice_keyboard("order"))
        return
    d=await state.get_data()
    await finalize_order_payment(m.from_user.id,d,m.photo[-1].file_id)
    await state.clear()
    await m.answer("رسید و اطلاعات پرداخت ثبت شد و پس از بررسی دستی نتیجه اعلام می‌شود.",reply_markup=home(m.from_user.id))

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
    await m.answer("پرداخت فقط با TON روی شبکه TON Mainnet انجام می‌شود.",parse_mode="HTML",reply_markup=kb([["پرداخت با TON"],["بازگشت"]]))
@dp.message(Flow.wallet_deposit_method)
async def wallet_deposit_method(m:Message,state:FSMContext):
    d=await state.get_data()
    if d.get("deposit_ton_methods"):
        methods=[x for x in db.methods() if x['id'] in d["deposit_ton_methods"]]
        chosen=next((x for x in methods if m.text==f"{x['currency']} | {x['network']}"),None)
        if chosen:
            memo=f"WAL{uuid.uuid4().hex[:10].upper()}"
            await state.update_data(deposit_method=chosen["id"],deposit_memo=memo); await state.set_state(Flow.wallet_deposit_txid)
            invoice = (
                f"{custom_emoji('5769403330761593044','🧾')} <b>فاکتور شارژ کیف پول</b>\n"
                f"{custom_emoji('5872872125169146997','💎')} عنوان: شارژ از طریق گرام (تون)\n"
                f"{custom_emoji('5873230707693723886','📥')} آدرس دریافت TON:\n<code>{esc(chosen['address'])}</code>\n"
                f"{custom_emoji('6008341333624758856','💰')} مبلغ دقیق: <b>{d['deposit_amount']} TON</b>\n"
                f"{custom_emoji('5447410659077661506','🌐')} شبکه: TON Mainnet\n"
                f"{custom_emoji('5933929504803134783','📝')} Memo / Comment: <code>{memo}</code>\n"
                f"{custom_emoji('5933850636318678448','⏳')} مهلت: ۳۰ دقیقه\n\n"
                f"{custom_emoji('6032666885927999842','⚠️')} Memo را دقیقاً وارد کنید. TXID را پس از پرداخت ارسال کنید؛ تأیید شارژ دستی است."
            )
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 پرداخت با Tonkeeper", url=tonkeeper_url(chosen['address'], d['deposit_amount'], memo))]])
            await m.answer(invoice, parse_mode="HTML", reply_markup=markup)
            return
    if m.text not in ("پرداخت با TON", "پرداخت با تون (گرام)"):
        await m.answer("یکی از دو روش نمایش‌داده‌شده را انتخاب کنید."); return
    methods=[x for x in db.methods() if x['currency'].upper() == "TON" and x['network'].lower().replace(" ","") in ("tonmainnet","ton")]
    if not methods:
        await state.clear(); await m.answer(f"روش پرداخت TON هنوز تنظیم نشده است. برای هماهنگی با <a href=\"tg://user?id={OWNER_ID}\">مالک</a> ارتباط بگیرید.",parse_mode="HTML",reply_markup=home(m.from_user.id)); return
    await state.update_data(deposit_ton_methods=[x['id'] for x in methods]); await state.set_state(Flow.wallet_deposit_method)
    await m.answer("<b>شبکه پرداخت TON را انتخاب کنید:</b>",parse_mode="HTML",reply_markup=kb([[f"{x['currency']} | {x['network']}"] for x in methods]+[["بازگشت"]]))
@dp.message(Flow.wallet_deposit_txid)
async def wallet_deposit_txid(m:Message,state:FSMContext):
    if not m.text or len(m.text.strip())<8:
        await m.answer("TXID معتبر ارسال کنید.")
        return
    await state.update_data(deposit_txid=m.text.strip())
    await state.set_state(Flow.wallet_deposit_receipt)
    await m.answer("اگر رسید پرداخت دارید، دکمه ارسال تصویر رسید را بزنید؛ در غیر این صورت «رسید ندارم» را انتخاب کنید.", reply_markup=receipt_choice_keyboard("wallet"))

async def finalize_wallet_deposit(user_id, data, fid=""):
    entry=db.add_wallet_entry(user_id,data["deposit_amount"],"TON","deposit","pending",f"TXID:{data['deposit_txid']} MEMO:{data.get('deposit_memo','')} method:{data['deposit_method']} receipt:{fid}")
    gmsg=await group_notice("wallet",entry,user_id,f"<b>درخواست شارژ کیف پول</b>\nشناسه: #{entry}\nکاربر: <code>{user_id}</code>\nمبلغ: {data['deposit_amount']} TON\nTXID: <code>{esc(data['deposit_txid'])}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تأیید شارژ",callback_data=f"ba:wallet:yes:{entry}"),InlineKeyboardButton(text="رد شارژ",callback_data=f"ba:wallet:no:{entry}")]]))
    if fid and gmsg:
        try: await bot.send_photo(MANAGEMENT_GROUP_ID,fid,caption=f"رسید شارژ کیف پول #{entry}",reply_to_message_id=gmsg.message_id)
        except Exception: log.exception("wallet receipt forward failed")

@dp.message(Flow.wallet_deposit_receipt)
async def wallet_deposit_receipt(m:Message,state:FSMContext):
    if not m.photo:
        await m.answer("برای ثبت رسید، ابتدا دکمه «ارسال تصویر رسید» را بزنید یا گزینه «رسید ندارم» را انتخاب کنید.", reply_markup=receipt_choice_keyboard("wallet"))
        return
    d=await state.get_data()
    await finalize_wallet_deposit(m.from_user.id,d,m.photo[-1].file_id)
    await state.clear()
    await m.answer("درخواست شارژ ثبت شد و پس از بررسی دستی به موجودی اضافه می‌شود.",reply_markup=home(m.from_user.id))

@dp.callback_query(F.data.startswith("ba:receipt:"))
async def receipt_choice_callback(cq:CallbackQuery,state:FSMContext):
    parts=cq.data.split(":")
    action,kind=parts[2],parts[3]
    expected_state = Flow.receipt if kind=="order" else Flow.wallet_deposit_receipt
    if await state.get_state() != expected_state.state:
        await cq.answer("این مرحله منقضی شده است؛ دوباره فرایند پرداخت را آغاز کنید.",show_alert=True)
        return
    data=await state.get_data()
    if action=="back":
        await state.set_state(Flow.txid if kind=="order" else Flow.wallet_deposit_txid)
        await cq.answer()
        await cq.message.answer("لطفاً TXID تراکنش را دوباره ارسال کنید.")
        return
    if action=="photo":
        await cq.answer()
        await cq.message.answer("حالا تصویر رسید پرداخت را به‌صورت عکس ارسال کنید.")
        return
    if action=="skip":
        if kind=="order":
            await finalize_order_payment(cq.from_user.id,data,"")
            confirmation="اطلاعات پرداخت ثبت شد. پس از بررسی دستی نتیجه اعلام می‌شود."
        else:
            await finalize_wallet_deposit(cq.from_user.id,data,"")
            confirmation="درخواست شارژ ثبت شد و پس از بررسی دستی به موجودی اضافه می‌شود."
        await state.clear()
        await cq.message.answer(confirmation,reply_markup=home(cq.from_user.id))
        await cq.answer("ثبت شد.")
@dp.message(F.text=="راهنما")
async def help_user(m:Message):
    # Original Premium guide styling and custom emoji IDs supplied by the owner.
    guide = (
        f"{custom_emoji('5456269518751948393', '📣')} برای شروع، یکی از دسته‌بندی‌های تبلیغاتی را انتخاب کنید.\n\n"
        f"{custom_emoji('5456250195694080809', '🎯')} سپس مقصد تبلیغ را از فهرست کانال‌های تأییدشده انتخاب کنید. "
        f"{custom_emoji('5456382802809347478', '➕')} اگر مقصد شما در فهرست نیست، درخواست ثبت کانال یا گروه خود را ارسال کنید.\n\n"
        f"{custom_emoji('5456503547224939436', '🛍️')} در مرحله بعد، خدمت و پکیج موردنظرتان را انتخاب و سفارش خود را ثبت کنید.\n\n"
        f"{custom_emoji('5456503547224939436', '💳')} پرداخت را انجام دهید؛ پس از تأیید پرداخت توسط تیم BoostlyAds، اجرای تبلیغ شما آغاز می‌شود.\n\n"
        f"امیدواریم با {custom_emoji('5823664203822536260', '💎')} BoostlyAds به نتیجه‌ای عالی در تبلیغات خود برسید ❤️. "
        f"اگر در هر مرحله به راهنمایی نیاز داشتید، از طریق پشتیبانی با ما در ارتباط باشید {custom_emoji('5823551254772586211', '🎧')}."
    )
    await bot.send_message(m.chat.id, guide, parse_mode="HTML", reply_markup=home(m.from_user.id))
@dp.message(F.text=="پشتیبانی")
async def support_start(m:Message,state:FSMContext):
    await state.clear()
    markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ارتباط با پشتیبانی",url="https://t.me/Parsa_0102")]])
    await m.answer("برای ارتباط مستقیم با پشتیبانی BoostlyAds از دکمه زیر استفاده کنید.",reply_markup=markup)

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
        await m.answer(f"درخواست #{x['id']}\nکاربر: {x['user_id']}\nلینک: {esc(x['invite_link'])}\nوضعیت: در انتظار بررسی\nبرای تأیید یا رد، پیام مربوط به همین درخواست را در گروه مدیریت پیدا کنید و از دکمه‌های آن استفاده کنید.",parse_mode="HTML")

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
    await bot.send_message(row["user_id"],f"شارژ کیف پول شما به مبلغ {row['amount']} {row['currency']} تأیید شد.")
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
    await m.answer("دسته محصول جدید را انتخاب کنید:",reply_markup=kb([[x["title"]] for x in cats]+[["لغو","منوی مدیریت"]]))

@dp.message(Flow.add_product_category)
async def product_category(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    if m.text in ("لغو","منوی مدیریت"): await state.clear(); await m.answer("لغو شد.",reply_markup=admin_kb()); return
    with db.conn() as c: cat=c.execute("SELECT * FROM categories WHERE title=? AND active=1",(m.text,)).fetchone()
    if not cat: await m.answer("یکی از دسته‌های نمایش‌داده‌شده را انتخاب کنید."); return
    await state.update_data(new_category_id=cat["id"]); await state.set_state(Flow.add_product_title); await m.answer("نام خدمت جدید را وارد کنید:")

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
    with db.conn() as c: ps=c.execute("SELECT p.id,p.title,c.title category FROM products p JOIN categories c ON c.id=p.category_id WHERE p.active=1 ORDER BY c.id,p.id").fetchall()
    await state.set_state(Flow.add_package_product)
    await state.update_data(package_products={f"{p['category']} — {p['title']}":p['id'] for p in ps})
    await m.answer("خدمت موردنظر برای پکیج را انتخاب کنید:",reply_markup=kb([[f"{p['category']} — {p['title']}"] for p in ps]+[["لغو","منوی مدیریت"]]))
@dp.message(Flow.add_package_product)
async def pack_product(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    d=await state.get_data()
    if m.text in ("لغو","منوی مدیریت"): await state.clear(); await m.answer("لغو شد.",reply_markup=admin_kb()); return
    pid=d.get("package_products",{}).get(m.text)
    if not pid: await m.answer("یکی از خدمات نمایش‌داده‌شده را انتخاب کنید."); return
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

@dp.message(F.text.in_({"روش‌های پرداخت","کیف پول TON"}))
async def wallet_admin(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    current=db.methods()
    addr=current[0]["address"] if current else "تنظیم نشده"
    await state.clear()
    await m.answer(f"<b>مدیریت کیف پول TON</b>\nشبکه: TON Mainnet\nآدرس فعلی: <code>{esc(addr)}</code>",parse_mode="HTML",reply_markup=kb([["ثبت/تغییر آدرس TON"],["حذف آدرس TON"],["منوی مدیریت"]]))

@dp.message(F.text=="ثبت/تغییر آدرس TON")
async def wallet_address_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.set_state(Flow.wallet_address)
    await m.answer("آدرس دریافت TON روی شبکه TON Mainnet را ارسال کنید:",reply_markup=kb([["بازگشت","منوی مدیریت"]]))

@dp.message(Flow.wallet_address)
async def wallet_address_save(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    address=(m.text or "").strip()
    if not address or len(address)<20 or len(address)>128:
        await m.answer("آدرس TON معتبر ارسال کنید."); return
    mid=db.add_method("TON","TON Mainnet",address)
    db.audit(m.from_user.id,"ton_wallet_changed","payment_method",mid)
    await state.clear(); await m.answer("آدرس کیف پول TON ذخیره شد.",reply_markup=admin_kb())

@dp.message(F.text=="حذف آدرس TON")
async def wallet_address_remove(m:Message):
    if not db.is_privileged(m.from_user.id): return
    db.remove_method(); db.audit(m.from_user.id,"ton_wallet_removed","payment_method")
    await m.answer("آدرس دریافت TON غیرفعال شد.",reply_markup=admin_kb())

@dp.message(F.text=="تیکت‌های پشتیبانی")
async def admin_tickets(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.tickets()
    if not rows: await m.answer("درخواست پشتیبانی بازی وجود ندارد."); return
    for t in rows: await m.answer(f"پیام پشتیبانی | کاربر {t['user_id']}\nموضوع: {t['subject']}\nبرای پاسخ به پیام مربوط در گروه مدیریت Reply کنید.")

@dp.message(F.text=="مدیریت کمپین")
async def campaign_admin(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.clear()
    await m.answer("مدیریت کمپین:",reply_markup=kb([["ایجاد کمپین"],["فهرست کمپین‌ها"],["اعلام نتایج کمپین"],["منوی مدیریت"]]))

@dp.message(F.text=="ایجاد کمپین")
async def campaign_create_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.set_state(Flow.campaign_title); await m.answer("عنوان کمپین را ارسال کنید:",reply_markup=kb([["لغو","منوی مدیریت"]]))

@dp.message(Flow.campaign_title)
async def campaign_title_save(m:Message,state:FSMContext):
    if m.text in ("لغو","منوی مدیریت"): await state.clear(); await m.answer("لغو شد.",reply_markup=admin_kb()); return
    await state.update_data(c_title=(m.text or "")[:100]); await state.set_state(Flow.campaign_prize); await m.answer("جایزه کلی کمپین را مشخص کنید:")

@dp.message(Flow.campaign_prize)
async def campaign_prize_save(m:Message,state:FSMContext):
    await state.update_data(c_prize=(m.text or "")[:200]); await state.set_state(Flow.campaign_winners); await m.answer("تعداد برندگان را به عدد وارد کنید:")

@dp.message(Flow.campaign_winners)
async def campaign_winners_save(m:Message,state:FSMContext):
    try: n=int(m.text); assert 1<=n<=100
    except: await m.answer("عدد بین ۱ تا ۱۰۰ وارد کنید."); return
    await state.update_data(c_winners=n,c_rank_index=1,c_rank_prizes=[]); await state.set_state(Flow.campaign_rank_prizes)
    rank_icons=['5440539497383087970','5447203607294265305','5453902265922376865']
    await m.answer(f"{custom_emoji(rank_icons[0],'🥇')} <b>جایزه رتبه اول لیدربورد را مشخص کنید:</b>",parse_mode="HTML")

@dp.message(Flow.campaign_rank_prizes)
async def campaign_rank_prize_input(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    prize=(m.text or '').strip()
    if not prize: await m.answer("جایزه این رتبه را وارد کنید."); return
    d=await state.get_data(); prizes=list(d.get('c_rank_prizes',[])); prizes.append(prize[:200])
    rank=int(d['c_rank_index']); total=int(d['c_winners'])
    if rank<total:
        rank+=1; await state.update_data(c_rank_index=rank,c_rank_prizes=prizes)
        rank_icons=['5440539497383087970','5447203607294265305','5453902265922376865']
        icon=rank_icons[rank-1] if rank<=3 else '6007844603477106253'
        await m.answer(f"{custom_emoji(icon,'🏆')} <b>جایزه رتبه {rank} لیدربورد را مشخص کنید:</b>",parse_mode="HTML"); return
    await state.update_data(c_rank_prizes=prizes); await state.set_state(Flow.campaign_captcha)
    preview='\n'.join(f"رتبه {i+1}: <b>{esc(value)}</b>" for i,value in enumerate(prizes))
    await m.answer("<b>جوایز رتبه‌های کمپین</b>\n"+preview+"\n\nکپچا برای معتبر شدن دعوت‌ها اجباری باشد؟",parse_mode="HTML",reply_markup=kb([["کپچا اجباری","کپچا غیراجباری"],["لغو"]]))

@dp.message(Flow.campaign_captcha)
async def campaign_captcha_save(m:Message,state:FSMContext):
    if m.text not in ("کپچا اجباری","کپچا غیراجباری"): await m.answer("یکی از دکمه‌ها را انتخاب کنید."); return
    d=await state.get_data(); cid=db.create_campaign(d['c_title'],d['c_prize'],d['c_winners'],m.text=="کپچا اجباری",d.get('c_rank_prizes',[]))
    await state.clear(); await m.answer(f"کمپین #{cid} ساخته شد. جوایز هر رتبه ذخیره شدند؛ برای شروع از فهرست کمپین‌ها فعالش کنید.",reply_markup=admin_kb())

@dp.message(F.text=="اعلام نتایج کمپین")
async def campaign_results_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    camp=db.active_campaign()
    if not camp: await m.answer("کمپین فعالی برای اعلام نتایج وجود ندارد.",reply_markup=admin_kb()); return
    board=db.referral_leaderboard(camp["winners_count"])
    if len(board)<camp["winners_count"]: await m.answer("تعداد دعوت‌کنندگان معتبر از تعداد برندگان کمتر است.",reply_markup=admin_kb()); return
    configured=db.campaign_rank_prizes(camp['id'])
    if len(configured)>=camp['winners_count']:
        winner_prizes=[(board[i]['inviter_id'],configured[i]['prize']) for i in range(camp['winners_count'])]
        preview=[]; rank_icons=['5440539497383087970','5447203607294265305','5453902265922376865']
        for i,(uid,prize) in enumerate(winner_prizes):
            icon=rank_icons[i] if i<3 else '6007844603477106253'
            preview.append(f"{custom_emoji(icon,'🏆')} <b>رتبه {i+1}</b> — کاربر <code>{uid}</code> — جایزه: <b>{esc(prize)}</b>")
        await state.update_data(result_campaign=camp['id'],winner_prizes=winner_prizes)
        await state.set_state(Flow.campaign_winner_confirm)
        await m.answer(f"{custom_emoji('6007944173703929511','🏆')} <b>پیش‌نمایش نتایج کمپین</b>\n"+'\n'.join(preview)+"\n\nنتایج ثبت شوند؟",parse_mode="HTML",reply_markup=kb([["تأیید نتایج کمپین","لغو نتایج کمپین"]]))
        return
    await state.update_data(result_campaign=camp["id"],winner_rows=[(r["inviter_id"],r["username"],r["first_name"],r["n"]) for r in board],winner_index=0,winner_prizes=[])
    await state.set_state(Flow.campaign_winner_prizes)
    r=board[0]
    await m.answer(f"{custom_emoji('5440539497383087970','🥇')} <b>جایزه رتبه اول</b>\nکاربر: {r['inviter_id']} (@{r['username'] or '-'})\nدعوت معتبر: {r['n']}\n\nجایزه این رتبه را وارد کنید:",parse_mode="HTML")

@dp.message(Flow.campaign_winner_prizes)
async def campaign_winner_prize_input(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    d=await state.get_data(); idx=d["winner_index"]; rows=d["winner_rows"]; prizes=d["winner_prizes"]
    prizes.append((rows[idx][0],(m.text or "")[:200]))
    idx+=1
    if idx<len(rows):
        await state.update_data(winner_index=idx,winner_prizes=prizes)
        r=rows[idx]; rank_icon=['5440539497383087970','5447203607294265305','5453902265922376865'][idx] if idx<3 else '6007844603477106253'
        await m.answer(f"{custom_emoji(rank_icon,'🏆')} <b>جایزه رتبه {idx+1}</b>\nکاربر: {r[0]} (@{r[1] or '-'})\nدعوت معتبر: {r[3]}\n\nجایزه این رتبه را وارد کنید:",parse_mode="HTML"); return
    rank_icons=['5440539497383087970','5447203607294265305','5453902265922376865']
    preview="\n".join(f"{custom_emoji(rank_icons[i] if i<3 else '6007844603477106253','🏆')} <b>رتبه {i+1}</b> — کاربر {uid} — جایزه: <b>{esc(prize)}</b>" for i,(uid,prize) in enumerate(prizes))
    await state.update_data(winner_prizes=prizes); await state.set_state(Flow.campaign_winner_confirm)
    await m.answer(f"{custom_emoji('6007944173703929511','🏆')} <b>پیش‌نمایش نهایی برندگان</b>\n"+preview+"\n\nنتایج ثبت شوند؟",parse_mode="HTML",reply_markup=kb([["تأیید نتایج کمپین","لغو نتایج کمپین"]]))

@dp.message(Flow.campaign_winner_confirm)
async def campaign_winner_confirm(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    if m.text!="تأیید نتایج کمپین":
        await state.clear(); await m.answer("اعلام نتایج لغو شد.",reply_markup=admin_kb()); return
    d=await state.get_data(); rows=[]
    for rank,(uid,prize) in enumerate(d["winner_prizes"],1): rows.append((rank,uid,prize))
    db.campaign_set_winners(d["result_campaign"],rows)
    await state.clear(); await m.answer("نتایج کمپین ثبت شد و کمپین پایان یافت.",reply_markup=admin_kb())
    result_lines="\n".join(f"رتبه {rank}: کاربر <code>{uid}</code> — جایزه <b>{esc(prize)}</b>" for rank,uid,prize in rows)
    await send_report(f"{custom_emoji('6007944173703929511','🏆')} <b>نتیجه نهایی کمپین #{d['result_campaign']}</b>\n{result_lines}")
    for rank,uid,prize in rows:
        try:
            rank_icon=['5440539497383087970','5447203607294265305','5453902265922376865'][rank-1] if rank<=3 else '6007844603477106253'
            await bot.send_message(uid,f"{custom_emoji(rank_icon,'🏆')} <b>تبریک! شما رتبه {rank} کمپین را کسب کردید.</b>\n{custom_emoji('6007844603477106253','🎁')} جایزه شما: <b>{esc(prize)}</b>",parse_mode="HTML")
        except Exception: log.exception("campaign winner notification failed")

@dp.message(F.text=="فهرست کمپین‌ها")
async def campaign_list_admin(m:Message):
    if not db.is_privileged(m.from_user.id): return
    rows=db.campaign_list()
    if not rows: await m.answer("هنوز کمپینی ساخته نشده.",reply_markup=admin_kb()); return
    for c in rows:
        kb_rows=[[f"فعال‌سازی کمپین {c['id']}",f"خاموش‌کردن کمپین {c['id']}"],[f"حذف کمپین {c['id']}"]]
        rank_rows=db.campaign_rank_prizes(c['id'])
        rank_text='\n'.join(f"رتبه {r['rank']}: {esc(r['prize'])}" for r in rank_rows)
        await m.answer(f"#{c['id']} | <b>{esc(c['title'])}</b>\nجایزه کلی: {esc(c['prize'])}\nجوایز رتبه‌ها:\n{rank_text or 'برای این کمپین ثبت نشده'}\nبرندگان: {c['winners_count']}\nوضعیت: {'روشن' if c['active'] else 'خاموش'}\nکپچا: {'اجباری' if c['captcha_required'] else 'غیراجباری'}",parse_mode="HTML",reply_markup=kb(kb_rows))

@dp.message(F.text.regexp(r"^(فعال‌سازی کمپین|خاموش‌کردن کمپین|حذف کمپین) \d+$"))
async def campaign_action(m:Message):
    if not db.is_privileged(m.from_user.id): return
    action,cid_text=m.text.rsplit(" ",1); cid=int(cid_text); c=db.campaign_by_id(cid)
    if not c: await m.answer("کمپین پیدا نشد."); return
    if action=="حذف کمپین": db.delete_campaign(cid); result="حذف شد"
    else: db.set_campaign_active(cid,action=="فعال‌سازی کمپین"); result="به‌روزرسانی شد"
    db.audit(m.from_user.id,"campaign_"+action,"campaign",cid)
    await m.answer(f"کمپین #{cid} {result}.",reply_markup=admin_kb())

@dp.message(Flow.referral_captcha)
async def referral_captcha_answer(m:Message,state:FSMContext):
    d=await state.get_data()
    if (m.text or "").strip()==d.get("ref_answer"):
        db.set_referral_valid(m.from_user.id,True)
        referral=db.referral_by_invitee(m.from_user.id)
        await state.clear()
        await m.answer("پاسخ صحیح بود؛ دعوت شما با موفقیت ثبت شد.",reply_markup=home(m.from_user.id))
        if referral:
            await bot.send_message(referral['inviter_id'], f"{custom_emoji('5823698361697440934','✅')} همچین مرحله کپچا را با موفیقت پشت سر گذاشت", parse_mode="HTML")
            await bot.send_message(referral['inviter_id'], f"{custom_emoji('5823678145286382134','🎉')} تبریک میگم به عنوان رفرال تو ثبت شد", parse_mode="HTML")
    else:
        await m.answer("پاسخ صحیح نیست. برای دریافت لینک دعوت، دوباره از دعوت‌کننده لینک را باز کنید.",reply_markup=home(m.from_user.id))
        await state.clear()

@dp.message(F.text=="کمپین")
async def referral_home(m:Message):
    camp=db.active_campaign(); total,valid=db.referral_stats(m.from_user.id)
    link=f"https://t.me/{(await bot.get_me()).username}?start=ref_{m.from_user.id}"
    if camp:
        rich_payload = {
            "is_rtl": True,
            "blocks": [
                {"type": "heading", "size": 1, "text": {"type": "bold", "text": str(camp['title'])}},
                {"type": "paragraph", "text": f"🎁 جایزه کمپین: {camp['prize']}"},
                {"type": "paragraph", "text": "🔗 لینک اختصاصی شما:"},
                {"type": "paragraph", "text": {"type": "code", "text": link}},
                {"type": "paragraph", "text": "👥 دوستانتان را دعوت کنید تا در کمپین شرکت کنید."}
            ]
        }
        try:
            timeout = aiohttp.ClientTimeout(total=25)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"https://api.telegram.org/bot{TOKEN}/sendRichMessage", json={"chat_id": m.chat.id, "rich_message": rich_payload, "reply_markup": kb([["وضعیت من","لیدربورد"],["منوی اصلی"]]).model_dump(exclude_none=True)}) as response:
                    result = await response.json(content_type=None)
            if not result.get("ok"):
                raise RuntimeError(result.get("description", "sendRichMessage failed"))
        except Exception as exc:
            log.warning("Campaign rich message failed: %s", exc)
            body=f"🎁 <b>{esc(camp['title'])}</b>\n🤝 {esc(camp['prize'])}\n\n🔗 لینک اختصاصی شما:\n<code>{esc(link)}</code>\n👥 دوستانتان را دعوت کنید تا در کمپین شرکت کنید."
            await m.answer(body,parse_mode="HTML",reply_markup=kb([["وضعیت من","لیدربورد"],["منوی اصلی"]]))
    else:
        body=f"🤝 سیستم دعوت همیشه فعال است؛ ℹ️ در حال حاضر کمپین فعالی نداریم.\n🔗 لینک اختصاصی شما:\n<code>{esc(link)}</code>"
        await m.answer(body,parse_mode="HTML",reply_markup=kb([["وضعیت من","لیدربورد"],["منوی اصلی"]]))

@dp.message(F.text=="وضعیت من")
async def referral_status(m:Message):
    total,valid=db.referral_stats(m.from_user.id); rank=db.referral_rank(m.from_user.id)
    await m.answer(f"{custom_emoji('5823493629196375797','👥')} دعوت‌های ثبت‌شده: {total}\n{custom_emoji('5821293029687825738','✅')} دعوت‌های معتبر کمپین: {valid}\n{custom_emoji('5823612273372959359','🏆')} رتبه فعلی: {rank or '—'}",parse_mode="HTML",reply_markup=kb([["کمپین","لیدربورد"],["منوی اصلی"]]))

@dp.message(F.text=="لیدربورد")
async def referral_board(m:Message):
    rows=db.referral_leaderboard(20)
    if not rows: await m.answer("هنوز دعوت معتبری ثبت نشده.",reply_markup=kb([["کمپین","وضعیت من"],["منوی اصلی"]])); return
    table=[[i,("@"+r['username']) if r['username'] else (r['first_name'] or str(r['inviter_id'])),r['n']] for i,r in enumerate(rows,1)]
    await send_rich_table(m.chat.id,"لیدربورد دعوت‌ها",["رتبه","کاربر","دعوت معتبر"],table,reply_markup=kb([["کمپین","وضعیت من"],["منوی اصلی"]]))

@dp.message(F.text=="جوین اجباری")
async def mandatory_admin(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    channels=db.mandatory_channels()
    status=db.setting("force_join_enabled","0")=="1"
    await m.answer(f"جوین اجباری: {'روشن' if status else 'خاموش'}\nتعداد کانال‌ها: {len(channels)}",reply_markup=kb([["روشن‌کردن جوین اجباری","خاموش‌کردن جوین اجباری"],["افزودن کانال اجباری","فهرست کانال‌های اجباری"],["منوی مدیریت"]]))

@dp.message(F.text.in_({"روشن‌کردن جوین اجباری","خاموش‌کردن جوین اجباری"}))
async def mandatory_toggle(m:Message):
    if not db.is_privileged(m.from_user.id): return
    db.set_setting("force_join_enabled","1" if m.text=="روشن‌کردن جوین اجباری" else "0")
    await m.answer("تنظیم جوین اجباری ذخیره شد.",reply_markup=admin_kb())

@dp.message(F.text=="افزودن کانال اجباری")
async def mandatory_add_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.set_state(Flow.mandatory_chat); await m.answer("شناسه عددی یا @username کانال را بفرستید. ربات باید در کانال ادمین باشد:")

@dp.message(Flow.mandatory_chat)
async def mandatory_chat_save(m:Message,state:FSMContext):
    await state.update_data(m_chat=(m.text or "").strip()); await state.set_state(Flow.mandatory_title); await m.answer("نام نمایشی کانال را وارد کنید:")

@dp.message(Flow.mandatory_title)
async def mandatory_title_save(m:Message,state:FSMContext):
    await state.update_data(m_title=(m.text or "")[:80]); await state.set_state(Flow.mandatory_url); await m.answer("لینک عضویت کانال را ارسال کنید:")

@dp.message(Flow.mandatory_url)
async def mandatory_url_save(m:Message,state:FSMContext):
    url=(m.text or "").strip()
    if not (url.startswith("https://t.me/") or url.startswith("http://t.me/")): await m.answer("لینک t.me معتبر ارسال کنید."); return
    d=await state.get_data(); cid=db.add_mandatory_channel(d['m_chat'],d['m_title'],url)
    await state.clear(); await m.answer(f"کانال اجباری #{cid} ثبت شد.",reply_markup=admin_kb())

@dp.message(F.text=="فهرست کانال‌های اجباری")
async def mandatory_list(m:Message):
    if not db.is_privileged(m.from_user.id): return
    rows=db.mandatory_channels()
    if not rows: await m.answer("کانال اجباری ثبت نشده."); return
    for x in rows: await m.answer(f"#{x['id']} {esc(x['title'])}\n{esc(x['join_url'])}",parse_mode="HTML",reply_markup=kb([[f"حذف کانال اجباری {x['id']}"]]))

@dp.message(F.text.regexp(r"^حذف کانال اجباری \d+$"))
async def mandatory_remove(m:Message):
    if not db.is_privileged(m.from_user.id): return
    cid=int(m.text.rsplit(" ",1)[1]); db.remove_mandatory_channel(cid); await m.answer("کانال حذف شد.",reply_markup=admin_kb())

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
    await send_report(f"{custom_emoji('5872872125169146997','💎')} <b>شارژ دستی کیف پول</b>\nکاربر: {user_mention(target['id'],target['first_name'],target['username'])}\nمبلغ: <b>+{amount:g} TON</b>\nمدیر: <code>{m.from_user.id}</code>")
    try: await send_wallet_balance_notice(target['id'], amount, added=True)
    except Exception: log.exception("wallet balance increase notification failed")
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
    await send_report(f"{custom_emoji('4990519099055408115','➖')} <b>کسر موجودی کیف پول</b>\nکاربر: {user_mention(target['id'],target['first_name'],target['username'])}\nمبلغ: <b>-{amount:g} TON</b>\nمدیر: <code>{m.from_user.id}</code>")
    try: await send_wallet_balance_notice(target['id'], amount, added=False)
    except Exception: log.exception("wallet balance deduction notification failed")
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
    await send_report(f"{custom_emoji('5872872125169146997' if kind=='adjustment' else '4990519099055408115','💎')} <b>تغییر موجودی کیف پول</b>\nکاربر: <code>{uid}</code>\nمبلغ: <b>{'+' if kind=='adjustment' else '-'}{amount:g} TON</b>\nمدیر: <code>{m.from_user.id}</code>")
    await state.clear(); await m.answer("موجودی با موفقیت به‌روزرسانی شد.",reply_markup=admin_kb())
    try: await send_wallet_balance_notice(uid, amount, added=(kind=='adjustment'))
    except Exception: log.exception("wallet adjustment notification failed")

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


async def notify_order_status(order, payment_approved=False):
    order_no=order["order_no"]
    if payment_approved:
        text=(f"{custom_emoji('5823539211684287784','✅')} <b>پرداخت سفارش شما با موفقیت تأیید شد.</b>\n"
              f"{custom_emoji('5823551254772586211','🧾')} شماره سفارش: <code>{esc(order_no)}</code>\n"
              f"{custom_emoji('5823698361697440934','⏳')} وضعیت سفارش: در انتظار اجرا\n"
              f"{custom_emoji('5823664203822536260','❤️')} از اعتماد شما به BoostlyAds سپاسگزاریم.")
        buttons=[[InlineKeyboardButton(text="مشاهده سفارش",callback_data=f"ba:userorder:{order_no}"),InlineKeyboardButton(text="بازگشت به صفحه اصلی",callback_data="ba:userhome")]]
    elif order["status"]=="in_progress":
        text=(f"{custom_emoji('5933702915213496299','⚙️')} <b>سفارش شما وارد مرحله اجرا شد.</b>\n"
              f"{custom_emoji('5823551254772586211','🧾')} شماره سفارش: <code>{esc(order_no)}</code>\n"
              f"{custom_emoji('5823678145286382134','🛠')} تیم ما در حال انجام سفارش شماست.")
        buttons=[[InlineKeyboardButton(text="مشاهده سفارش",callback_data=f"ba:userorder:{order_no}"),InlineKeyboardButton(text="پشتیبانی",url="https://t.me/Parsa_0102")]]
    elif order["status"]=="completed":
        text=(f"{custom_emoji('5461151367559141950','🎉')} <b>سفارش شما با موفقیت تکمیل شد!</b>\n"
              f"{custom_emoji('5823551254772586211','🧾')} شماره سفارش: <code>{esc(order_no)}</code>\n"
              f"{custom_emoji('6007944173703929511','✅')} وضعیت سفارش: تکمیل‌شده\n"
              f"{custom_emoji('5823664203822536260','❤️')} از انتخاب BoostlyAds متشکریم ❤️")
        buttons=[[InlineKeyboardButton(text="مشاهده سفارش",callback_data=f"ba:userorder:{order_no}"),InlineKeyboardButton(text="ثبت سفارش جدید",callback_data="ba:userhome")],[InlineKeyboardButton(text="پشتیبانی",url="https://t.me/Parsa_0102")]]
    else:
        text=f"وضعیت سفارش {esc(order_no)} به‌روزرسانی شد: {esc(order['status'])}"
        buttons=[[InlineKeyboardButton(text="مشاهده سفارش",callback_data=f"ba:userorder:{order_no}")]]
    await bot.send_message(order["user_id"],text,reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),parse_mode="HTML")

@dp.callback_query(F.data.startswith("ba:userorder:"))
async def user_order_button(cq:CallbackQuery):
    order_no=cq.data.split(":",2)[2]; o=db.get_order(order_no)
    if not o or o["user_id"]!=cq.from_user.id:
        await cq.answer("این سفارش متعلق به شما نیست.",show_alert=True); return
    details=json.loads(o["details"] or "{}")
    status_names={"awaiting_payment":"در انتظار پرداخت","payment_under_review":"در انتظار بررسی","queued":"در انتظار اجرا","in_progress":"در حال اجرا","completed":"تکمیل‌شده","cancelled":"لغوشده","payment_rejected":"پرداخت ردشده"}
    body=(f"<b>جزئیات سفارش {esc(order_no)}</b>\nخدمت: {esc(o['product_title'])}\nپکیج: {esc(o['package_title'])}\n"
          f"مبلغ: {esc(o['price'])} {esc(o['currency'])}\nوضعیت: {status_names.get(o['status'],esc(o['status']))}\n"
          f"مقصد: {esc(details.get('target_link','-'))}")
    await cq.message.answer(body,parse_mode="HTML",reply_markup=kb([["سفارش‌های من"],["منوی اصلی"]]))
    await cq.answer()

@dp.callback_query(F.data=="ba:userhome")
async def user_home_button(cq:CallbackQuery):
    await cq.message.answer("منوی اصلی:",reply_markup=home(cq.from_user.id)); await cq.answer()

@dp.message(F.text.startswith("وضعیت "))
async def status_prompt(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    order_no=m.text.replace("وضعیت ","",1).strip()
    if not db.get_order(order_no): await m.answer("سفارش پیدا نشد."); return
    await state.clear()
    await m.answer(f"وضعیت سفارش {order_no} را انتخاب کنید:",reply_markup=kb([[f"شروع اجرای {order_no}"],[f"تکمیل سفارش {order_no}"],[f"لغو سفارش {order_no}"],["منوی مدیریت"]]))
@dp.message(F.text.regexp(r"^(شروع اجرای|تکمیل سفارش|لغو سفارش) BA"))
async def status_change_button(m:Message):
    if not db.is_staff(m.from_user.id): return
    action,order_no=m.text.split(" ",1); new_status={"شروع اجرای":"in_progress","تکمیل سفارش":"completed","لغو سفارش":"cancelled"}[action]
    o=db.set_order_status(order_no,new_status,"لغو توسط مدیریت" if new_status=="cancelled" else None)
    if not o: await m.answer("سفارش پیدا نشد."); return
    await notify_order_status(o)
    db.audit(m.from_user.id,"order_status_changed","order",order_no,{"status":new_status})
    await m.answer("وضعیت سفارش به‌روزرسانی شد.",reply_markup=admin_kb())

@dp.message(F.text=="مدیریت بونوس")
async def bonus_admin(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.clear()
    await m.answer("<b>مدیریت بونوس</b>",parse_mode="HTML",reply_markup=kb([["ایجاد بونوس"],["فهرست بونوس‌ها"],["منوی مدیریت"]]))

@dp.message(F.text=="ایجاد بونوس")
async def bonus_create_start(m:Message,state:FSMContext):
    if not db.is_privileged(m.from_user.id): return
    await state.set_state(Flow.bonus_title)
    await m.answer(f"{custom_emoji('4990247536863216681','🎁')} <b>نام بونوس را وارد کنید:</b>",parse_mode="HTML",reply_markup=kb([["لغو","منوی مدیریت"]]))

@dp.message(Flow.bonus_title)
async def bonus_title_input(m:Message,state:FSMContext):
    if m.text in ("لغو","منوی مدیریت"): await state.clear(); await m.answer("لغو شد.",reply_markup=admin_kb()); return
    title=(m.text or "").strip()
    if not title: await m.answer("نام بونوس را وارد کنید."); return
    await state.update_data(bonus_title=title[:100]); await state.set_state(Flow.bonus_amount)
    await m.answer(f"{custom_emoji('5873230707693723886','💰')} <b>مبلغ بونوس به TON را وارد کنید:</b>",parse_mode="HTML")

@dp.message(Flow.bonus_amount)
async def bonus_amount_input(m:Message,state:FSMContext):
    try:
        amount=float((m.text or "").replace(',','.'))
        if not (0 < amount <= 100000000): raise ValueError()
    except Exception: await m.answer("مبلغ معتبر و بزرگ‌تر از صفر وارد کنید."); return
    await state.update_data(bonus_amount=amount); await state.set_state(Flow.bonus_capacity)
    await m.answer(f"{custom_emoji('5823638846335620397','👥')} <b>چند کاربر بتوانند این بونوس را دریافت کنند؟</b>",parse_mode="HTML")

@dp.message(Flow.bonus_capacity)
async def bonus_capacity_input(m:Message,state:FSMContext):
    try:
        capacity=int(m.text)
        if not 1<=capacity<=1000000: raise ValueError()
    except Exception: await m.answer("ظرفیت را به‌صورت عددی بین ۱ تا ۱٬۰۰۰٬۰۰۰ وارد کنید."); return
    await state.update_data(bonus_capacity=capacity); await state.set_state(Flow.bonus_start)
    await m.answer(f"{custom_emoji('4990533856563036953','🗓️')} <b>زمان شروع را به وقت ایران وارد کنید:</b>\nفرمت: <code>YYYY-MM-DD HH:MM</code> یا «اکنون»",parse_mode="HTML",reply_markup=kb([["اکنون"],["لغو"]]))

@dp.message(Flow.bonus_start)
async def bonus_start_input(m:Message,state:FSMContext):
    from zoneinfo import ZoneInfo
    raw=(m.text or "").strip()
    try:
        dt=datetime.now(ZoneInfo("Asia/Tehran")) if raw=="اکنون" else datetime.strptime(raw,"%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Asia/Tehran"))
        start_utc=dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except Exception: await m.answer("زمان را با فرمت YYYY-MM-DD HH:MM وارد کنید یا «اکنون» را بزنید."); return
    await state.update_data(bonus_start=start_utc); await state.set_state(Flow.bonus_end)
    await m.answer(f"{custom_emoji('4990533856563036953','⏳')} <b>زمان پایان را به وقت ایران وارد کنید:</b>\nفرمت: <code>YYYY-MM-DD HH:MM</code> یا «بدون انقضا»",parse_mode="HTML",reply_markup=kb([["بدون انقضا"],["لغو"]]))

@dp.message(Flow.bonus_end)
async def bonus_end_input(m:Message,state:FSMContext):
    from zoneinfo import ZoneInfo
    raw=(m.text or "").strip()
    if raw=="لغو": await state.clear(); await m.answer("لغو شد.",reply_markup=admin_kb()); return
    try:
        end_utc="" if raw=="بدون انقضا" else datetime.strptime(raw,"%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Asia/Tehran")).astimezone(timezone.utc).isoformat(timespec="seconds")
        d=await state.get_data()
        if end_utc and end_utc<=d['bonus_start']: raise ValueError()
    except Exception: await m.answer("زمان پایان معتبر نیست یا باید بعد از زمان شروع باشد."); return
    token=uuid.uuid4().hex[:20]
    bonus=db.create_bonus(d['bonus_title'],d['bonus_amount'],d['bonus_capacity'],d['bonus_start'],end_utc,token)
    me=await bot.get_me(); link=f"https://t.me/{me.username}?start=bonus_{bonus['id']}_{token}"
    await state.clear()
    await m.answer(f"{custom_emoji('4990247536863216681','🎁')} <b>بونوس ساخته شد.</b>\nنام: <b>{esc(bonus['title'])}</b>\n{custom_emoji('5873230707693723886','💰')} مبلغ هر نفر: <b>{bonus['amount']:g} TON</b>\n{custom_emoji('5823638846335620397','👥')} ظرفیت: <b>{bonus['capacity']}</b> نفر\n{custom_emoji('6008124493610885197','🔗')} لینک اختصاصی:\n<code>{link}</code>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="انتشار لینک بونوس",url=link)]]))

@dp.message(F.text=="فهرست بونوس‌ها")
async def bonus_list(m:Message):
    if not db.is_privileged(m.from_user.id): return
    rows=db.list_bonuses()
    if not rows: await m.answer("هنوز بونوسی ساخته نشده.",reply_markup=admin_kb()); return
    for b in rows:
        active=bool(b['active']) and (not b['end_at'] or b['end_at']>=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        await m.answer(f"{custom_emoji('4990247536863216681','🎁')} <b>{esc(b['title'])}</b>\nمبلغ: <b>{b['amount']:g} TON</b>\nظرفیت: {b['claimed_count']} / {b['capacity']}\nوضعیت: {'فعال' if active else 'غیرفعال/تمام‌شده'}\nشناسه: <code>#{b['id']}</code>",parse_mode="HTML",reply_markup=kb([[f"غیرفعال‌کردن بونوس {b['id']}"]] if b['active'] else [[f"فعال‌کردن بونوس {b['id']}"]]))

@dp.message(F.text.regexp(r"^(فعال‌کردن بونوس|غیرفعال‌کردن بونوس) \d+$"))
async def bonus_toggle(m:Message):
    if not db.is_privileged(m.from_user.id): return
    action,bid=m.text.rsplit(" ",1); b=db.set_bonus_active(int(bid),action=="فعال‌کردن بونوس")
    if not b: await m.answer("بونوس پیدا نشد."); return
    await m.answer("وضعیت بونوس به‌روزرسانی شد.",reply_markup=admin_kb())

@dp.message(Command("backup"))
async def backup(m:Message):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    path=db.backup_file()
    try: await m.answer_document(FSInputFile(path,filename="boostly-backup.sqlite3"),caption="نسخه پشتیبان دیتابیس")
    finally:
        try: os.unlink(path)
        except OSError: pass

@dp.message(Flow.channel_reject_reason, F.chat.id==MANAGEMENT_GROUP_ID)
async def channel_reject_reason_input(m:Message,state:FSMContext):
    authorized=db.is_staff(m.from_user.id)
    if not authorized:
        try:
            member=await bot.get_chat_member(MANAGEMENT_GROUP_ID,m.from_user.id)
            authorized=member.status in ("administrator","creator")
        except Exception:
            authorized=False
    if not authorized:
        await state.clear(); return
    reason=(m.text or m.caption or "").strip()
    if len(reason)<3:
        await m.answer("لطفاً دلیل رد را با توضیح کافی ارسال کنید."); return
    d=await state.get_data(); kind=d.get("channel_reject_kind"); rid=int(d.get("channel_reject_id",0))
    if kind=="channel":
        row=db.review_channel(rid,False,m.from_user.id,reason)
        user_id=row['user_id'] if row else None
    else:
        row=db.review_custom_channel(rid,m.from_user.id,"rejected",reason)
        user_id=row['user_id'] if row else None
    if not row:
        await state.clear(); await m.answer("این درخواست قبلاً بررسی شده یا پیدا نشد.",reply_markup=admin_kb()); return
    try:
        await bot.send_message(user_id, f"{custom_emoji('5820953654256997602','❌')} <b>درخواست کانال شما رد شد.</b>\n{custom_emoji('4990182601252668309','📝')} <b>دلیل رد:</b>\n{esc(reason)}",parse_mode="HTML")
    except Exception: log.exception("channel rejection notification failed")
    try:
        await bot.edit_message_reply_markup(MANAGEMENT_GROUP_ID,d.get("channel_reject_group_message_id"),reply_markup=None)
    except Exception: pass
    await send_report(f"{custom_emoji('5820953654256997602','❌')} <b>درخواست کانال رد شد</b>\nکاربر: <code>{user_id}</code>\nشناسه درخواست: <code>#{rid}</code>\n{custom_emoji('4990182601252668309','📝')} دلیل: {esc(reason)}")
    db.audit(m.from_user.id,"channel_rejected_with_reason","channel",rid,{"reason":reason})
    await state.clear(); await m.answer("درخواست رد شد و دلیل برای کاربر ارسال شد.",reply_markup=admin_kb())

# One-tap management actions in the management group (no manual approval text).
@dp.callback_query(F.data.startswith("ba:") & ~F.data.startswith("ba:user") & (F.data != "ba:joincheck"))
async def management_action_button(cq:CallbackQuery, state:FSMContext):
    if not cq.message or cq.message.chat.id != MANAGEMENT_GROUP_ID:
        await cq.answer("این دکمه فقط در گروه مدیریت قابل استفاده است.",show_alert=True); return
    if not db.is_staff(cq.from_user.id):
        try:
            member=await bot.get_chat_member(MANAGEMENT_GROUP_ID,cq.from_user.id)
            if member.status not in ("administrator","creator"):
                await cq.answer("دسترسی مدیریت ندارید.",show_alert=True); return
        except Exception:
            await cq.answer("بررسی دسترسی ممکن نشد.",show_alert=True); return
    try:
        _, kind, action, raw_id = cq.data.split(":",3)
        ref_id = raw_id if kind in ("payment", "order") else int(raw_id)
    except Exception:
        await cq.answer("درخواست نامعتبر است.",show_alert=True); return
    if kind=="channel" and action=="no":
        await state.update_data(channel_reject_kind="channel",channel_reject_id=ref_id,channel_reject_group_message_id=cq.message.message_id)
        await state.set_state(Flow.channel_reject_reason)
        try:
            await cq.message.reply(f"{custom_emoji('5823393706782232983','📝')} <b>دلیل رد درخواست کانال #{ref_id} را در پاسخ به همین پیام بنویسید:</b>\nاین متن برای کاربر ارسال می‌شود.",parse_mode="HTML")
            await cq.answer("منتظر دلیل رد در همین گروه هستم.")
        except Exception:
            await state.clear()
            await cq.answer("ارسال پیام برای دریافت دلیل رد ناموفق بود.",show_alert=True)
        return
    if kind=="custom" and action=="no":
        await state.update_data(channel_reject_kind="custom",channel_reject_id=ref_id,channel_reject_group_message_id=cq.message.message_id)
        await state.set_state(Flow.channel_reject_reason)
        try:
            await cq.message.reply(f"{custom_emoji('5823393706782232983','📝')} <b>دلیل رد درخواست کانال #{ref_id} را در پاسخ به همین پیام بنویسید:</b>\nاین متن برای کاربر ارسال می‌شود.",parse_mode="HTML")
            await cq.answer("منتظر دلیل رد در همین گروه هستم.")
        except Exception:
            await state.clear()
            await cq.answer("ارسال پیام برای دریافت دلیل رد ناموفق بود.",show_alert=True)
        return
    if kind=="channel":
        row=db.review_channel(ref_id,action=="yes",cq.from_user.id)
        if not row: await cq.answer("این درخواست قبلاً بررسی شده است.",show_alert=True); return
        result="تأیید شد" if action=="yes" else "رد شد"
        try: await bot.send_message(row['user_id'],f"درخواست ثبت کانال/گروه شما {result}.")
        except Exception: pass
        await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.reply(f"درخواست کانال #{ref_id} {result}.")
        db.audit(cq.from_user.id,"channel_reviewed","channel",ref_id,{"result":result})
    elif kind=="custom":
        row=db.review_custom_channel(ref_id,cq.from_user.id,"rejected" if action=="no" else ("approved" if action=="public" else "contacted"),action)
        if not row: await cq.answer("این درخواست قبلاً بررسی شده است.",show_alert=True); return
        text="درخواست کانال شما رد شد." if action=="no" else ("کانال شما برای استفاده شخصی تأیید شد." if action=="private" else ("کانال شما به فهرست عمومی مقصدها اضافه شد." if action=="public" else "درخواست شما دریافت شد."))
        if action=="private": db.add_private_channel(row['user_id'],row['channel_link'])
        if action=="public":
            db.submit_channel(row['user_id'],"channel/group",row['channel_link'])
            with db.conn() as con: con.execute("UPDATE channel_submissions SET status='approved',reviewer_id=?,reviewed_at=? WHERE id=(SELECT MAX(id) FROM channel_submissions WHERE user_id=? AND invite_link=?)",(cq.from_user.id,db.now(),row['user_id'],row['channel_link']))
        try: await bot.send_message(row['user_id'],text)
        except Exception: pass
        await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.reply("وضعیت درخواست کانال به‌روزرسانی شد.")
    elif kind in ("payment","wallet"):
        if kind=="wallet" and not db.is_privileged(cq.from_user.id):
            await cq.answer("فقط مالک یا توسعه‌دهنده می‌تواند شارژ کیف پول را تأیید کند.",show_alert=True); return
        if kind=="payment":
            with db.conn() as con: pay=con.execute("SELECT id FROM payments WHERE order_id=(SELECT id FROM orders WHERE order_no=?) AND status='under_review' ORDER BY id DESC LIMIT 1",(str(ref_id),)).fetchone()
            if not pay: await cq.answer("پرداخت در انتظار بررسی پیدا نشد.",show_alert=True); return
            order=db.review_payment(pay['id'],action=="yes",cq.from_user.id)
            if not order: await cq.answer("پرداخت قبلاً بررسی شده است.",show_alert=True); return
            try:
                if action=="yes":
                    await notify_order_status(order, payment_approved=True)
                    await send_report(f"{custom_emoji('6007944173703929511','✅')} <b>خرید موفق</b>\nکاربر: {user_mention(order['user_id'])}\nخدمت: <b>{esc(order['product_title'])}</b>\nپکیج: <b>{esc(order['package_title'])}</b>\nمبلغ: <b>{esc(order['price'])} {esc(order['currency'])}</b>\nسفارش: <code>{esc(order['order_no'])}</code>")
                    await send_report(f"{custom_emoji('6007944173703929511','💳')} <b>پرداخت تأیید شد</b>\nکاربر: {user_mention(order['user_id'])}\nمبلغ: <b>{esc(order['price'])} {esc(order['currency'])}</b>\nسفارش: <code>{esc(order['order_no'])}</code>")
                else:
                    await bot.send_message(order['user_id'],f"پرداخت سفارش {order['order_no']} رد شد. برای پشتیبانی از @Parsa_0102 کمک بگیرید.")
                    await send_report(f"{custom_emoji('4990519099055408115','❌')} <b>پرداخت رد شد</b>\nکاربر: {user_mention(order['user_id'])}\nمبلغ: <b>{esc(order['price'])} {esc(order['currency'])}</b>\nسفارش: <code>{esc(order['order_no'])}</code>")
            except Exception: log.exception("payment status notification failed")
        else:
            row=db.review_wallet_entry(ref_id,action=="yes",cq.from_user.id)
            if not row: await cq.answer("این درخواست قبلاً بررسی شده است.",show_alert=True); return
            try:
                if action=="yes":
                    amount=float(row['amount'])
                    await send_wallet_balance_notice(row['user_id'], amount, added=True)
                    await send_report(f"{custom_emoji('5872872125169146997','💎')} <b>شارژ کیف پول تأیید شد</b>\nکاربر: {user_mention(row['user_id'])}\nمبلغ شارژ: <b>+{amount:g} TON</b>\nشناسه شارژ: <code>#{ref_id}</code>")
                else:
                    await bot.send_message(row['user_id'],"درخواست شارژ کیف پول شما تأیید نشد. برای راهنمایی با پشتیبانی تماس بگیرید.")
                    await send_report(f"{custom_emoji('4990519099055408115','❌')} <b>شارژ کیف پول رد شد</b>\nکاربر: {user_mention(row['user_id'])}\nمبلغ: <b>{float(row['amount']):g} TON</b>\nشناسه شارژ: <code>#{ref_id}</code>")
            except Exception: pass
        await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.reply("نتیجه بررسی برای کاربر ارسال شد.")
    elif kind=="order":
        status={"doing":"in_progress","done":"completed","cancel":"cancelled"}.get(action)
        if not status: await cq.answer("وضعیت نامعتبر است.",show_alert=True); return
        order=db.set_order_status(str(ref_id),status,"لغو توسط مدیریت" if status=="cancelled" else None)
        if not order: await cq.answer("سفارش پیدا نشد.",show_alert=True); return
        try: await notify_order_status(order)
        except Exception: log.exception("order status notification failed")
        await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.reply("وضعیت سفارش تغییر کرد و به مشتری اطلاع داده شد.")
    await cq.answer("انجام شد.")

# Reply-to workflows inside the management group: channel review, customer support, order follow-up.
@dp.message(F.chat.id==MANAGEMENT_GROUP_ID, F.reply_to_message)
async def management_group_reply(m:Message):
    # Operational decisions are made only through inline buttons attached to the original notice.
    if not m.from_user or m.from_user.is_bot: return
    link=db.group_link(m.reply_to_message.message_id)
    if link and link["kind"] in ("payment","wallet","order","channel","custom"):
        await m.reply("برای این عملیات از دکمه‌های زیر پیام اصلی استفاده کنید؛ اجرای دستوری غیرفعال است.")


async def nightly_backup():
    while True:
        now=datetime.now()
        seconds=((24*60*60)-((now.hour*3600+now.minute*60+now.second)))
        await asyncio.sleep(max(60,seconds))
        path=None
        try:
            path=db.backup_file()
            await bot.send_document(MANAGEMENT_GROUP_ID,FSInputFile(path,filename=f"boostly-backup-{datetime.now().strftime('%Y%m%d')}.sqlite3"),caption="بکاپ خودکار شبانه دیتابیس BoostlyAds")
        except Exception: log.exception("nightly backup failed")
        finally:
            if path:
                try: os.unlink(path)
                except OSError: pass

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
            if db.setting("force_join_enabled","0")=="1" and event.chat.type=="private":
                channels=db.mandatory_channels(); missing=[]
                for ch in channels:
                    try:
                        member=await bot.get_chat_member(ch["chat_id"],user_obj.id)
                        if member.status not in ("creator","administrator","member") and not (member.status=="restricted" and getattr(member,"is_member",False)):
                            missing.append(ch)
                    except Exception:
                        missing.append(ch)
                if missing:
                    rows=[[KeyboardButton(text=ch["title"],url=ch["join_url"]) ] for ch in []]  # URL buttons are rendered inline below
                    markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=ch["title"],url=ch["join_url"])] for ch in missing]+[[InlineKeyboardButton(text="عضو شدم، بررسی عضویت",callback_data="ba:joincheck")]])
                    if hasattr(event,"answer"):
                        await event.answer(f"{custom_emoji('5823442050934116771','🔒')} برای استفاده از خدمات ما باید در چنل‌های زیر جوین شوید",parse_mode="HTML",reply_markup=markup)
                    return None
        return await handler(event,data)

dp.message.outer_middleware(BlockedUserMiddleware())

@dp.callback_query(F.data=="ba:joincheck")
async def mandatory_join_check(cq:CallbackQuery):
    missing=[]
    for ch in db.mandatory_channels():
        try:
            member=await bot.get_chat_member(ch["chat_id"],cq.from_user.id)
            if member.status not in ("creator","administrator","member") and not (member.status=="restricted" and getattr(member,"is_member",False)): missing.append(ch)
        except Exception: missing.append(ch)
    if missing: await cq.answer("هنوز عضویت همه کانال‌ها تأیید نشده است.",show_alert=True); return
    await cq.answer("عضویت تأیید شد.")
    await cq.message.answer("عضویت شما تأیید شد. از منوی ربات استفاده کنید.",reply_markup=home(cq.from_user.id))

async def main():
    db.init_db(OWNER_ID,DEVELOPER_ID)
    db.set_setting("management_group_id",str(MANAGEMENT_GROUP_ID))
    db.set_setting("report_group_id",str(REPORT_GROUP_ID))
    await bot.delete_webhook(drop_pending_updates=False)
    asyncio.create_task(hourly_report())
    asyncio.create_task(nightly_backup())
    log.info("Boostly Ads started with long polling")
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__": asyncio.run(main())

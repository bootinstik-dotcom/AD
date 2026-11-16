import asyncio, os, tempfile, html, json, logging, traceback
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
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
    user_lookup=State()

async def send_group(text, reply_markup=None):
    try:
        msg=await bot.send_message(MANAGEMENT_GROUP_ID, text, parse_mode="HTML", reply_markup=reply_markup)
        return msg
    except Exception as e:
        log.exception("Cannot send to management group")
        return None

async def notify_staff(text):
    return await send_group(text)

async def group_notice(kind, ref_id, uid, text):
    msg=await send_group(text)
    if msg: db.add_group_link(msg.message_id, kind, ref_id, uid)
    return msg

async def start_order(message:Message, state:FSMContext, slug:str):
    with db.conn() as c: cat=c.execute("SELECT * FROM categories WHERE slug=? AND active=1",(slug,)).fetchone()
    if not cat:
        await message.answer("این دسته خدمات فعلاً فعال نیست.", reply_markup=home(message.from_user.id)); return
    targets=db.approved_channels()
    if not targets:
        await message.answer("هنوز هیچ کانال یا گروهی برای تبلیغات تأیید نشده است. بعداً دوباره مراجعه کنید.", reply_markup=home(message.from_user.id)); return
    await state.clear(); await state.update_data(category_id=cat["id"], category_title=cat["title"], category_slug=slug)
    await state.set_state(Flow.choose_target)
    rows=[[f"{x['target_type']} | {x['invite_link'][:28]} | #{x['id']}"] for x in targets]
    await message.answer("ابتدا کانال یا گروه مقصد تبلیغ را انتخاب کنید:", reply_markup=kb(rows+[["بازگشت","منوی اصلی"]]))

@dp.message(CommandStart())
async def start(m:Message,state:FSMContext):
    db.upsert_user(m.from_user); await state.clear()
    await m.answer(f"به <b>{BOT_NAME}</b> خوش آمدید.\nاز منوی زیر خدمات موردنظر را انتخاب کنید.",parse_mode="HTML",reply_markup=home(m.from_user.id))

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
    await m.answer(f"برای ثبت کانال یا گروه، ابتدا اکانت {REQUIRED_ADMIN_ACCOUNT} را در کانال یا گروه خود ادمین کنید.\nپس از انجام، دکمه «ادمین کردم» را بزنید.",reply_markup=kb([["ادمین کردم"],["بازگشت"]]))

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
        f"<b>درخواست ثبت کانال/گروه</b>\nشناسه درخواست: <code>#{cid}</code>\nکاربر: <code>{m.from_user.id}</code> (@{esc(m.from_user.username or '-')})\nلینک: {esc(link)}\n\nبرای تأیید یا رد، روی همین پیام Reply کنید و بنویسید «تأیید» یا «رد».")
    await state.clear()
    await m.answer("درخواست شما برای بررسی ارسال شد. پس از تأیید مدیریت، کانال یا گروه در فهرست مقصدهای تبلیغاتی قرار می‌گیرد.",reply_markup=home(m.from_user.id))

@dp.message(Flow.choose_target)
async def choose_target(m:Message,state:FSMContext):
    targets=db.approved_channels(); chosen=None
    for x in targets:
        label=f"{x['target_type']} | {x['invite_link'][:28]} | #{x['id']}"
        if m.text==label: chosen=x; break
    if not chosen: await m.answer("یکی از کانال‌ها یا گروه‌های فهرست را انتخاب کنید."); return
    d=await state.get_data(); await state.update_data(target_id=chosen["id"],target_link=chosen["invite_link"])
    items=[]
    with db.conn() as c: items=c.execute("SELECT * FROM products WHERE category_id=? AND active=1 ORDER BY sort_order,id",(d["category_id"],)).fetchall()
    if not items: await m.answer("برای این دسته هنوز خدمتی تعریف نشده است.",reply_markup=home(m.from_user.id)); await state.clear(); return
    await state.set_state(Flow.choose_product)
    await m.answer("خدمت موردنظر را انتخاب کنید:",reply_markup=kb([[p["title"]] for p in items]+[["بازگشت","منوی اصلی"]]))

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
    await state.set_state(Flow.destination)
    await m.answer("توضیحات یا لینک موردنیاز سفارش را ارسال کنید:")

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
    d=await state.get_data(); order=db.create_order(m.from_user.id,{"id":d["product_id"],"title":d["product_title"]},
        {"id":d["package_id"],"title":d["package_title"],"price":d["price"],"currency":d["currency"]},d["details"])
    db.audit(m.from_user.id,"order_created","order",order["order_no"])
    await group_notice("order",order["order_no"],m.from_user.id,
        f"<b>سفارش جدید</b>\nشناسه: <code>{order['order_no']}</code>\nکاربر: <code>{m.from_user.id}</code>\nخدمت: {esc(order['product_title'])}\nمبلغ: {esc(order['price'])} {esc(order['currency'])}\nمقصد: {esc(d['details'].get('target_link','-'))}")
    methods=db.methods()
    if not methods:
        await state.clear(); await m.answer(f"سفارش {order['order_no']} ثبت شد. روش پرداخت هنوز فعال نشده؛ پشتیبانی راهنمایی می‌کند.",reply_markup=home(m.from_user.id)); return
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
        f"<b>پرداخت برای بررسی</b>\nسفارش: <code>{d['order_no']}</code>\nکاربر: <code>{m.from_user.id}</code>\nTXID: <code>{esc(d['txid'])}</code>\nبرای بررسی، روی این پیام Reply کنید و «تأیید» یا «رد» بنویسید.")
    if fid and gmsg:
        try: await bot.send_photo(MANAGEMENT_GROUP_ID,fid,caption=f"رسید پرداخت سفارش {d['order_no']}",reply_to_message_id=gmsg.message_id)
        except Exception: log.exception("receipt forward failed")
    await state.clear(); await m.answer("رسید و اطلاعات پرداخت ثبت شد و پس از بررسی دستی نتیجه اعلام می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="سفارش‌های من")
async def my_orders(m:Message):
    rows=db.user_orders(m.from_user.id)
    if not rows: await m.answer("هنوز سفارشی ثبت نکرده‌اید.",reply_markup=home(m.from_user.id)); return
    labels=[]
    for x in rows:
        status={"cancelled":"🔴","completed":"🟢","in_progress":"🔵","awaiting_payment":"⚪","payment_under_review":"🟡","queued":"🔵","payment_rejected":"🔴"}.get(x["status"],"⚪")
        labels.append([f"{status} {x['order_no']}"])
    await m.answer("برای مشاهده جزئیات، سفارش را انتخاب کنید:",reply_markup=kb(labels+[["منوی اصلی"]]))

@dp.message(F.text.regexp(r"^(?:🔴 |🟢 |🔵 |⚪ |🟡 )?BA\d+"))
async def order_detail(m:Message,state:FSMContext):
    order_no=m.text.split()[-1]
    o=db.get_order(order_no)
    if not o or o["user_id"]!=m.from_user.id: return
    try: details=json.loads(o["details"])
    except: details={}
    status_map={"awaiting_payment":"در انتظار پرداخت","payment_under_review":"در انتظار بررسی پرداخت","queued":"تأیید شده / در صف اجرا","in_progress":"در حال انجام","completed":"تکمیل شده","cancelled":"لغو شده","payment_rejected":"پرداخت رد شده"}
    text=(f"<b>جزئیات سفارش {o['order_no']}</b>\nخدمت: {esc(o['product_title'])}\nپکیج: {esc(o['package_title'])}\n"
          f"مبلغ: {esc(o['price'])} {esc(o['currency'])}\nوضعیت: {status_map.get(o['status'],o['status'])}\n"
          f"مقصد: {esc(details.get('target_link','-'))}\nتوضیحات: {esc(details.get('destination','-'))}")
    if o["status"]=="cancelled": text+=f"\nعلت لغو: {esc(details.get('cancel_reason','در توضیحات سفارش ثبت نشده است'))}"
    await m.answer(text,parse_mode="HTML",reply_markup=kb([[f"پیگیری {o['order_no']}"] ,["سفارش‌های من","منوی اصلی"]]))

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
    u=db.user(m.from_user.id); balance=float(u["balance"] or 0) if u else 0
    table=(f"شناسه       {m.from_user.id}\nنام          {m.from_user.full_name}\n"
           f"نام کاربری   @{m.from_user.username or '-'}\nنقش          {role_label(m.from_user.id)}\n"
           f"موجودی       {balance:.2f} USDT")
    text=f"<b>👤 حساب کاربری</b>\n<pre>{esc(table)}</pre>"
    await m.answer(text,parse_mode="HTML",reply_markup=kb([["شارژ کیف پول","تاریخچه کیف پول"],["منوی اصلی"]]))

@dp.message(F.text=="تاریخچه کیف پول")
async def wallet_history(m:Message):
    rows=db.wallet_history(m.from_user.id)
    if not rows: await m.answer("هنوز تراکنشی در کیف پول شما ثبت نشده است.",reply_markup=home(m.from_user.id)); return
    lines=[f"#{x['id']} | {x['kind']} | {x['amount']} {x['currency']} | {x['status']}" for x in rows]
    await m.answer("<b>تاریخچه کیف پول</b>\n"+"\n".join(lines),parse_mode="HTML",reply_markup=home(m.from_user.id))

@dp.message(F.text=="شارژ کیف پول")
async def wallet_deposit_start(m:Message,state:FSMContext):
    await state.set_state(Flow.wallet_deposit_amount); await m.answer("مبلغ شارژ به USDT را وارد کنید:")
@dp.message(Flow.wallet_deposit_amount)
async def wallet_deposit_amount(m:Message,state:FSMContext):
    try: amount=float(m.text.replace(",","")); assert amount>0
    except: await m.answer("مبلغ باید عددی و بیشتر از صفر باشد."); return
    methods=db.methods()
    if not methods: await m.answer("روش پرداختی فعال نیست. لطفاً بعداً مراجعه کنید.",reply_markup=home(m.from_user.id)); await state.clear(); return
    await state.update_data(deposit_amount=amount); await state.set_state(Flow.wallet_deposit_method)
    await m.answer("روش پرداخت را انتخاب کنید:",reply_markup=kb([[f"{x['currency']} | {x['network']}"] for x in methods]))
@dp.message(Flow.wallet_deposit_method)
async def wallet_deposit_method(m:Message,state:FSMContext):
    methods=db.methods(); chosen=next((x for x in methods if m.text==f"{x['currency']} | {x['network']}"),None)
    if not chosen: await m.answer("یک روش پرداخت را انتخاب کنید."); return
    d=await state.get_data(); await state.update_data(deposit_method=chosen["id"]); await state.set_state(Flow.wallet_deposit_txid)
    await m.answer(f"آدرس پرداخت:\n<code>{esc(chosen['address'])}</code>\nمبلغ: {d['deposit_amount']} USDT\nپس از پرداخت TXID را ارسال کنید.",parse_mode="HTML")
@dp.message(Flow.wallet_deposit_txid)
async def wallet_deposit_txid(m:Message,state:FSMContext):
    if not m.text or len(m.text.strip())<8: await m.answer("TXID معتبر ارسال کنید."); return
    await state.update_data(deposit_txid=m.text.strip()); await state.set_state(Flow.wallet_deposit_receipt); await m.answer("رسید پرداخت را بفرستید یا «ندارم» بنویسید:")
@dp.message(Flow.wallet_deposit_receipt)
async def wallet_deposit_receipt(m:Message,state:FSMContext):
    d=await state.get_data(); fid=m.photo[-1].file_id if m.photo else ""
    if not fid and (m.text or "").strip()!="ندارم": await m.answer("رسید یا «ندارم» ارسال کنید."); return
    entry=db.add_wallet_entry(m.from_user.id,d["deposit_amount"],"USDT","deposit","pending",f"TXID:{d['deposit_txid']} method:{d['deposit_method']} receipt:{fid}")
    gmsg=await group_notice("wallet",entry,m.from_user.id,f"<b>درخواست شارژ کیف پول</b>\nشناسه: #{entry}\nکاربر: <code>{m.from_user.id}</code>\nمبلغ: {d['deposit_amount']} USDT\nTXID: <code>{esc(d['deposit_txid'])}</code>\nبرای بررسی، روی این پیام Reply کنید و «تأیید» یا «رد» بنویسید.")
    if fid and gmsg:
        try: await bot.send_photo(MANAGEMENT_GROUP_ID,fid,caption=f"رسید شارژ کیف پول #{entry}",reply_to_message_id=gmsg.message_id)
        except Exception: log.exception("wallet receipt forward failed")
    await state.clear(); await m.answer("درخواست شارژ ثبت شد و پس از بررسی دستی به موجودی اضافه می‌شود.",reply_markup=home(m.from_user.id))

@dp.message(F.text=="راهنما")
async def help_user(m:Message):
    await m.answer("۱) یکی از دسته‌های تبلیغ را انتخاب کنید.\n۲) مقصد تبلیغ را از فهرست کانال‌های تأییدشده انتخاب کنید.\n۳) خدمت و پکیج را انتخاب و سفارش را ثبت کنید.\n۴) پرداخت را انجام دهید و TXID و رسید را بفرستید.\nتمام تبلیغات به‌صورت دستی توسط تیم انجام می‌شود.",reply_markup=home(m.from_user.id))
@dp.message(F.text=="پشتیبانی")
async def support_start(m:Message,state:FSMContext):
    await state.set_state(Flow.support); await m.answer("از اینکه با تیم پشتیبانی Boostly Ads در ارتباط هستید خوشحالیم. لطفاً پیام یا مشکل خود را ارسال کنید؛ کارشناسان ما در اولین فرصت پاسخ می‌دهند.")
@dp.message(Flow.support)
async def support_save(m:Message,state:FSMContext):
    body=m.text or m.caption or "رسانه"
    tid=db.add_ticket(m.from_user.id,"درخواست پشتیبانی",body)
    group_msg=await group_notice("support",tid,m.from_user.id,f"<b>پیام پشتیبانی جدید</b>\nکاربر: <code>{m.from_user.id}</code> (@{esc(m.from_user.username or '-')})\nپیام:\n{esc(body)}\n\nبرای پاسخ به مشتری، روی همین پیام Reply کنید و پاسخ را ارسال کنید.")
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
    await m.answer(f"<b>گزارش کلی</b>\nکاربران: {s['users']}\nسفارش‌ها: {s['orders']}\nپرداخت‌های در انتظار: {s['pending']}\nمجموع پرداخت‌های تأییدشده: {s['revenue']}",parse_mode="HTML",reply_markup=admin_kb())

@dp.message(F.text=="همه سفارش‌ها")
async def admin_orders(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.all_orders()
    if not rows: await m.answer("سفارشی ثبت نشده است."); return
    for x in rows[:25]:
        await m.answer(f"<b>#{x['order_no']}</b>\nکاربر: <code>{x['user_id']}</code>\n{x['product_title']} / {x['package_title']}\nمبلغ: {x['price']} {x['currency']}\nوضعیت: {x['status']}\nبرای تغییر وضعیت: وضعیت {x['order_no']}",parse_mode="HTML")

@dp.message(F.text=="بررسی پرداخت‌ها")
async def admin_payments(m:Message):
    if not db.is_staff(m.from_user.id): return
    rows=db.pending_payments()
    if not rows: await m.answer("پرداخت در انتظار بررسی وجود ندارد."); return
    for x in rows:
        await m.answer(f"پرداخت #{x['id']}\nسفارش: {x['order_no']}\nکاربر: {x['user_id']}\nمبلغ: {x['price']} {x['currency']}\nTXID: <code>{esc(x['txid'])}</code>\nبرای شارژ کیف پول نیز درخواست‌ها در گروه مدیریت ثبت می‌شوند.",parse_mode="HTML",reply_markup=kb([[f"تأیید پرداخت {x['id']}",f"رد پرداخت {x['id']}"]]))

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
    await state.update_data(new_price=m.text); await state.set_state(Flow.add_package_currency); await m.answer("واحد قیمت؛ مثلاً USDT یا تومان:")
@dp.message(Flow.add_package_currency)
async def pack_currency(m:Message,state:FSMContext):
    await state.update_data(new_currency=m.text.upper()); await state.set_state(Flow.add_package_duration); await m.answer("مدت/شرایط پکیج یا «-»:")
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
    await state.set_state(Flow.user_lookup); await m.answer("شناسه عددی کاربر را ارسال کنید:")
@dp.message(Flow.user_lookup)
async def user_admin_lookup(m:Message,state:FSMContext):
    if not db.is_staff(m.from_user.id): return
    try: uid=int(m.text)
    except: await m.answer("شناسه عددی معتبر نیست."); return
    u=db.user(uid)
    if not u: await m.answer("کاربر در دیتابیس پیدا نشد."); return
    await state.clear(); await m.answer(f"کاربر: <code>{uid}</code>\nنام: {esc(u['first_name'])}\nنام کاربری: @{esc(u['username'] or '-')}\nنقش: {esc(u['role'])}\nموجودی: {u['balance']} USDT\nوضعیت: {'فعال' if u['active'] else 'غیرفعال'}",parse_mode="HTML",reply_markup=admin_kb())

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
    if m.text not in allowed: await m.answer("وضعیت نامعتبر است."); return
    d=await state.get_data(); o=db.set_order_status(d["status_order"],m.text)
    db.audit(m.from_user.id,"order_status_changed","order",o["order_no"],{"status":m.text})
    await bot.send_message(o["user_id"],f"وضعیت سفارش {o['order_no']} تغییر کرد: {m.text}")
    await state.clear(); await m.answer("وضعیت سفارش به‌روزرسانی شد.",reply_markup=admin_kb())

@dp.message(Command("backup"))
async def backup(m:Message):
    if not db.is_privileged(m.from_user.id): await m.answer("دسترسی کافی ندارید."); return
    path=db.backup_file()
    try: await m.answer_document(FSInputFile(path,filename="boostly-backup.sqlite3"),caption="نسخه پشتیبان دیتابیس")
    finally:
        try: os.unlink(path)
        except OSError: pass

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
            await send_group(f"<b>گزارش یک‌ساعته Boostly Ads</b>\nکاربران: {s['users']}\nکل سفارش‌ها: {s['orders']}\nسفارش‌های ثبت‌شده در ساعت اخیر: {r['orders']}\nتکمیل‌شده در ساعت اخیر: {r['completed']}\nدرخواست‌های پشتیبانی جدید: {r['tickets']}\nواریزی تأییدشده ساعت اخیر: {r['deposits']} USDT\nبرداشت تأییدشده ساعت اخیر: {r['withdrawals']} USDT\nپرداخت‌های در انتظار: {s['pending']}")
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

async def main():
    db.init_db(OWNER_ID,DEVELOPER_ID)
    db.set_setting("management_group_id",str(MANAGEMENT_GROUP_ID))
    await bot.delete_webhook(drop_pending_updates=False)
    asyncio.create_task(hourly_report())
    log.info("Boostly Ads started with long polling")
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__": asyncio.run(main())

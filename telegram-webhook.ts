import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

type TgMessage = { message_id:number; chat:{id:number;type:string}; from:{id:number;first_name?:string;username?:string}; text?:string; caption?:string; photo?:Array<{file_id:string}>; document?:{file_id:string}; };
const token = Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "";
const secret = Deno.env.get("TELEGRAM_WEBHOOK_SECRET") ?? "";
const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const ownerId = Deno.env.get("OWNER_TELEGRAM_ID") ?? "8292338949";
const developerId = Deno.env.get("DEVELOPER_TELEGRAM_ID") ?? "858897695";
const groupId = Deno.env.get("TELEGRAM_PRIVATE_GROUP_ID") ?? "";
const db = createClient(supabaseUrl, serviceKey);

async function tg(method:string, body:Record<string,unknown>) {
  const r=await fetch(`https://api.telegram.org/bot${token}/${method}`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});
  const j=await r.json(); if(!j.ok) console.error("Telegram API error",method,j); return j;
}
const keyboard=(rows:string[][])=>({keyboard:rows.map(r=>r.map(text=>({text}))),resize_keyboard:true,is_persistent:true});
const homeKb=(staff=false)=>keyboard([["📢 تبلیغات گروه","📣 تبلیغات چنل"],["📦 سفارش‌های من","👤 حساب کاربری"],["💬 پشتیبانی","📖 راهنما"],...(staff?[["⚙️ پنل مدیریت"]]:[])]);
const adminKb=(p:Record<string,any>)=>keyboard([
  ...(can(p,"orders_read")||can(p,"orders_update")?[["📋 سفارش‌ها"]]:[]),
  ...(can(p,"payments_review")?[["💳 بررسی پرداخت‌ها"]]:[]),
  ...(can(p,"support_read")?[["🎫 تیکت‌های پشتیبانی"]]:[]),
  ...(can(p,"packages_manage")?[["📦 مدیریت پکیج‌ها"]]:[]),
  ...(can(p,"wallets_manage")?[["👛 روش‌های پرداخت"]]:[]),
  ...(p.role==="owner"?[["👥 مدیران و دسترسی‌ها"],["📊 گزارش کلی"]]:[]),
  ...(p.role==="developer"||can(p,"technical_read")?[["🛠 وضعیت فنی"]]:[]),
  ["🏠 منوی اصلی"]
]);
const can=(p:Record<string,any>,permission:string)=>p.role==="owner"||(p.role==="admin"&&p.permissions?.[permission]===true)||(p.role==="developer"&&["technical_read","technical_settings"].includes(permission));
const backKb=keyboard([["🔙 بازگشت","🏠 منوی اصلی"]]);
async function send(chat_id:number,text:string,reply_markup?:unknown,extra:Record<string,unknown>={}) {
  const customEmojiId=Deno.env.get("PREMIUM_EMOJI_DECORATION_ID")??"";
  const safeId=/^\d+$/.test(customEmojiId)?customEmojiId:"";
  const decorated=safeId?`<tg-emoji emoji-id="${safeId}">✨</tg-emoji> ${text}`:text;
  return tg("sendMessage",{chat_id,text:decorated,parse_mode:"HTML",...(reply_markup?{reply_markup}:{}),...extra});
}
async function session(uid:string,chat:string) {
  const {data}=await db.from("telegram_sessions").select("state,data").eq("telegram_user_id",uid).maybeSingle();
  return data ?? {state:"home",data:{}};
}
async function setSession(uid:string,chat:string,state:string,data:Record<string,unknown>) {
  await db.from("telegram_sessions").upsert({telegram_user_id:uid,chat_id:chat,state,data,updated_at:new Date().toISOString()});
}
async function profile(uid:string,name:string,username?:string) {
  const {data}=await db.from("profiles").select("id,role,permissions").eq("telegram_id",uid).maybeSingle();
  if(data) {
    if(uid===ownerId) return {...data,role:"owner",permissions:data.permissions??{}};
    if(uid===developerId) return {...data,role:"developer",permissions:{}};
    return data;
  }
  // Telegram-only privileged accounts are resolved from server-side IDs.
  return {id:null,role:uid===ownerId?"owner":uid===developerId?"developer":"customer",permissions:{}};
}
async function notifyGroup(text:string) { if(groupId) await send(Number(groupId),text); }
async function startOrder(chat:number,uid:string,categorySlug:string,categoryName:string) {
  const {data:products}=await db.from("products").select("id,name,slug,product_type").eq("active",true).eq("category_id",(await db.from("categories").select("id").eq("slug",categorySlug).single()).data?.id).order("sort_order");
  if(!products?.length) return send(chat,"در حال حاضر محصول فعالی در این دسته وجود ندارد.",homeKb());
  await setSession(uid,String(chat),"choose_product",{categorySlug,categoryName,products});
  return send(chat,`<b>${categoryName}</b>\nنوع تبلیغات را انتخاب کنید:`,keyboard([["جوین اجباری","بنر ۲۴ ساعته"],["🔙 بازگشت","🏠 منوی اصلی"]]));
}
async function handle(msg:TgMessage) {
  const chat=msg.chat.id, uid=String(msg.from.id), text=msg.text?.trim()??"";
  const p=await profile(uid,msg.from.first_name??"",msg.from.username);
  const isAdmin=p.role==="owner"||p.role==="admin"||p.role==="developer";
  if(text==="/id") return send(chat,`شناسه تلگرام شما: <code>${uid}</code>`,homeKb(isAdmin));
  if(text==="/start"||text==="🏠 منوی اصلی") {
    await setSession(uid,String(chat),"home",{});
    return send(chat,"<b>✦ به AdServiceBot خوش آمدید</b>\n\nاز اینجا می‌توانید خدمات تبلیغاتی را انتخاب کنید، سفارش بسازید و وضعیت سفارش‌ها و پرداخت‌هایتان را پیگیری کنید.\n\n<b>برای شروع، یکی از گزینه‌ها را انتخاب کنید:</b>",homeKb(isAdmin));
  }
  const s=await session(uid,String(chat)); const d=s.data??{};

  if(text==="🔙 بازگشت") {
    if(s.state==="choose_product") { await setSession(uid,String(chat),"home",{}); return send(chat,"به منوی اصلی برگشتید.",homeKb(isAdmin)); }
    if(s.state==="choose_package") { await setSession(uid,String(chat),"choose_product",d); return send(chat,"نوع خدمت را انتخاب کنید:",keyboard([["جوین اجباری","بنر ۲۴ ساعته"],["🔙 بازگشت","🏠 منوی اصلی"]])); }
    if(["collect_details","force_destination"].includes(s.state)) { await setSession(uid,String(chat),"choose_package",d); const packs=(d.packages as Array<Record<string,unknown>>)||[]; return send(chat,"پکیج را دوباره انتخاب کنید:",keyboard([...packs.map(x=>[`${x.title} — ${x.price} ${x.currency}`]),["🔙 بازگشت","🏠 منوی اصلی"]])); }
    if(s.state==="force_join_link") { await setSession(uid,String(chat),"force_destination",d); return send(chat,"لینک مقصد تبلیغ را ارسال کنید:",backKb); }
    if(s.state==="confirm_order") { await setSession(uid,String(chat),"choose_package",d); const packs=(d.packages as Array<Record<string,unknown>>)||[]; return send(chat,"برای اصلاح سفارش، پکیج را دوباره انتخاب کنید:",keyboard([...packs.map(x=>[`${x.title} — ${x.price} ${x.currency}`]),["🔙 بازگشت","🏠 منوی اصلی"]])); }
    if(s.state==="submit_txid") { await setSession(uid,String(chat),"select_payment",d); const methods=(d.methods as Array<Record<string,unknown>>)||[]; return send(chat,"روش پرداخت را انتخاب کنید:",keyboard([...methods.map(m=>[`${m.title} — ${m.network}`]),["🔙 بازگشت","🏠 منوی اصلی"]])); }
    await setSession(uid,String(chat),"home",{}); return send(chat,"به منوی اصلی برگشتید.",homeKb(isAdmin));
  }

  if(text==="📢 تبلیغات گروه") return startOrder(chat,uid,"group-advertising","تبلیغات گروه");
  if(text==="📣 تبلیغات چنل") return startOrder(chat,uid,"channel-advertising","تبلیغات چنل");
  if(text==="📦 سفارش‌های من") {
    const {data:orders}=await db.from("orders").select("order_number,status,total_amount,currency,created_at").eq("telegram_user_id",uid).order("created_at",{ascending:false}).limit(10);
    const lines=(orders??[]).map(o=>`• <b>${o.order_number}</b> — ${o.status} — ${o.total_amount??"—"} ${o.currency??""}`);
    return send(chat,lines.length?`<b>سفارش‌های اخیر شما</b>\n\n${lines.join("\n")}`:"هنوز سفارشی ثبت نکرده‌اید.",homeKb(isAdmin));
  }
  if(text==="👤 حساب کاربری") return send(chat,`<b>حساب کاربری</b>\nنام: ${msg.from.first_name??"—"}\nشناسه: <code>${uid}</code>\nنام کاربری: @${msg.from.username??"ندارد"}`,homeKb(isAdmin));
  if(text==="📖 راهنما") return send(chat,"<b>راهنمای ثبت سفارش</b>\n۱. دسته تبلیغاتی را انتخاب کنید.\n۲. نوع خدمت و پکیج را انتخاب کنید.\n۳. اطلاعات و لینک‌های لازم را ارسال کنید.\n۴. خلاصه سفارش را بررسی و تأیید کنید.\n۵. روش رمزارزی را انتخاب و TXID را ثبت کنید؛ پرداخت دستی بررسی می‌شود.",homeKb(isAdmin));
  if(text==="💬 پشتیبانی") { await setSession(uid,String(chat),"support",{}); return send(chat,"پیام خود را برای پشتیبانی ارسال کنید:",backKb); }
  if(text==="⚙️ پنل مدیریت") {
    if(!isAdmin) return send(chat,"شما دسترسی مدیریت ندارید.",homeKb(false));
    return send(chat,"<b>✦ پنل مدیریت AdServiceBot</b>\nاز منوی زیر بخش موردنظر را انتخاب کنید. دسترسی هر بخش بر اساس مجوز حساب شما کنترل می‌شود.",adminKb(p));
  }
  if(text==="🏠 منوی اصلی") { await setSession(uid,String(chat),"home",{}); return send(chat,"منوی اصلی",homeKb(isAdmin)); }
  if(text==="📊 گزارش کلی") {
    if(!can(p,"orders_read")) return send(chat,"دسترسی غیرمجاز.",adminKb(p));
    const [{count:orders},{count:pending},{count:payments},{count:customers}]=await Promise.all([
      db.from("orders").select("id",{count:"exact",head:true}),
      db.from("orders").select("id",{count:"exact",head:true}).in("status",["awaiting_payment","payment_under_review","queued","in_progress"]),
      db.from("payment_submissions").select("id",{count:"exact",head:true}).eq("status","under_review"),
      db.from("telegram_sessions").select("telegram_user_id",{count:"exact",head:true})
    ]);
    return send(chat,`<b>📊 گزارش کلی</b>\nکل سفارش‌ها: ${orders??0}\nسفارش‌های باز: ${pending??0}\nپرداخت‌های در انتظار بررسی: ${payments??0}\nکاربران تلگرام ثبت‌شده در نشست‌ها: ${customers??0}`,adminKb(p));
  }
  if(text==="📋 سفارش‌ها"||text==="📋 سفارش‌های در انتظار"||text==="/orders") {
    if(!can(p,"orders_read")) return send(chat,"دسترسی غیرمجاز.",adminKb(p));
    const {data}=await db.from("orders").select("id,order_number,status,total_amount,currency,product,telegram_user_id").order("created_at",{ascending:false}).limit(15);
    if(!data?.length) return send(chat,"سفارشی ثبت نشده است.",adminKb(p));
    await setSession(uid,String(chat),"admin_orders",{orders:data});
    return send(chat,"<b>📋 آخرین سفارش‌ها</b>\nبرای مشاهده و تغییر وضعیت، یک سفارش را انتخاب کنید:",keyboard([...data.map(x=>[`${x.order_number} | ${x.status}`]),["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(text==="💳 بررسی پرداخت‌ها"||text==="💳 پرداخت‌های بررسی‌نشده"||text==="/payments") {
    if(!can(p,"payments_review")) return send(chat,"دسترسی غیرمجاز.",adminKb(p));
    const {data}=await db.from("payment_submissions").select("id,order_id,txid,expected_amount,status,created_at,orders(order_number,telegram_user_id,total_amount,currency)").eq("status","under_review").order("created_at",{ascending:false}).limit(15);
    if(!data?.length) return send(chat,"پرداخت بررسی‌نشده‌ای وجود ندارد.",adminKb(p));
    await setSession(uid,String(chat),"admin_payments",{payments:data});
    return send(chat,"<b>💳 پرداخت‌های در انتظار بررسی</b>\nیک پرداخت را انتخاب کنید:",keyboard([...data.map(x=>[`پرداخت ${String(x.id).slice(0,8)} | ${x.orders?.order_number??"سفارش"}`]),["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(text==="🎫 تیکت‌های پشتیبانی") {
    if(!can(p,"support_read")) return send(chat,"دسترسی غیرمجاز.",adminKb(p));
    const {data}=await db.from("support_tickets").select("id,ticket_number,subject,status,telegram_user_id,created_at").neq("status","closed").order("created_at",{ascending:false}).limit(15);
    if(!data?.length) return send(chat,"تیکت بازی وجود ندارد.",adminKb(p));
    await setSession(uid,String(chat),"admin_tickets",{tickets:data});
    return send(chat,"<b>🎫 تیکت‌های باز</b>\nیک تیکت را انتخاب کنید:",keyboard([...data.map(x=>[`${x.ticket_number} | ${x.status}`]),["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(text==="📦 مدیریت پکیج‌ها") {
    if(!can(p,"packages_manage")) return send(chat,"دسترسی غیرمجاز.",adminKb(p));
    const {data}=await db.from("packages").select("title,price,currency,active,products(name)").order("created_at",{ascending:false}).limit(30);
    return send(chat,"<b>📦 پکیج‌های ثبت‌شده</b>\n"+(data??[]).map(x=>`${x.active?"🟢":"⚪"} ${x.products?.name??"خدمت"} — ${x.title}: ${x.price} ${x.currency}`).join("\n")+"\n\nمدیریت افزودن و ویرایش پکیج از طریق گفت‌وگوی مدیریتی در نسخه بعدی فعال می‌شود.",adminKb(p));
  }
  if(text==="👛 روش‌های پرداخت") {
    if(!can(p,"wallets_manage")) return send(chat,"دسترسی غیرمجاز.",adminKb(p));
    const {data}=await db.from("crypto_methods").select("title,currency_code,network,wallet_address,active").order("sort_order");
    return send(chat,"<b>👛 روش‌های پرداخت</b>\n"+(data??[]).map(x=>`${x.active?"🟢":"⚪"} ${x.title} | ${x.currency_code} | ${x.network}\n<code>${x.wallet_address}</code>`).join("\n\n")||"روشی ثبت نشده است.",adminKb(p));
  }
  if(text==="👥 مدیران و دسترسی‌ها") {
    if(p.role!=="owner") return send(chat,"فقط Owner به مدیریت مدیران دسترسی دارد.",adminKb(p));
    const {data}=await db.from("profiles").select("id,telegram_id,display_name,role,permissions").in("role",["admin","developer"]).limit(30);
    return send(chat,"<b>👥 مدیران و دسترسی‌ها</b>\n"+(data??[]).map(x=>`${x.display_name??"بدون نام"} | ${x.role} | TG: ${x.telegram_id??"—"}\nمجوزها: ${JSON.stringify(x.permissions??{})}`).join("\n\n")||"مدیری ثبت نشده است.",adminKb(p));
  }
  if(text==="🛠 وضعیت فنی") {
    if(p.role!=="developer"&&p.role!=="owner"&&!can(p,"technical_read")) return send(chat,"دسترسی غیرمجاز.",adminKb(p));
    const [{count:orders},{count:tickets}]=await Promise.all([db.from("orders").select("id",{count:"exact",head:true}),db.from("support_tickets").select("id",{count:"exact",head:true})]);
    return send(chat,`<b>🛠 وضعیت فنی</b>\nاتصال دیتابیس: برقرار\nتعداد سفارش‌ها: ${orders??0}\nتعداد تیکت‌ها: ${tickets??0}`,adminKb(p));
  }
  if(s.state==="admin_orders") {
    const chosen=(d.orders as Array<Record<string,any>>)?.find(x=>text.startsWith(String(x.order_number)));
    if(!chosen) return send(chat,"یک سفارش از فهرست انتخاب کنید.",backKb);
    await setSession(uid,String(chat),"admin_order_status",{order:chosen});
    return send(chat,`<b>سفارش ${chosen.order_number}</b>\nوضعیت فعلی: ${chosen.status}\nمحصول: ${chosen.product??"—"}\nمبلغ: ${chosen.total_amount??"—"} ${chosen.currency??""}\nکاربر: ${chosen.telegram_user_id??"—"}\n\nوضعیت جدید را انتخاب کنید:`,keyboard([["paid","queued"],["in_progress","completed"],["cancelled"],["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(s.state==="admin_order_status") {
    const allowed=["paid","queued","in_progress","completed","cancelled"];
    if(!allowed.includes(text)) return send(chat,"یک وضعیت معتبر انتخاب کنید.",backKb);
    if(!can(p,"orders_update")) return send(chat,"مجوز تغییر وضعیت سفارش را ندارید.",adminKb(p));
    const order=d.order as Record<string,any>;
    const {error}=await db.from("orders").update({status:text,completed_at:text==="completed"?new Date().toISOString():null}).eq("id",order.id);
    if(error) return send(chat,"تغییر وضعیت ناموفق بود: "+error.message,adminKb(p));
    await db.from("order_status_history").insert({order_id:order.id,old_status:order.status,new_status:text,note:`Changed by Telegram admin ${uid}`});
    if(order.telegram_user_id) await send(Number(order.telegram_user_id),`وضعیت سفارش <b>${order.order_number}</b> به <b>${text}</b> تغییر کرد.`);
    await db.from("audit_logs").insert({action:"telegram_order_status",target_type:"order",target_id:order.id,metadata:{telegram_admin_id:uid,status:text}});
    await setSession(uid,String(chat),"home",{}); return send(chat,"وضعیت سفارش به‌روزرسانی شد.",adminKb(p));
  }
  if(s.state==="admin_payments") {
    const payment=(d.payments as Array<Record<string,any>>)?.find(x=>text.includes(String(x.id).slice(0,8)));
    if(!payment) return send(chat,"یک پرداخت از فهرست انتخاب کنید.",backKb);
    await setSession(uid,String(chat),"admin_payment_review",{payment});
    return send(chat,`<b>بررسی پرداخت</b>\nسفارش: ${payment.orders?.order_number??payment.order_id}\nمبلغ مورد انتظار: ${payment.expected_amount??payment.orders?.total_amount??"—"}\nTXID: <code>${payment.txid}</code>\n\nنتیجه بررسی را انتخاب کنید:`,keyboard([["✅ تأیید پرداخت","❌ رد پرداخت"],["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(s.state==="admin_payment_review") {
    if(!["✅ تأیید پرداخت","❌ رد پرداخت"].includes(text)) return send(chat,"نتیجه بررسی را انتخاب کنید.",backKb);
    if(!can(p,"payments_review")) return send(chat,"مجوز بررسی پرداخت ندارید.",adminKb(p));
    const payment=d.payment as Record<string,any>, approved=text==="✅ تأیید پرداخت", status=approved?"approved":"rejected";
    const {data:updated,error}=await db.from("payment_submissions").update({status,review_note:`Reviewed by Telegram admin ${uid}`,reviewed_at:new Date().toISOString()}).eq("id",payment.id).eq("status","under_review").select("id").maybeSingle();
    if(error||!updated) return send(chat,"این پرداخت قبلاً بررسی شده یا خطایی رخ داده است.",adminKb(p));
    await db.from("orders").update({payment_state:status,status:approved?"queued":"payment_rejected"}).eq("id",payment.order_id);
    const order=payment.orders??{}; if(order.telegram_user_id) await send(Number(order.telegram_user_id),`پرداخت سفارش <b>${order.order_number??""}</b> ${approved?"تأیید شد و سفارش در صف اجرا قرار گرفت.":"رد شد. برای راهنمایی با پشتیبانی تماس بگیرید."}`);
    await db.from("audit_logs").insert({action:"telegram_payment_review",target_type:"payment",target_id:payment.id,metadata:{telegram_admin_id:uid,status}});
    await setSession(uid,String(chat),"home",{}); return send(chat,approved?"پرداخت تأیید شد.":"پرداخت رد شد.",adminKb(p));
  }
  if(s.state==="admin_tickets") {
    const ticket=(d.tickets as Array<Record<string,any>>)?.find(x=>text.startsWith(String(x.ticket_number)));
    if(!ticket) return send(chat,"یک تیکت از فهرست انتخاب کنید.",backKb);
    const {data:messages}=await db.from("support_messages").select("sender_type,body,created_at").eq("ticket_id",ticket.id).order("created_at").limit(20);
    await setSession(uid,String(chat),"admin_ticket_reply",{ticket});
    return send(chat,`<b>${ticket.ticket_number}</b> | ${ticket.status}\nموضوع: ${ticket.subject}\nکاربر: ${ticket.telegram_user_id??"—"}\n\n`+(messages??[]).map(m=>`${m.sender_type}: ${m.body}`).join("\n")+"\n\nپاسخ خود را ارسال کنید یا /close_ticket بزنید.",backKb);
  }
  if(s.state==="admin_ticket_reply") {
    const ticket=d.ticket as Record<string,any>;
    if(text==="/close_ticket") { await db.from("support_tickets").update({status:"closed"}).eq("id",ticket.id); await setSession(uid,String(chat),"home",{}); return send(chat,"تیکت بسته شد.",adminKb(p)); }
    if(!can(p,"support_read")) return send(chat,"مجوز پاسخ‌گویی ندارید.",adminKb(p));
    await db.from("support_messages").insert({ticket_id:ticket.id,sender_type:"admin",sender_id:uid,body:text});
    await db.from("support_tickets").update({status:"answered"}).eq("id",ticket.id);
    if(ticket.telegram_user_id) await send(Number(ticket.telegram_user_id),`پاسخ پشتیبانی برای تیکت <b>${ticket.ticket_number}</b>:\n${text}`);
    await setSession(uid,String(chat),"home",{}); return send(chat,"پاسخ برای کاربر ارسال شد.",adminKb(p));
  }

  if(s.state==="choose_product") {
    const product=(d.products as Array<Record<string,unknown>>)?.find(x=>String(x.name)===text || (x.product_type==="force_join"&&text.includes("جوین")) || (x.product_type==="banner_24h"&&text.includes("بنر")));
    if(!product) return send(chat,"یکی از دو خدمت نمایش‌داده‌شده را انتخاب کنید.",backKb);
    const {data:packages}=await db.from("packages").select("id,title,description,price,currency,duration_hours,conditions").eq("product_id",product.id).eq("active",true).order("sort_order");
    if(!packages?.length) return send(chat,"برای این خدمت هنوز پکیجی تعریف نشده است. لطفاً بعداً مراجعه کنید.",homeKb());
    await setSession(uid,String(chat),"choose_package",{...d,product,packages});
    return send(chat,`<b>${product.name}</b>\nپکیج موردنظر را انتخاب کنید:`,keyboard([...packages.map(x=>[`${x.title} — ${x.price} ${x.currency}`]),["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(s.state==="choose_package") {
    const pack=(d.packages as Array<Record<string,unknown>>)?.find(x=>text.startsWith(String(x.title)));
    if(!pack) return send(chat,"یک پکیج معتبر انتخاب کنید.",backKb);
    const force=String((d.product as Record<string,unknown>)?.product_type)==="force_join";
    await setSession(uid,String(chat),force?"force_destination":"collect_details",{...d,pack,details:{}});
    return send(chat,force?"ابتدا لینک مقصد تبلیغ را ارسال کنید:":"تصویر بنر را به‌صورت عکس ارسال کنید؛ یا توضیحات و لینک محل انتشار را بنویسید.",backKb);
  }
  if(s.state==="force_destination") {
    if(!text) return send(chat,"لطفاً لینک مقصد تبلیغ را به‌صورت متن ارسال کنید.",backKb);
    await setSession(uid,String(chat),"force_join_link",{...d,details:{destination_link:text}});
    return send(chat,"حالا لینک کانال یا گروهی را ارسال کنید که کاربران باید ابتدا عضو آن شوند:",backKb);
  }
  if(s.state==="force_join_link") {
    if(!text) return send(chat,"لطفاً لینک کانال/گروه عضویت اجباری را ارسال کنید.",backKb);
    const details={...(d.details as Record<string,unknown>),required_membership_link:text};
    const pack=d.pack as Record<string,unknown>, product=d.product as Record<string,unknown>;
    await setSession(uid,String(chat),"confirm_order",{...d,details});
    return send(chat,`<b>پیش‌نمایش سفارش</b>\nدسته: ${d.categoryName}\nخدمت: ${product.name}\nپکیج: ${pack.title}\nمبلغ: ${pack.price} ${pack.currency}\nمقصد تبلیغ: ${details.destination_link}\nلینک عضویت اجباری: ${details.required_membership_link}\n\nآیا سفارش را تأیید می‌کنید؟`,keyboard([["✅ تأیید سفارش"],["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(s.state==="collect_details") {
    const details={...(d.details as Record<string,unknown>),submission:text||msg.caption||"",media_file_id:msg.photo?.at(-1)?.file_id??msg.document?.file_id??null};
    if(!details.media_file_id&&!details.submission) return send(chat,"لطفاً فایل بنر یا توضیحات انتشار را ارسال کنید.",backKb);
    const product=d.product as Record<string,unknown>, pack=d.pack as Record<string,unknown>;
    await setSession(uid,String(chat),"confirm_order",{...d,details});
    return send(chat,`<b>پیش‌نمایش سفارش</b>\nدسته: ${d.categoryName}\nخدمت: ${product.name}\nپکیج: ${pack.title}\nمبلغ: ${pack.price} ${pack.currency}\nتوضیحات: ${details.submission||"—"}\nفایل بنر: ${details.media_file_id?"دریافت شد":"ارسال نشده"}\n\nآیا سفارش را تأیید می‌کنید؟`,keyboard([["✅ تأیید سفارش"],["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(s.state==="confirm_order") {
    if(text!=="✅ تأیید سفارش") return send(chat,"برای ثبت نهایی، دکمه تأیید سفارش را بزنید.",keyboard([["✅ تأیید سفارش"],["🔙 بازگشت","🏠 منوی اصلی"]]));
    const product=d.product as Record<string,unknown>, pack=d.pack as Record<string,unknown>;
    const {data:profileRow}=await db.from("profiles").select("id").eq("telegram_id",uid).maybeSingle();
    const {data:order,error}=await db.from("orders").insert({customer_id:profileRow?.id??null,telegram_user_id:uid,category:d.categoryName,product:product.name,package_id:pack.id,package_snapshot:pack,order_details:d.details??{},total_amount:pack.price,currency:pack.currency,status:"awaiting_payment",payment_state:"not_submitted"}).select("id,order_number").single();
    if(error) { console.error(error); return send(chat,"ثبت سفارش با خطا مواجه شد. لطفاً با پشتیبانی تماس بگیرید.",homeKb()); }
    await db.from("order_status_history").insert({order_id:order.id,new_status:"awaiting_payment",note:"Order confirmed from Telegram bot"});
    const {data:methods}=await db.from("crypto_methods").select("id,title,currency_code,network").eq("active",true).order("sort_order");
    await notifyGroup(`<b>سفارش جدید</b>\n${order.order_number}\nکاربر: ${uid}\nمحصول: ${product.name}\nمبلغ: ${pack.price} ${pack.currency}`);
    if(!methods?.length) { await setSession(uid,String(chat),"home",{}); return send(chat,`سفارش <code>${order.order_number}</code> ثبت شد؛ روش پرداخت هنوز تنظیم نشده است.`,homeKb()); }
    await setSession(uid,String(chat),"select_payment",{orderId:order.id,orderNumber:order.order_number,amount:pack.price,currency:pack.currency,methods});
    return send(chat,`<b>سفارش ثبت شد</b>\nشماره: <code>${order.order_number}</code>\nمبلغ: ${pack.price} ${pack.currency}\nروش پرداخت را انتخاب کنید:`,keyboard([...methods.map(m=>[`${m.title} — ${m.network}`]),["🔙 بازگشت","🏠 منوی اصلی"]]));
  }
  if(s.state==="select_payment") {
    const method=(d.methods as Array<Record<string,unknown>>)?.find(m=>text.startsWith(String(m.title)));
    if(!method) return send(chat,"یکی از روش‌های پرداخت نمایش‌داده‌شده را انتخاب کنید.",backKb);
    const {data:wallet}=await db.from("crypto_methods").select("id,title,currency_code,network,wallet_address,instructions").eq("id",method.id).single();
    if(!wallet) return send(chat,"روش پرداخت در دسترس نیست.",homeKb());
    await setSession(uid,String(chat),"submit_txid",{...d,methodId:wallet.id,wallet});
    return send(chat,`<b>اطلاعات پرداخت</b>\nارز: ${wallet.currency_code}\nشبکه: ${wallet.network}\nمبلغ: ${d.amount} ${d.currency}\nآدرس کیف پول:\n<code>${wallet.wallet_address}</code>\n${wallet.instructions??""}\n\nپس از پرداخت، TXID تراکنش را ارسال کنید. پرداخت به‌صورت دستی بررسی می‌شود.`,backKb);
  }
  if(s.state==="submit_txid") {
    if(text.length<8) return send(chat,"TXID معتبر را ارسال کنید.",backKb);
    const wallet=d.wallet as Record<string,unknown>;
    const {error}=await db.from("payment_submissions").insert({order_id:d.orderId,customer_id:null,crypto_method_id:d.methodId,txid:text,expected_amount:d.amount,payment_method_snapshot:wallet,status:"under_review"});
    if(error) { console.error(error); return send(chat,"ثبت TXID ناموفق بود؛ لطفاً با پشتیبانی تماس بگیرید.",homeKb()); }
    await db.from("orders").update({status:"payment_under_review",payment_state:"under_review"}).eq("id",d.orderId);
    await setSession(uid,String(chat),"home",{});
    await notifyGroup(`<b>پرداخت برای بررسی ارسال شد</b>\nسفارش: ${d.orderNumber}\nکاربر: ${uid}\nTXID: ${text}`);
    return send(chat,"TXID ثبت شد و پرداخت شما در صف بررسی دستی قرار گرفت. پس از بررسی نتیجه اطلاع‌رسانی می‌شود.",homeKb());
  }
  if(s.state==="support") {
    const {data:ticket,error}=await db.from("support_tickets").insert({telegram_user_id:uid,subject:text.slice(0,100)||"درخواست پشتیبانی"}).select("id,ticket_number").single();
    if(!error&&ticket) await db.from("support_messages").insert({ticket_id:ticket.id,sender_type:"customer",sender_id:uid,body:text});
    await notifyGroup(`<b>تیکت پشتیبانی جدید</b>\n${ticket?.ticket_number??""}\nکاربر: ${uid}\n${text}`);
    await setSession(uid,String(chat),"home",{}); return send(chat,"پیام شما برای پشتیبانی ثبت شد. تیم ما بررسی می‌کند.",homeKb());
  }
  return send(chat,"لطفاً از دکمه‌های منو استفاده کنید.",homeKb(isAdmin));
}
serve(async(req)=>{
  if(req.method==="GET") return new Response("AdServiceBot webhook is online",{status:200});
  if(req.method!=="POST") return new Response("Method not allowed",{status:405});
  if(!token||!secret||!supabaseUrl||!serviceKey) return new Response("Server configuration missing",{status:500});
  if(req.headers.get("x-telegram-bot-api-secret-token")!==secret) return new Response("Unauthorized",{status:401});
  try { const update=await req.json(); if(update.message) await handle(update.message as TgMessage); return new Response("ok"); }
  catch(e) { console.error("Webhook failed",e); return new Response("Internal error",{status:500}); }
});

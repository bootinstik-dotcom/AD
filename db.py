import os, sqlite3, json, shutil, tempfile
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.getenv("DB_PATH", "/data/adservice.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
# If Railway's persistent volume is empty, automatically seed it from the
# bundled verified backup. Existing databases are never overwritten.
SEED_DB_PATH = Path(__file__).with_name("boostly-backup.sqlite3")
if not DB_PATH.exists() and SEED_DB_PATH.exists():
    shutil.copy2(SEED_DB_PATH, DB_PATH)

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    return c

def init_db(owner_id: int, developer_id: int):
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, role TEXT NOT NULL DEFAULT 'customer',
          active INTEGER NOT NULL DEFAULT 1, balance REAL NOT NULL DEFAULT 0, balance_ton REAL NOT NULL DEFAULT 0, blocked INTEGER NOT NULL DEFAULT 0, block_reason TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS categories(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
          sort_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS products(
          id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL REFERENCES categories(id),
          title TEXT NOT NULL, kind TEXT NOT NULL, description TEXT DEFAULT '',
          sort_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS packages(
          id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL REFERENCES products(id),
          title TEXT NOT NULL, description TEXT DEFAULT '', price TEXT NOT NULL, currency TEXT NOT NULL,
          duration TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS payment_methods(
          id INTEGER PRIMARY KEY AUTOINCREMENT, currency TEXT NOT NULL, network TEXT NOT NULL,
          address TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders(
          id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT UNIQUE NOT NULL,
          user_id INTEGER NOT NULL REFERENCES users(id), product_id INTEGER NOT NULL,
          package_id INTEGER NOT NULL, product_title TEXT NOT NULL, package_title TEXT NOT NULL,
          price TEXT NOT NULL, currency TEXT NOT NULL, details TEXT NOT NULL,
          status TEXT NOT NULL, payment_status TEXT NOT NULL DEFAULT 'unpaid',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS payments(
          id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL REFERENCES orders(id),
          method_id INTEGER NOT NULL, txid TEXT NOT NULL, receipt_file_id TEXT, memo TEXT DEFAULT '',
          status TEXT NOT NULL DEFAULT 'under_review', reviewer_id INTEGER, review_note TEXT,
          created_at TEXT NOT NULL, reviewed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS tickets(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
          subject TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ticket_messages(
          id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER NOT NULL REFERENCES tickets(id),
          sender_id INTEGER NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(
          id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INTEGER, action TEXT NOT NULL,
          entity TEXT, entity_id TEXT, meta TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS channel_submissions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, target_type TEXT NOT NULL DEFAULT 'channel',
          invite_link TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', admin_note TEXT DEFAULT '',
          created_at TEXT NOT NULL, reviewed_at TEXT, reviewer_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS wallet_ledger(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL,
          currency TEXT NOT NULL DEFAULT 'USDT', kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          description TEXT DEFAULT '', created_at TEXT NOT NULL, reviewer_id INTEGER, reviewed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS order_followups(
          id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT NOT NULL, user_id INTEGER NOT NULL,
          message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
          group_message_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS group_message_links(
          group_message_id INTEGER PRIMARY KEY, kind TEXT NOT NULL, ref_id TEXT NOT NULL, user_id INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS custom_channel_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, channel_link TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, reviewed_at TEXT, reviewer_id INTEGER, note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS referrals(
          id INTEGER PRIMARY KEY AUTOINCREMENT, inviter_id INTEGER NOT NULL, invitee_id INTEGER NOT NULL UNIQUE,
          valid INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS campaigns(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, prize TEXT NOT NULL,
          winners_count INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 0,
          captcha_required INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, ended_at TEXT
        );
        CREATE TABLE IF NOT EXISTS campaign_winners(
          id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
          rank INTEGER NOT NULL, prize TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS campaign_rank_prizes(
          id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
          rank INTEGER NOT NULL, prize TEXT NOT NULL, UNIQUE(campaign_id,rank)
        );
        CREATE TABLE IF NOT EXISTS mandatory_channels(
          id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, title TEXT NOT NULL,
          join_url TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS private_channels(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, channel_link TEXT NOT NULL,
          created_at TEXT NOT NULL, UNIQUE(user_id,channel_link)
        );
        CREATE TABLE IF NOT EXISTS bonuses(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, amount REAL NOT NULL,
          capacity INTEGER NOT NULL, claimed_count INTEGER NOT NULL DEFAULT 0,
          start_at TEXT NOT NULL, end_at TEXT DEFAULT '', token TEXT NOT NULL UNIQUE,
          active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bonus_claims(
          id INTEGER PRIMARY KEY AUTOINCREMENT, bonus_id INTEGER NOT NULL REFERENCES bonuses(id),
          user_id INTEGER NOT NULL, amount REAL NOT NULL, claimed_at TEXT NOT NULL,
          UNIQUE(bonus_id,user_id)
        );
        """)
        # Lightweight migrations for databases created by earlier releases.
        payment_cols={r['name'] for r in c.execute("PRAGMA table_info(payments)").fetchall()}
        if 'memo' not in payment_cols:
            c.execute("ALTER TABLE payments ADD COLUMN memo TEXT DEFAULT ''")
        user_cols={r['name'] for r in c.execute("PRAGMA table_info(users)").fetchall()}
        if 'balance' not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN balance REAL NOT NULL DEFAULT 0")
        if 'balance_ton' not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN balance_ton REAL NOT NULL DEFAULT 0")
        if 'blocked' not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN blocked INTEGER NOT NULL DEFAULT 0")
        if 'block_reason' not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN block_reason TEXT DEFAULT ''")
        if 'game_points' not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN game_points INTEGER NOT NULL DEFAULT 0")
        c.execute('''CREATE TABLE IF NOT EXISTS game_plays(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, dice_value INTEGER NOT NULL,
          points INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)''')
        c.execute("INSERT OR IGNORE INTO categories(title,slug,sort_order) VALUES('تبلیغات گروه','group_ads',1)")
        c.execute("INSERT OR IGNORE INTO categories(title,slug,sort_order) VALUES('تبلیغات چنل','channel_ads',2)")
        c.execute("INSERT OR IGNORE INTO categories(title,slug,sort_order) VALUES('تبلیغات گیووای','giveaway_ads',3)")
        for cat in c.execute("SELECT id,slug FROM categories").fetchall():
            defaults = [("جوین اجباری","force_join",1),("بنر ۲۴ ساعته","banner_24h",2)]
            if cat["slug"] == "giveaway_ads":
                defaults = [("تبلیغات گیووای","giveaway",1)]
            for title,kind,order in defaults:
                c.execute("INSERT INTO products(category_id,title,kind,sort_order) SELECT ?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM products WHERE category_id=? AND kind=?)",
                          (cat["id"],title,kind,order,cat["id"],kind))
        c.execute("INSERT OR IGNORE INTO users(id,role,created_at) VALUES(?,?,?)",(owner_id,"owner",now()))
        c.execute("INSERT OR IGNORE INTO users(id,role,created_at) VALUES(?,?,?)",(developer_id,"developer",now()))
        c.execute("UPDATE users SET role='owner', active=1 WHERE id=?",(owner_id,))
        c.execute("UPDATE users SET role='developer', active=1 WHERE id=? AND id<>?",(developer_id,owner_id))

def upsert_user(tg_user):
    with conn() as c:
        c.execute("""INSERT INTO users(id,username,first_name,created_at) VALUES(?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name""",
        (tg_user.id,tg_user.username,tg_user.first_name or "",now()))

def user(uid):
    with conn() as c: return c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()

def is_staff(uid):
    u=user(uid); return bool(u and u["active"] and u["role"] in ("owner","admin","developer"))

def is_owner(uid):
    u=user(uid); return bool(u and u["active"] and u["role"]=="owner")

def is_privileged(uid):
    u=user(uid); return bool(u and u["active"] and u["role"] in ("owner", "developer"))

def products(category_id):
    with conn() as c: return c.execute("SELECT * FROM products WHERE category_id=? AND active=1 ORDER BY sort_order,id",(category_id,)).fetchall()

def categories():
    with conn() as c: return c.execute("SELECT * FROM categories WHERE active=1 ORDER BY sort_order,id").fetchall()

def packages(product_id):
    with conn() as c: return c.execute("SELECT * FROM packages WHERE product_id=? AND active=1 ORDER BY id",(product_id,)).fetchall()

def add_package(product_id,title,description,price,currency,duration):
    with conn() as c:
        c.execute("INSERT INTO packages(product_id,title,description,price,currency,duration,created_at) VALUES(?,?,?,?,?,?,?)",
                  (product_id,title,description,price,currency,duration,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def add_method(currency,network,address):
    if str(currency).upper() not in ("TON", "GRAM") or str(network).upper().replace(" ", "") not in ("TON", "TONMAINNET"):
        raise ValueError("Only TON on TON Mainnet is supported")
    with conn() as c:
        c.execute("UPDATE payment_methods SET active=0 WHERE active=1")
        c.execute("INSERT INTO payment_methods(currency,network,address,created_at) VALUES('TON','TON Mainnet',?,?)",(address,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def methods():
    with conn() as c: return c.execute("SELECT * FROM payment_methods WHERE active=1 AND upper(currency) IN ('TON','GRAM') AND lower(replace(network,' ','')) IN ('ton','tonmainnet') ORDER BY id DESC LIMIT 1").fetchall()

def remove_method(method_id=None):
    with conn() as c:
        if method_id is None: c.execute("UPDATE payment_methods SET active=0")
        else: c.execute("UPDATE payment_methods SET active=0 WHERE id=?",(method_id,))


def create_order(uid,product,pack,details):
    with conn() as c:
        order_no=f"BA{datetime.now().strftime('%y%m%d')}{os.urandom(2).hex().upper()}"
        c.execute("""INSERT INTO orders(order_no,user_id,product_id,package_id,product_title,package_title,price,currency,details,status,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,'awaiting_payment',?,?)""",
        (order_no,uid,product["id"],pack["id"],product["title"],pack["title"],pack["price"],pack["currency"],
         json.dumps(details,ensure_ascii=False),now(),now()))
        return c.execute("SELECT * FROM orders WHERE order_no=?",(order_no,)).fetchone()

def get_order(order_no):
    with conn() as c: return c.execute("SELECT * FROM orders WHERE order_no=?",(order_no,)).fetchone()

def user_orders(uid):
    with conn() as c: return c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 20",(uid,)).fetchall()

def all_orders(limit=30):
    with conn() as c: return c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?",(limit,)).fetchall()

def order_payment(order_id,method_id,txid,receipt,memo=''):
    with conn() as c:
        c.execute("INSERT INTO payments(order_id,method_id,txid,receipt_file_id,memo,created_at) VALUES(?,?,?,?,?,?)",
                  (order_id,method_id,txid,receipt,memo,now()))
        c.execute("UPDATE orders SET payment_status='under_review',status='payment_under_review',updated_at=? WHERE id=?",(now(),order_id))

def pending_payments():
    with conn() as c:
        return c.execute("""SELECT p.*,o.order_no,o.user_id,o.price,o.currency,o.package_title
        FROM payments p JOIN orders o ON o.id=p.order_id WHERE p.status='under_review' ORDER BY p.id""").fetchall()

def review_payment(pid,approved,reviewer,note=""):
    with conn() as c:
        p=c.execute("SELECT * FROM payments WHERE id=?",(pid,)).fetchone()
        if not p or p["status"]!="under_review": return None
        status="approved" if approved else "rejected"
        c.execute("UPDATE payments SET status=?,reviewer_id=?,review_note=?,reviewed_at=? WHERE id=?",
                  (status,reviewer,note,now(),pid))
        c.execute("UPDATE orders SET payment_status=?,status=?,updated_at=? WHERE id=?",
                  ("paid" if approved else "rejected", "queued" if approved else "payment_rejected",now(),p["order_id"]))
        return c.execute("SELECT * FROM orders WHERE id=?",(p["order_id"],)).fetchone()

def set_order_status(order_no,status,reason=None):
    with conn() as c:
        if reason is not None:
            row=c.execute("SELECT details FROM orders WHERE order_no=?",(order_no,)).fetchone()
            if row:
                try: details=json.loads(row["details"] or "{}")
                except Exception: details={}
                details["cancel_reason"]=reason
                c.execute("UPDATE orders SET details=? WHERE order_no=?",(json.dumps(details,ensure_ascii=False),order_no))
        c.execute("UPDATE orders SET status=?,updated_at=? WHERE order_no=?",(status,now(),order_no))
        return c.execute("SELECT * FROM orders WHERE order_no=?",(order_no,)).fetchone()

def add_ticket(uid,subject,body):
    with conn() as c:
        c.execute("INSERT INTO tickets(user_id,subject,created_at) VALUES(?,?,?)",(uid,subject,now()))
        tid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.execute("INSERT INTO ticket_messages(ticket_id,sender_id,body,created_at) VALUES(?,?,?,?)",(tid,uid,body,now()))
        return tid

def tickets():
    with conn() as c: return c.execute("SELECT * FROM tickets WHERE status='open' ORDER BY id DESC LIMIT 30").fetchall()

def set_setting(key,value):
    with conn() as c: c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))

def setting(key,default=""):
    with conn() as c:
        r=c.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return r["value"] if r else default

def add_admin(uid,role="admin"):
    with conn() as c:
        c.execute("INSERT INTO users(id,role,created_at) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET role=excluded.role,active=1",
                  (uid,role,now()))

def remove_admin(uid):
    with conn() as c: c.execute("UPDATE users SET active=0 WHERE id=? AND role<>'owner'",(uid,))

def audit(actor,action,entity=None,entity_id=None,meta=None):
    with conn() as c:
        c.execute("INSERT INTO audit(actor_id,action,entity,entity_id,meta,created_at) VALUES(?,?,?,?,?,?)",
                  (actor,action,entity,str(entity_id) if entity_id is not None else None,json.dumps(meta or {},ensure_ascii=False),now()))

def stats():
    with conn() as c:
        return {
          "users":c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"],
          "orders":c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"],
          "pending":c.execute("SELECT COUNT(*) n FROM payments WHERE status='under_review'").fetchone()["n"],
          "revenue":c.execute("SELECT COALESCE(SUM(CAST(price AS REAL)),0) n FROM orders WHERE payment_status='paid' AND currency='TON'").fetchone()["n"]
        }

def backup_file():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(suffix=".sqlite3"); os.close(fd)
    with conn() as src, sqlite3.connect(tmp) as dst:
        src.backup(dst)
    return tmp


# --- Boostly Ads extended operations ---
def submit_channel(uid, target_type, invite_link):
    with conn() as c:
        c.execute("INSERT INTO channel_submissions(user_id,target_type,invite_link,created_at) VALUES(?,?,?,?)",(uid,target_type,invite_link,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def pending_channels():
    with conn() as c: return c.execute("SELECT * FROM channel_submissions WHERE status='pending' ORDER BY id").fetchall()

def channel_submission(cid):
    with conn() as c: return c.execute("SELECT * FROM channel_submissions WHERE id=?",(cid,)).fetchone()

def review_channel(cid, approved, reviewer, note=''):
    with conn() as c:
        row=c.execute("SELECT * FROM channel_submissions WHERE id=? AND status='pending'",(cid,)).fetchone()
        if not row: return None
        c.execute("UPDATE channel_submissions SET status=?,reviewer_id=?,admin_note=?,reviewed_at=? WHERE id=?",
                  ('approved' if approved else 'rejected',reviewer,note,now(),cid))
        return row

def approved_channels(target_type=None):
    with conn() as c:
        if target_type: return c.execute("SELECT * FROM channel_submissions WHERE status='approved' AND target_type=? ORDER BY id DESC",(target_type,)).fetchall()
        return c.execute("SELECT * FROM channel_submissions WHERE status='approved' ORDER BY id DESC").fetchall()

def add_wallet_entry(uid, amount, currency, kind, status='pending', description=''):
    with conn() as c:
        c.execute("INSERT INTO wallet_ledger(user_id,amount,currency,kind,status,description,created_at) VALUES(?,?,?,?,?,?,?)",
                  (uid,amount,currency,kind,status,description,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def wallet_history(uid, limit=20):
    with conn() as c: return c.execute("SELECT * FROM wallet_ledger WHERE user_id=? ORDER BY id DESC LIMIT ?",(uid,limit)).fetchall()

def review_wallet_entry(entry_id, approved, reviewer):
    with conn() as c:
        row=c.execute("SELECT * FROM wallet_ledger WHERE id=? AND status='pending'",(entry_id,)).fetchone()
        if not row: return None
        status='approved' if approved else 'rejected'
        c.execute("UPDATE wallet_ledger SET status=?,reviewer_id=?,reviewed_at=? WHERE id=?",(status,reviewer,now(),entry_id))
        if approved and row['kind']=='deposit':
            col = 'balance_ton' if row['currency'].upper() == 'TON' else 'balance'
            c.execute(f"UPDATE users SET {col}={col}+? WHERE id=?",(row['amount'],row['user_id']))
        if row['kind']=='withdrawal' and str(row['description'] or '').startswith('RESERVED:') and not approved:
            col = 'balance_ton' if row['currency'].upper() == 'TON' else 'balance'
            c.execute(f"UPDATE users SET {col}={col}+? WHERE id=?",(row['amount'],row['user_id']))
        elif approved and row['kind']=='withdrawal' and not str(row['description'] or '').startswith('RESERVED:'):
            col = 'balance_ton' if row['currency'].upper() == 'TON' else 'balance'
            c.execute(f"UPDATE users SET {col}={col}-? WHERE id=?",(row['amount'],row['user_id']))
        return row

def create_followup(order_no, uid, message):
    with conn() as c:
        c.execute("INSERT INTO order_followups(order_no,user_id,message,created_at) VALUES(?,?,?,?)",(order_no,uid,message,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def add_group_link(message_id, kind, ref_id, uid):
    with conn() as c: c.execute("INSERT OR REPLACE INTO group_message_links(group_message_id,kind,ref_id,user_id) VALUES(?,?,?,?)",(message_id,kind,str(ref_id),uid))

def group_link(message_id):
    with conn() as c: return c.execute("SELECT * FROM group_message_links WHERE group_message_id=?",(message_id,)).fetchone()

def latest_ticket_message(ticket_id):
    with conn() as c: return c.execute("SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY id DESC LIMIT 1",(ticket_id,)).fetchone()

def add_ticket_message(ticket_id, sender_id, body):
    with conn() as c:
        c.execute("INSERT INTO ticket_messages(ticket_id,sender_id,body,created_at) VALUES(?,?,?,?)",(ticket_id,sender_id,body,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def ticket_by_id(ticket_id):
    with conn() as c: return c.execute("SELECT * FROM tickets WHERE id=?",(ticket_id,)).fetchone()

def report_snapshot():
    with conn() as c:
        return {
          'deposits':c.execute("SELECT COALESCE(SUM(amount),0) n FROM wallet_ledger WHERE kind='deposit' AND currency='TON' AND status='approved' AND julianday(created_at)>=julianday('now','-1 hour')").fetchone()['n'],
          'withdrawals':c.execute("SELECT COALESCE(SUM(amount),0) n FROM wallet_ledger WHERE kind='withdrawal' AND currency='TON' AND status='approved' AND julianday(created_at)>=julianday('now','-1 hour')").fetchone()['n'],
          'orders':c.execute("SELECT COUNT(*) n FROM orders WHERE julianday(created_at)>=julianday('now','-1 hour')").fetchone()['n'],
          'completed':c.execute("SELECT COUNT(*) n FROM orders WHERE status='completed' AND julianday(updated_at)>=julianday('now','-1 hour')").fetchone()['n'],
          'tickets':c.execute("SELECT COUNT(*) n FROM tickets WHERE julianday(created_at)>=julianday('now','-1 hour')").fetchone()['n']
        }


def add_product(category_id, title, kind, description=''):
    with conn() as c:
        c.execute("INSERT INTO products(category_id,title,kind,description,sort_order,active) VALUES(?,?,?,?,COALESCE((SELECT MAX(sort_order)+1 FROM products WHERE category_id=?),1),1)",(category_id,title,kind,description,category_id))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def deactivate_channel(cid):
    with conn() as c: c.execute("UPDATE channel_submissions SET status='removed' WHERE id=? AND status='approved'",(cid,))


# --- v3 user, TON wallet and giveaway operations ---
def find_user(identifier):
    with conn() as c:
        if str(identifier).startswith('@'):
            return c.execute("SELECT * FROM users WHERE lower(username)=lower(?)", (str(identifier)[1:],)).fetchone()
        try: uid=int(identifier)
        except (TypeError, ValueError): return None
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def set_user_blocked(uid, blocked, reason=''):
    with conn() as c:
        c.execute("UPDATE users SET blocked=?,block_reason=? WHERE id=?", (1 if blocked else 0, reason if blocked else '', uid))
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def adjust_ton_balance(uid, amount, kind, actor_id, description=''):
    with conn() as c:
        u=c.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
        if not u: return None
        if kind == 'deduction':
            cur=c.execute("SELECT balance_ton FROM users WHERE id=?", (uid,)).fetchone()['balance_ton']
            if float(cur) < float(amount): return False
            c.execute("UPDATE users SET balance_ton=balance_ton-? WHERE id=?", (amount,uid))
        else:
            c.execute("UPDATE users SET balance_ton=balance_ton+? WHERE id=?", (amount,uid))
        c.execute("INSERT INTO wallet_ledger(user_id,amount,currency,kind,status,description,created_at,reviewer_id,reviewed_at) VALUES(?,?,'TON',?,'approved',?,?,?,?)",
                  (uid,amount,kind,description or kind,now(),actor_id,now()))
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def user_order_history(uid, limit=50):
    with conn() as c: return c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?",(uid,limit)).fetchall()

def submit_custom_channel(uid, link):
    with conn() as c:
        c.execute("INSERT INTO custom_channel_requests(user_id,channel_link,created_at) VALUES(?,?,?)",(uid,link,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def custom_channel_request(rid):
    with conn() as c: return c.execute("SELECT * FROM custom_channel_requests WHERE id=?",(rid,)).fetchone()

def review_custom_channel(rid, reviewer, status='contacted', note=''):
    with conn() as c:
        row=c.execute("SELECT * FROM custom_channel_requests WHERE id=? AND status='pending'",(rid,)).fetchone()
        if not row: return None
        c.execute("UPDATE custom_channel_requests SET status=?,reviewer_id=?,reviewed_at=?,note=? WHERE id=?",(status,reviewer,now(),note,rid))
        return row

def users_recent(limit=50, offset=0):
    with conn() as c: return c.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",(limit,offset)).fetchall()

def users_all_ids():
    """All Telegram user IDs registered through /start."""
    with conn() as c:
        return [int(r["id"]) for r in c.execute("SELECT id FROM users ORDER BY created_at,id").fetchall()]


# Referral, campaign and forced-join persistence
def users_count():
    with conn() as c: return c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]

def user_full_profile(uid):
    with conn() as c:
        u=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
        if not u: return None
        return {"user":u,"orders":c.execute("SELECT COUNT(*) n FROM orders WHERE user_id=?",(uid,)).fetchone()["n"],"paid":c.execute("SELECT COALESCE(SUM(CAST(price AS REAL)),0) n FROM orders WHERE user_id=? AND payment_status='paid'",(uid,)).fetchone()["n"],"withdrawals":c.execute("SELECT COALESCE(SUM(amount),0) n FROM wallet_ledger WHERE user_id=? AND kind='withdrawal' AND status='approved'",(uid,)).fetchone()["n"],"referrals":c.execute("SELECT COUNT(*) n FROM referrals WHERE inviter_id=?",(uid,)).fetchone()["n"],"bonuses":c.execute("SELECT COUNT(*) n FROM bonus_claims WHERE user_id=?",(uid,)).fetchone()["n"],"ledger":c.execute("SELECT COUNT(*) n FROM wallet_ledger WHERE user_id=?",(uid,)).fetchone()["n"]}

def create_withdrawal(uid, amount, address):
    amount=float(amount)
    with conn() as c:
        c.execute("BEGIN IMMEDIATE")
        u=c.execute("SELECT balance_ton FROM users WHERE id=?",(uid,)).fetchone()
        if not u: c.rollback(); return (False,"user")
        minimum_row=c.execute("SELECT value FROM settings WHERE key='wallet_min_withdrawal'").fetchone()
        minimum=float(minimum_row["value"]) if minimum_row else 0.1
        if amount < minimum: c.rollback(); return (False,"minimum")
        if float(u["balance_ton"] or 0)<amount: c.rollback(); return (False,"balance")
        c.execute("UPDATE users SET balance_ton=balance_ton-? WHERE id=?",(amount,uid))
        c.execute("INSERT INTO wallet_ledger(user_id,amount,currency,kind,status,description,created_at) VALUES(?,?,'TON','withdrawal','pending',?,?)",(uid,amount,"RESERVED: withdrawal to "+str(address),now()))
        eid=c.execute("SELECT last_insert_rowid() id").fetchone()["id"]; c.commit(); return (True,eid)

def referral_link_user(inviter_id, invitee_id, valid=True):
    if inviter_id == invitee_id: return False
    with conn() as c:
        if not c.execute("SELECT 1 FROM users WHERE id=?",(inviter_id,)).fetchone(): return False
        cur=c.execute("INSERT OR IGNORE INTO referrals(inviter_id,invitee_id,valid,created_at) VALUES(?,?,?,?)",(inviter_id,invitee_id,1 if valid else 0,now()))
        return cur.rowcount > 0

def set_referral_valid(invitee_id, valid=True):
    with conn() as c: c.execute("UPDATE referrals SET valid=? WHERE invitee_id=?",(1 if valid else 0,invitee_id))

def referral_stats(uid):
    with conn() as c:
        total=c.execute("SELECT COUNT(*) n FROM referrals WHERE inviter_id=?",(uid,)).fetchone()['n']
        valid=c.execute("SELECT COUNT(*) n FROM referrals WHERE inviter_id=? AND valid=1",(uid,)).fetchone()['n']
        return total,valid

def referral_rank(uid):
    with conn() as c:
        rows=c.execute("SELECT inviter_id,COUNT(*) n FROM referrals WHERE valid=1 GROUP BY inviter_id ORDER BY n DESC, inviter_id ASC").fetchall()
        for i,r in enumerate(rows,1):
            if r['inviter_id']==uid: return i
        return None

def referral_leaderboard(limit=20):
    with conn() as c: return c.execute("SELECT r.inviter_id,COUNT(*) n,u.username,u.first_name FROM referrals r JOIN users u ON u.id=r.inviter_id WHERE r.valid=1 GROUP BY r.inviter_id ORDER BY n DESC,r.inviter_id ASC LIMIT ?",(limit,)).fetchall()

def create_campaign(title,prize,winners,captcha_required=False,rank_prizes=None):
    with conn() as c:
        c.execute("UPDATE campaigns SET active=0 WHERE active=1")
        c.execute("UPDATE referrals SET valid=0")
        c.execute("INSERT INTO campaigns(title,prize,winners_count,active,captcha_required,created_at) VALUES(?,?,?,0,?,?)",(title,prize,int(winners),1 if captcha_required else 0,now()))
        cid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for rank, value in enumerate(rank_prizes or [],1):
            c.execute("INSERT INTO campaign_rank_prizes(campaign_id,rank,prize) VALUES(?,?,?)",(cid,rank,str(value)))
        return cid

def campaign_rank_prizes(cid):
    with conn() as c:
        return c.execute("SELECT rank,prize FROM campaign_rank_prizes WHERE campaign_id=? ORDER BY rank",(cid,)).fetchall()

def active_campaign():
    with conn() as c: return c.execute("SELECT * FROM campaigns WHERE active=1 ORDER BY id DESC LIMIT 1").fetchone()

def campaign_by_id(cid):
    with conn() as c: return c.execute("SELECT * FROM campaigns WHERE id=?",(cid,)).fetchone()

def campaign_list(limit=20):
    with conn() as c: return c.execute("SELECT * FROM campaigns ORDER BY id DESC LIMIT ?",(limit,)).fetchall()

def set_campaign_active(cid,active):
    with conn() as c:
        if active: c.execute("UPDATE campaigns SET active=0 WHERE active=1")
        c.execute("UPDATE campaigns SET active=? WHERE id=?",(1 if active else 0,cid))
        return c.execute("SELECT * FROM campaigns WHERE id=?",(cid,)).fetchone()

def delete_campaign(cid):
    with conn() as c:
        c.execute("DELETE FROM campaign_winners WHERE campaign_id=?",(cid,))
        c.execute("DELETE FROM campaign_rank_prizes WHERE campaign_id=?",(cid,))
        c.execute("DELETE FROM campaigns WHERE id=?",(cid,))

def campaign_set_winners(cid, rows):
    with conn() as c:
        c.execute("DELETE FROM campaign_winners WHERE campaign_id=?",(cid,))
        for rank,uid,prize in rows:
            c.execute("INSERT INTO campaign_winners(campaign_id,user_id,rank,prize,created_at) VALUES(?,?,?,?,?)",(cid,uid,rank,prize,now()))
        c.execute("UPDATE campaigns SET active=0,ended_at=? WHERE id=?",(now(),cid))
        c.execute("UPDATE referrals SET valid=0")

def add_mandatory_channel(chat_id,title,join_url):
    with conn() as c:
        c.execute("INSERT INTO mandatory_channels(chat_id,title,join_url,created_at) VALUES(?,?,?,?)",(str(chat_id),title,join_url,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def mandatory_channels(active_only=True):
    with conn() as c:
        q="SELECT * FROM mandatory_channels" + (" WHERE active=1" if active_only else "") + " ORDER BY id"
        return c.execute(q).fetchall()

def remove_mandatory_channel(cid):
    with conn() as c: c.execute("UPDATE mandatory_channels SET active=0 WHERE id=?",(cid,))


def add_private_channel(uid,link):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO private_channels(user_id,channel_link,created_at) VALUES(?,?,?)",(uid,link,now()))

def available_channels(uid):
    with conn() as c:
        public=c.execute("SELECT id,invite_link,'public' AS scope FROM channel_submissions WHERE status='approved' ORDER BY id DESC").fetchall()
        private=c.execute("SELECT id,channel_link AS invite_link,'private' AS scope FROM private_channels WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
        return list(public)+list(private)


# --- Referral lookup and one-time bonus links ---
def referral_by_invitee(invitee_id):
    with conn() as c:
        return c.execute("SELECT * FROM referrals WHERE invitee_id=?", (invitee_id,)).fetchone()

def create_bonus(title, amount, capacity, start_at, end_at, token):
    with conn() as c:
        c.execute("INSERT INTO bonuses(title,amount,capacity,start_at,end_at,token,created_at) VALUES(?,?,?,?,?,?,?)",
                  (title,float(amount),int(capacity),start_at,end_at or '',token,now()))
        return c.execute("SELECT * FROM bonuses WHERE id=last_insert_rowid()").fetchone()

def bonus_by_id(bonus_id):
    with conn() as c:
        return c.execute("SELECT * FROM bonuses WHERE id=?", (bonus_id,)).fetchone()

def list_bonuses(limit=30):
    with conn() as c:
        return c.execute("SELECT * FROM bonuses ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

def set_bonus_active(bonus_id, active):
    with conn() as c:
        c.execute("UPDATE bonuses SET active=? WHERE id=?", (1 if active else 0, bonus_id))
        return c.execute("SELECT * FROM bonuses WHERE id=?", (bonus_id,)).fetchone()

def claim_bonus(bonus_id, token, user_id):
    """Atomically claim a bonus once per user and within its capacity/date window."""
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("BEGIN IMMEDIATE")
        b = c.execute("SELECT * FROM bonuses WHERE id=? AND token=?", (bonus_id,token)).fetchone()
        if not b:
            c.rollback(); return (False, "invalid", None)
        if c.execute("SELECT 1 FROM bonus_claims WHERE bonus_id=? AND user_id=?", (bonus_id,user_id)).fetchone():
            c.rollback(); return (False, "already", b)
        if b['claimed_count'] >= b['capacity']:
            c.execute("UPDATE bonuses SET active=0 WHERE id=?", (bonus_id,))
            c.commit(); return (False, "exhausted", b)
        if not b['active']:
            c.rollback(); return (False, "inactive", b)
        current = datetime.now(timezone.utc).isoformat(timespec='seconds')
        if current < b['start_at']:
            c.rollback(); return (False, "not_started", b)
        if b['end_at'] and current > b['end_at']:
            c.execute("UPDATE bonuses SET active=0 WHERE id=?", (bonus_id,))
            c.commit(); return (False, "expired", b)
        c.execute("INSERT INTO bonus_claims(bonus_id,user_id,amount,claimed_at) VALUES(?,?,?,?)",
                  (bonus_id,user_id,b['amount'],current))
        c.execute("UPDATE bonuses SET claimed_count=claimed_count+1, active=CASE WHEN claimed_count+1>=capacity THEN 0 ELSE active END WHERE id=?", (bonus_id,))
        c.execute("UPDATE users SET balance_ton=balance_ton+? WHERE id=?", (b['amount'],user_id))
        c.execute("INSERT INTO wallet_ledger(user_id,amount,currency,kind,status,description,created_at) VALUES(?,?,'TON','bonus','approved',?,?)",
                  (user_id,b['amount'],f"Bonus #{bonus_id}: {b['title']}",current))
        c.commit()
        return (True, "claimed", b)
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def game_cooldown_remaining(uid, cooldown_hours=None):
    """Return remaining cooldown seconds, or 0 when the user may play."""
    if cooldown_hours is None:
        cooldown_hours = float(setting("game_cooldown_hours", "6") or 6)
    cooldown_hours = max(0.0, float(cooldown_hours))
    if cooldown_hours <= 0:
        return 0
    with conn() as c:
        row = c.execute("SELECT created_at FROM game_plays WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    if not row:
        return 0
    with conn() as c:
        elapsed = c.execute("SELECT (julianday('now')-julianday(?))*86400 AS seconds", (row['created_at'],)).fetchone()['seconds']
    return max(0, int(cooldown_hours * 3600 - (elapsed or 0)))

def record_game_play(uid, dice_value, points):
    with conn() as c:
        c.execute("UPDATE users SET game_points=COALESCE(game_points,0)+? WHERE id=?", (int(points), uid))
        c.execute("INSERT INTO game_plays(user_id,dice_value,points,created_at) VALUES(?,?,?,?)",
                  (uid, int(dice_value), int(points), now()))
        return c.execute("SELECT game_points FROM users WHERE id=?", (uid,)).fetchone()["game_points"]

def game_stats():
    with conn() as c:
        return {
            "plays": c.execute("SELECT COUNT(*) n FROM game_plays").fetchone()["n"],
            "winners": c.execute("SELECT COUNT(*) n FROM game_plays WHERE points>0").fetchone()["n"],
            "points": c.execute("SELECT COALESCE(SUM(points),0) n FROM game_plays").fetchone()["n"]
        }

import os, sqlite3, json, shutil, tempfile
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.getenv("DB_PATH", "/data/adservice.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

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
          active INTEGER NOT NULL DEFAULT 1, balance REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL
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
          method_id INTEGER NOT NULL, txid TEXT NOT NULL, receipt_file_id TEXT,
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
        """)
        # Lightweight migrations for databases created by earlier releases.
        user_cols={r['name'] for r in c.execute("PRAGMA table_info(users)").fetchall()}
        if 'balance' not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN balance REAL NOT NULL DEFAULT 0")
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
    with conn() as c:
        c.execute("INSERT INTO payment_methods(currency,network,address,created_at) VALUES(?,?,?,?)",(currency,network,address,now()))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def methods():
    with conn() as c: return c.execute("SELECT * FROM payment_methods WHERE active=1 ORDER BY id").fetchall()

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

def order_payment(order_id,method_id,txid,receipt):
    with conn() as c:
        c.execute("INSERT INTO payments(order_id,method_id,txid,receipt_file_id,created_at) VALUES(?,?,?,?,?)",
                  (order_id,method_id,txid,receipt,now()))
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
          "revenue":c.execute("SELECT COALESCE(SUM(CAST(price AS REAL)),0) n FROM orders WHERE payment_status='paid'").fetchone()["n"]
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
        if approved and row['kind']=='deposit': c.execute("UPDATE users SET balance=balance+? WHERE id=?",(row['amount'],row['user_id']))
        if approved and row['kind']=='withdrawal': c.execute("UPDATE users SET balance=balance-? WHERE id=?",(row['amount'],row['user_id']))
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
          'deposits':c.execute("SELECT COALESCE(SUM(amount),0) n FROM wallet_ledger WHERE kind='deposit' AND status='approved' AND julianday(created_at)>=julianday('now','-1 hour')").fetchone()['n'],
          'withdrawals':c.execute("SELECT COALESCE(SUM(amount),0) n FROM wallet_ledger WHERE kind='withdrawal' AND status='approved' AND julianday(created_at)>=julianday('now','-1 hour')").fetchone()['n'],
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

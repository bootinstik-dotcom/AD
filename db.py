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
          active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
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
        """)
        c.execute("INSERT OR IGNORE INTO categories(title,slug,sort_order) VALUES('تبلیغات گروه','group_ads',1)")
        c.execute("INSERT OR IGNORE INTO categories(title,slug,sort_order) VALUES('تبلیغات چنل','channel_ads',2)")
        for cat in c.execute("SELECT id,slug FROM categories").fetchall():
            for title,kind,order in [("جوین اجباری","force_join",1),("بنر ۲۴ ساعته","banner_24h",2)]:
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

def set_order_status(order_no,status):
    with conn() as c:
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

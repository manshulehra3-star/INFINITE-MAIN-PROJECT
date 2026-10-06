"""InfiniteCore Bot — Database"""
import os
import sqlite3

class DB:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER UNIQUE, user_id INTEGER, guild_id INTEGER,
            subject TEXT, category TEXT, status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'normal', claimed_by INTEGER,
            created_at TEXT, closed_at TEXT, last_activity TEXT,
            ai_summary TEXT, transcript_url TEXT,
            rating INTEGER, escalated INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ticket_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER, author_id INTEGER, note TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS tickets_blacklist (
            user_id INTEGER PRIMARY KEY, reason TEXT, added_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ticket_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER, staff_id INTEGER, user_id INTEGER,
            rating INTEGER, feedback TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, amount REAL, currency TEXT, method TEXT,
            status TEXT DEFAULT 'pending', proof_url TEXT, txn TEXT,
            invoice_id TEXT, verified_by INTEGER, created_at TEXT, verified_at TEXT
        );
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, price REAL, ram INTEGER, cpu INTEGER,
            disk INTEGER, duration_days INTEGER
        );
        CREATE TABLE IF NOT EXISTS promos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE, discount_percent INTEGER, max_uses INTEGER,
            used INTEGER DEFAULT 0, expires_at TEXT, created_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, url TEXT, description TEXT
        );
        CREATE TABLE IF NOT EXISTS vps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, vps_id TEXT UNIQUE, os TEXT, ram INTEGER,
            cpu INTEGER, disk INTEGER, ip TEXT, status TEXT DEFAULT 'pending',
            ptero_id INTEGER, created_at TEXT, expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS mc_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, server_id TEXT UNIQUE, name TEXT, version TEXT,
            ram INTEGER, ip TEXT, port INTEGER, status TEXT DEFAULT 'active',
            ptero_id INTEGER, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS welcome_config (
            guild_id INTEGER PRIMARY KEY, channel_id INTEGER,
            message TEXT, enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER, user_id INTEGER, mod_id INTEGER,
            reason TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER, case_number INTEGER, action TEXT,
            user_id INTEGER, mod_id INTEGER, reason TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE, user_id INTEGER, content TEXT,
            status TEXT DEFAULT 'pending', created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE, channel_id INTEGER, host_id INTEGER,
            prize TEXT, winners INTEGER, ends_at TEXT, status TEXT DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS giveaway_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            giveaway_id INTEGER, user_id INTEGER, entered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS levels (
            user_id INTEGER, guild_id INTEGER, xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0, messages INTEGER DEFAULT 0,
            last_xp TEXT, PRIMARY KEY (user_id, guild_id)
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, channel_id INTEGER, message TEXT,
            remind_at TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, task TEXT, done INTEGER DEFAULT 0, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT, guild_id INTEGER, user_id INTEGER, data TEXT, created_at TEXT
        );
        """)
        self.conn.commit()

    def ex(self, q, p=()):
        c = self.conn.cursor(); c.execute(q, p); self.conn.commit(); return c

    def one(self, q, p=()):
        c = self.conn.cursor(); c.execute(q, p); return c.fetchone()

    def all(self, q, p=()):
        c = self.conn.cursor(); c.execute(q, p); return c.fetchall()

    def close(self):
        self.conn.close()

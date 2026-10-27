import os
import sqlite3
import datetime
import numpy as np


class DB:
    def __init__(self, folder):
        self.path = os.path.join(folder, "attendance.db")
        self.con = sqlite3.connect(self.path)
        self.con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, roll TEXT);
        CREATE TABLE IF NOT EXISTS templates(
            user_id INTEGER, feat BLOB);
        CREATE TABLE IF NOT EXISTS attendance(
            user_id INTEGER, day TEXT, time TEXT,
            UNIQUE(user_id, day));
        """)
        self.con.commit()

    def add_user(self, name, roll, feats):
        cur = self.con.execute("INSERT INTO users(name, roll) VALUES(?,?)",
                               (name, roll))
        uid = cur.lastrowid
        self.con.executemany(
            "INSERT INTO templates VALUES(?,?)",
            [(uid, np.asarray(f, np.float32).tobytes()) for f in feats])
        self.con.commit()
        return uid

    def load_templates(self):
        rows = self.con.execute("SELECT user_id, feat FROM templates").fetchall()
        if not rows:
            return np.empty((0, 0), np.float32), []
        owners = [r[0] for r in rows]
        mat = np.stack([np.frombuffer(r[1], np.float32) for r in rows])
        return mat, owners

    def user_name(self, uid):
        r = self.con.execute("SELECT name, roll FROM users WHERE id=?",
                             (uid,)).fetchone()
        return r if r else ("?", "")

    def count_users(self):
        return self.con.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def mark(self, uid):
        """Returns True if newly marked today, False if already present."""
        now = datetime.datetime.now()
        try:
            self.con.execute("INSERT INTO attendance VALUES(?,?,?)",
                             (uid, now.strftime("%Y-%m-%d"),
                              now.strftime("%H:%M:%S")))
            self.con.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def report(self, day=None):
        day = day or datetime.date.today().strftime("%Y-%m-%d")
        return self.con.execute("""
            SELECT u.name, u.roll, a.day, a.time FROM attendance a
            JOIN users u ON u.id = a.user_id
            WHERE a.day=? ORDER BY a.time""", (day,)).fetchall()

    def all_records(self):
        return self.con.execute("""
            SELECT u.name, u.roll, a.day, a.time FROM attendance a
            JOIN users u ON u.id = a.user_id
            ORDER BY a.day DESC, a.time""").fetchall()

    def delete_user(self, uid):
        for t, col in (("templates", "user_id"), ("attendance", "user_id"),
                       ("users", "id")):
            self.con.execute(f"DELETE FROM {t} WHERE {col}=?", (uid,))
        self.con.commit()

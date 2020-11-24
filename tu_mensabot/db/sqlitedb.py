import sqlite3
from time import time

class SqliteDB:
    def __init__(self, database):
        self._conn = sqlite3.connect(database, check_same_thread=False)
        self._cur = self._conn.cursor()
        self._cur.execute('''
            CREATE TABLE IF NOT EXISTS userstats 
                (id INT PRIMARY KEY, firstname VARCHAR(60), languagecode VARCHAR(10))
                ''')
        self._cur.execute('''
            CREATE TABLE IF NOT EXISTS newsletter 
                (id INT PRIMARY KEY, time VARCHAR(8))
                ''')
        self._cur.execute('''
            CREATE TABLE IF NOT EXISTS chatsettings
                (id INT PRIMARY KEY, location VARCHAR(20), preferences TEXT)
                ''')
        self._cur.execute('''
            CREATE TABLE IF NOT EXISTS execlog
                (id VARCHAR(8) PRIMARY KEY, recipients INT, lastexecution TIMESTAMP)
                ''')
        self._conn.commit()

    def log_update(self, chat, from_user, s=0):
        self._log_chat(from_user)

    def _log_chat(self, from_user):
        self._cur.execute('INSERT OR REPLACE INTO userstats VALUES (?, ?, ?)', (from_user.id, from_user.first_name, from_user.language_code))
        self._conn.commit()

    def get_all_users(self, time_string):
        self._cur.execute('''
            SELECT newsletter.id, location, preferences, languagecode
            FROM (newsletter LEFT JOIN chatsettings ON newsletter.id=chatsettings.id) LEFT JOIN userstats ON newsletter.id = userstats.id
            WHERE time=?
            ''', (time_string,))
        return self._cur.fetchall()

    def get_user_newsletter(self, id):
        self._cur.execute('''
            SELECT time FROM newsletter WHERE id=?
            ''', (id,))
        result = self._cur.fetchone()
        return result[0] if result else None

    def set_user(self, id, time_string):
        try:
            self._cur.execute('INSERT OR REPLACE INTO newsletter VALUES (?, ?)', (id, time_string))
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    def get_chat_location(self, id):
        self._cur.execute('''
            SELECT location FROM chatsettings WHERE id=?
            ''', (id,))
        result = self._cur.fetchone()
        return result[0] if result else None

    def set_chat_location(self, id, location):
        try:
            self._cur.execute('INSERT OR REPLACE INTO chatsettings (id, location) VALUES (?, ?)',
                    (id, location))
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    def get_preferences(self, id):
        self._cur.execute('''
            SELECT preferences FROM chatsettings WHERE id=?
            ''', (id,))
        result = self._cur.fetchone()
        return result[0].split(",") if result and result[0] else []

    def set_preferences(self, id, preferences):
        pref_string = ",".join(preferences)
        try:
            self._cur.execute('INSERT OR REPLACE INTO chatsettings (id, preferences) VALUES (?, ?)',
                    (id, pref_string))
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    def log_exec(self, ident, count):
        self._cur.execute("INSERT OR REPLACE INTO execlog VALUES (?, ?, ?)", (ident, count, time()))
        self._conn.commit()

    def __del__(self):
        self._cur.close()
        self._conn.close()

import sqlite3
from time import time

class FeedbackDB:
    def __init__(self, database):
        self._conn = sqlite3.connect(database, check_same_thread=False)
        self._cur = self._conn.cursor()
        self._cur.execute('''
            CREATE TABLE IF NOT EXISTS feedback
                (feedback_id INT PRIMARY KEY, user_id INT, msg_id INT, content VARCHAR(255), time TIMESTAMP)
                ''')
        self._conn.commit()

    def write_feedback(self, user_id, msg_id, content):
        try:
            self._cur.execute('INSERT INTO feedback (user_id, msg_id, content, time) VALUES (?, ?, ?)', (user_id, msg_id, content, time()))
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    def __del__(self):
        self._cur.close()
        self._conn.close()

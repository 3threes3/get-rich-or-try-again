import sqlite3, config
import smtplib, ssl

def make_admin(user_id):

    context = ssl.create_default_context()

    connection = sqlite3.connect(config.DB_FILE)

    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users 
        SET admin = 1
        WHERE id = ?
    """, (user_id,))

    connection.commit()
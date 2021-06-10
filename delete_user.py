import sqlite3, config
import smtplib, ssl

def delete_user(user_id):

    context = ssl.create_default_context()

    connection = sqlite3.connect(config.DB_FILE)

    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM users 
        WHERE id = ?
    """, (user_id,))

    cursor.execute("""
        DELETE FROM stock_strategy
        WHERE user_id = ?
    """, (user_id))

    connection.commit()


import sqlite3, config
import alpaca_trade_api as tradeapi
from datetime import datetime as dt

connection = sqlite3.connect(config.DB_FILE)

# Especificamos el tipo de objeto Row de sqlite3, en lugar de simples tuplas
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

# Cogemos una lista de los stocks que tenemos en la DB
cursor.execute("""
    SELECT id, symbol, name FROM stock
""")

rows = cursor.fetchall()

# Guardamos el id en la tabla de stocks para usarlo más adelante, además de generar nuestra lista de ISINs
symbols = []
stock_dict = {}
for row in rows: 
    symbol = row ['symbol']
    symbols.append(symbol)
    stock_dict[symbol] = row['id']

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.BASE_URL)


# Saving the date for which we already have data based on the last stock saved on the dictionary
stock_id = stock_dict[symbol] 
cursor.execute("""SELECT max(date) from stock_price where stock_id = (?)
 """, (stock_id,))

current_info_date = cursor.fetchone()[0]

chunk_size = 200
for i in range(0, len(symbols), chunk_size):
    symbol_chunk = symbols[i:i+chunk_size]

    barsets = api.get_barset(symbol_chunk, 'day')

    for symbol in barsets: 

        stock_id = stock_dict[symbol] 

        print(f"Processing symbol {symbol}")

        for bar in barsets[symbol]:

            if current_info_date is None or bar.t.date() > dt.strptime(current_info_date, "%Y-%m-%d").date():
                cursor.execute("""
                    INSERT INTO stock_price (stock_id, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (stock_id, bar.t.date(), bar.o, bar.h, bar.l, bar.c, bar.v))

connection.commit()


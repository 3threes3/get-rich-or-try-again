import sqlite3

from numpy import empty
import config
import alpaca_trade_api as tradeapi
import smtplib, ssl
from alpaca_trade_api.rest import TimeFrame
from datetime import date, datetime, timedelta, timezone

context = ssl.create_default_context()

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
    SELECt id FROM strategy WHERE name = 'opening_range_breakout'
""")

strategy_id = cursor.fetchone()['id']

cursor.execute("""
    SELECT symbol, name 
    FROM stock 
    JOIN stock_strategy on stock_strategy.stock_id = stock.id
    WHERE stock_strategy.strategy_id = ?
""", (strategy_id,))

stocks = cursor.fetchall()
symbols = [stock['symbol'] for stock in stocks]

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.BASE_URL)

# Actually yesterday to prevent timezone issues when demoing 
current_date = (date.today() - timedelta(days=1)).isoformat()
start_minute_bar = f"{current_date} 09:30:00-04:00"
end_minute_bar = f"{current_date} 09:45:00-04:00"

print(current_date)

orders = api.list_orders(status='all', limit=500, after=f'{current_date}T09:30:00-04:00')
existing_order_symbols = [order.symbol for order in orders]
print(existing_order_symbols)

messages = []

for symbol in symbols:
    minute_bars = api.get_bars(symbol, TimeFrame.Minute, (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()).df

    opening_range_mask = (minute_bars.index >= start_minute_bar) & (minute_bars.index < end_minute_bar)
    opening_range_bars = minute_bars.loc[opening_range_mask]

    if not opening_range_bars.empty:

        opening_range_low = opening_range_bars['low'].min()
        opening_range_high = opening_range_bars['high'].max()
        opening_range = opening_range_high - opening_range_low

        after_opening_range_mask = minute_bars.index >= end_minute_bar
        after_opening_range_bars = minute_bars.loc[after_opening_range_mask]
        print(f'############## {symbol} with a high of {opening_range_high} #############')
        print(after_opening_range_bars)

        after_opening_range_breakout = after_opening_range_bars[after_opening_range_bars['close'] > opening_range_high]

        if not after_opening_range_breakout.empty:
            if symbol not in existing_order_symbols:
                limit_price = after_opening_range_breakout.iloc[0]['close']

                messages.append(f"Placing order for {symbol} at {limit_price}, closed above {opening_range_high}\n\n{after_opening_range_breakout.iloc[0]['close']}\n\n")
                
                print(f"Placing order for {symbol} at {limit_price}, closed above {opening_range_high} at {after_opening_range_breakout.iloc[0]}")

                api.submit_order(
                    symbol=symbol,
                    side='buy',
                    type='limit', 
                    qty='100',
                    time_in_force='day',
                    order_class='bracket',
                    limit_price = limit_price,
                    take_profit=dict(
                        limit_price=limit_price + opening_range + 0.02,
                    ),
                    stop_loss=dict(
                        stop_price=limit_price - opening_range - 0.2,
                    )
                )
            else:
                print(f'Conditions met, but order for {symbol} already existing. Skipping...')
                messages.append(f'Conditions met, but order for {symbol} already existing.')

        else:
            print(f'Initial conditions met but no point through the day ideal to buy for {symbol}')
            messages.append(f'Initial conditions met but no point through the day ideal to buy for {symbol}')
            
    else:
        messages.append(f'Unable to retrieve sufficient data to place order for {symbol}')

print(messages)

with smtplib.SMTP_SSL("smtp.gmail.com", config.EMAIL_PORT, context=context) as server:
    server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
    email_message = f'Subject: Trade Notifications for {current_date}\n\n'
    email_message += "\n\n".join(messages)
    server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_ADDRESS, email_message)
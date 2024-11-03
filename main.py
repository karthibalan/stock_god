from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')


def fetch_stock_list():
    data = {
        'scan_clause':
        '( {cash} ( latest low > latest ema ( latest close , 20 ) and latest volume > 1 day ago sma ( volume,30 ) * 1 and latest count( 20, 1 where ( latest open - latest close ) = 0 ) < 1 and latest "close - 1 candle ago close / 1 candle ago close * 100" > 1 and ( {cash} ( ( {cash} ( 1 day ago "close - 1 candle ago close / 1 candle ago close * 100" < -1 and 1 day ago volume < latest volume * 0.3 ) ) or ( {cash} ( 2 days ago "close - 1 candle ago close / 1 candle ago close * 100" < -1 and 2 days ago volume < latest volume * 0.3 ) ) or ( {cash} ( 3 days ago "close - 1 candle ago close / 1 candle ago close * 100" < -1 and 3 days ago volume < latest volume * 0.3 ) ) ) ) and latest ema ( latest close , 50 ) < latest low and latest ema ( latest close , 200 ) < latest low and latest close < latest ema ( latest close , 20 ) * 1.10 and latest min ( 20 , latest ema ( latest close , 20 ) ) < latest ema ( latest close , 20 ) * 0.98 and weekly volume > weekly sma ( weekly volume , 20 ) * 1.5 ) )  '
    }

    with requests.Session() as s:
        r = s.get('https://chartink.com/screener/time-pass-48')
        soup = bs(r.content, 'lxml')  # Ensure lxml is installed
        s.headers['X-CSRF-TOKEN'] = soup.select_one(
            '[name=csrf-token]')['content']
        r = s.post('https://chartink.com/screener/process', data=data).json()

        # Extract stock names and details
        df = pd.DataFrame(r['data'])
        if not df.empty:
            stocks = df['nsecode'].tolist(
            )  # Adjust based on the actual column name
        else:
            stocks = []

    return stocks


async def send_update(context: ContextTypes.DEFAULT_TYPE, stock_list):
    message = "Bull Flag Stock list:\n\n" + "\n".join(stock_list)
    await context.bot.send_message(chat_id=CHAT_ID, text=message)


async def fetch_end_of_day_list():
    data = {
        'scan_clause':
        '( {cash} ( ( {cash} ( ( {cash} ( latest volume > 1 day ago sma ( volume,30 ) * 2 and latest close >= latest max ( 250 , latest high ) * 0.98 and latest close > latest open and latest "close - 1 candle ago close / 1 candle ago close * 100" > 3 and latest count( 100, 1 where latest "close - 1 candle ago close / 1 candle ago close * 100" = 0 ) < 1 ) ) and ( {33489} not ( latest close > 1 ) ) ) ) ) )   '
    }

    with requests.Session() as s:
        r = s.get('https://chartink.com/screener/time-pass-48')
        soup = bs(r.content, 'lxml')  # Ensure lxml is installed
        s.headers['X-CSRF-TOKEN'] = soup.select_one(
            '[name=csrf-token]')['content']
        r = s.post('https://chartink.com/screener/process', data=data).json()

        # Extract stock names and details
        df = pd.DataFrame(r['data'])
        if not df.empty:
            stocks = df['nsecode'].tolist(
            )  # Adjust based on the actual column name
        else:
            stocks = []

    return stocks


async def send_end_of_day_update(context: ContextTypes.DEFAULT_TYPE):
    end_of_day_list = await fetch_end_of_day_list()
    message = "Breakout Stock List:\n\n" + "\n".join(end_of_day_list)
    await context.bot.send_message(chat_id=CHAT_ID, text=message)


async def scheduled_end_of_day_update(context: ContextTypes.DEFAULT_TYPE):
    while True:
        now = datetime.now()
        # Wait until it's 4 PM
        target_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if now > target_time:
            # If it's already past 4 PM, schedule for the next day
            target_time += timedelta(days=1)

        # Calculate the time to wait until 4 PM
        wait_time = (target_time - now).total_seconds()
        await asyncio.sleep(wait_time)  # Wait until 4 PM

        # Send the end of day update
        await send_end_of_day_update(context)


async def monitor_stocks(context: ContextTypes.DEFAULT_TYPE):
    last_stock_list = []

    while True:
        current_stock_list = fetch_stock_list()

        if current_stock_list != last_stock_list:
            await send_update(context, current_stock_list)
            last_stock_list = current_stock_list

        await asyncio.sleep(3600)


async def breakout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching Breakout with Volume Stocks...")
    await send_end_of_day_update(context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Stock monitor started!")
    await asyncio.create_task(monitor_stocks(context))
    await asyncio.create_task(scheduled_end_of_day_update(context))


def main():
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register the command handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("breakout", breakout))

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main()

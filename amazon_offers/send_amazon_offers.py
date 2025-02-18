import requests
from bs4 import BeautifulSoup
from telegram import *
from telegram.ext import *
from telegram.constants import ParseMode

import asyncio
import time
#import pyshorteners

TELEGRAM_TOKEN = 'your-telegram-bot-token'
CHAT_ID = 'your-chat-id'
REF_CODE = "your-referral-code-here"

# Define a dictionary to keep track of sent items
sent_items = set()

"""
def shorten_amazon_link_with_referral(link, referral_code):
    # Add referral code to the link
    if "?" in link:
        link = link + "&tag=" + referral_code
    else:
        link = link + "?tag=" + referral_code

    # Shorten the link to an amzn.to URL
    shortener = pyshorteners.Shortener()
    return shortener.tinyurl.short(link)
"""

# Define the function to scrape Amazon website offers
async def scrape_amazon_offers(update: Update, context: CallbackContext) -> None:

    while True:
        url = 'https://www.amazon.it/deal/98a64104?pf_rd_r=3NZQ5JN1YFVSEKT6MWBW&pf_rd_t=Events&pf_rd_i=deals&pf_rd_p=08c3b6f5-c277-48d7-92b2-370f1198a648&pf_rd_s=slot-17&ref=dlx_deals_gd_dcl_img_2_98a64104_dt_sl17_48'
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        items = soup.find_all('div', {'class': 'a-section octopus-dlp-asin-section'})

        for item in items:
            link = 'https://www.amazon.it' + item.find('a', {'class': 'a-link-normal'})['href']
            img_link = item.find('img', {'class': 'octopus-dlp-asin-image'})['src']
            name = item.find('a', {'class': 'a-size-base a-color-base a-link-normal a-text-normal'}).text.strip()
            price = item.find('span', {'class': 'a-price-whole'}).text.strip() + item.find('span', {'class': 'a-price-fraction'}).text.strip()
            old_price = item.find('span', {'class':'a-text-strike'}).text.strip()
            percentage = item.find('div', {'class': 'oct-deal-badge-label'}).text.strip()
            #asin = item.find('td', {'class' : 'prodDetAttrValue'}).text.strip()
            #print("ASIN: ", asin)

            if link not in sent_items:
                message = f"<a href='{img_link}'>📌</a> <b>{name}</b>\n\n💰 {price}€ invece di {old_price}\n\n🔥{percentage}\n\n➡️ <a href='{link}'>{link}</a>"
                sent_items.add(link)
                await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.HTML)
                time.sleep(3)    
        time.sleep(10)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')


def main():

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", scrape_amazon_offers))
    app.run_polling()


if __name__ == "__main__":
    main()

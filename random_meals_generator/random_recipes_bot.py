import os
import random
import json
import requests
import time
import datetime
import logging
from tqdm import tqdm
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Configure the logging module
logging.basicConfig(filename="log_file.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BASE_URL = "https://www.giallozafferano.it/ricette-cat/page{}/{}"

RECIPES_PATH = "recipes.json"

ALLOW_DUPLICATES = False # Set this variable to True to allow duplicated recipes
SLEEP_TIME_MIN = 0.25
SLEEP_TIME_MAX = 1.5


CATEGORIES = [
    "Antipasti",
    "Primi",
    "Secondi-piatti",
    "Contorni",             
    "Piatti-Unici",
    "Dolci-e-Desserts",
    "Salse-e-Sughi",
    "Bevande",
    "Vegetariani",
]

CATEGORY_MAPPING = {
    "Antipasti": "Antipasti",
    "Primi": "Primi",
    "Secondi-piatti": "Secondi",
    "Contorni": "Contorni", 
    "Piatti-Unici": "Piatti Unici",
    "Dolci-e-Desserts": "Desserts",
    "Salse-e-Sughi": "Sughi",
    "Bevande": "Bevande",
    "Vegetariani": "Piatti Vegetariani"
}

pages_scraped = {}

def scrape_category(category):
    recipes = []
    session = requests.Session()
    page_number = 1
    total_pages = 1

    logging.info(f'{datetime.datetime.now()} | Scraping category {category}')
    
    while page_number <= total_pages:
        time.sleep(random.uniform(SLEEP_TIME_MIN, SLEEP_TIME_MAX))

        if page_number == 1:
            url = f"https://www.giallozafferano.it/ricette-cat/{category}"
        else:
            url = BASE_URL.format(page_number, category)

        response = session.get(url)
        if not response.ok:
            if not response.ok:
                logging.error(f'{datetime.datetime.now()} | Failed to fetch category {category}: {response.status_code}')
                return

        soup = BeautifulSoup(response.text, "html.parser")
        if total_pages == 1:
            if category == "Bevande" or category == "Salse-e-Sughi":
                last_page = soup.find_all('a', {'class': 'page'})[-1].text
                total_pages = int(last_page)
            else:
                span = soup.find('span', {'class': 'disabled total-pages'})
                total_pages = int(span.text.strip())

        for recipe in soup.find_all("article"):
            link_tag = recipe.find("h2").find("a")
            link = link_tag["href"]
            title = link_tag.text.strip()
            recipes.append({"name": title, "recipe_url": link})

        page_number += 1

    return category, recipes

def scrape_recipes(context: CallbackContext, chat_id, message_id):
    all_recipes = {}

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(scrape_category, category): category for category in CATEGORIES}
        for future in as_completed(futures):
            category = futures[future]
            try:
                category, recipes = future.result()
                all_recipes[category] = recipes

                # Update the message with loading bar
                progress = "[" + "#" * len(all_recipes) + "-" * (len(CATEGORIES) - len(all_recipes)) + "]"
                loading_str = f"Progress: {progress}"

                message = f"Refreshing the recipes in the <b>{category}</b> category...\n\n{loading_str}"
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message, parse_mode=ParseMode.HTML)

                # Append the number of recipes to the pages_scraped dictionary
                pages_scraped[category] = len(recipes)

            except Exception as e:
                print(f'{category} generated an exception: {e}')

    with open(RECIPES_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_recipes, f, indent=4, ensure_ascii=False)

def pin_start_message(context: CallbackContext, chat_id, message_id):
    context.bot.pin_chat_message(chat_id=chat_id, message_id=message_id, disable_notification=True)

def start(update: Update, context: CallbackContext):
    with open(RECIPES_PATH, 'r') as f:
        all_recipes = json.load(f)

    keyboard = []
    for i in range(0, len(CATEGORIES), 2):  # increment by 2 each loop
        row = []
        for j in range(i, i+2):  # get two categories
            if j < len(CATEGORIES):  # ensure we don't go out of range
                row.append(InlineKeyboardButton(CATEGORY_MAPPING[CATEGORIES[j]], callback_data=CATEGORIES[j]))
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    starting_message = ("<b>Welcome to the Random Recipes Bot!</b> 🍽\n\n"
                        "Discover and receive random recipes from various categories on <a href='https://www.giallozafferano.it/'>GialloZafferano</a> 🇮🇹.\n\n"
                        #"<i>Choose a category from below or type /refresh to update the recipes list</i> 🔄.\n\n"
                        "<b>Enjoy exploring and cooking delicious dishes!</b> 😋👨‍🍳")

    
    message = context.bot.send_message(chat_id=update.effective_chat.id, text=starting_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    pin_start_message(context, update.effective_chat.id, message.message_id)


def refresh_recipes(update: Update, context: CallbackContext):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    message = context.bot.send_message(chat_id=update.effective_chat.id, text="Starting to refresh the recipes...")
    scrape_recipes(context, update.message.chat_id, message.message_id)
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Append the number of recipes scraped for each category to the message
    message_text = "🔄 Recipes have been refreshed.\n\nNumber of recipes scraped for each category:\n"
    for category, count in pages_scraped.items():
        message_text += f"{category}: {count}\n"
    context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=message.message_id, text=message_text)


def get_random_recipe(recipes, sent_recipes):
    """
    Returns a random recipe that has not been sent yet.
    """
    while True:
        recipe = random.choice(recipes)
        if recipe["name"] not in sent_recipes or ALLOW_DUPLICATES:
            return recipe

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    category = query.data
    with open(RECIPES_PATH, 'r', encoding='utf-8') as f:
        all_recipes = json.load(f)
    recipes = all_recipes[category]
    sent_recipes = set()

    if len(sent_recipes) < len(recipes):
        recipe = get_random_recipe(recipes, sent_recipes)
        sent_recipes.add(recipe["name"])
        message_text = f"📌 <b>{recipe['name']}:</b>\n\n {recipe['recipe_url']}"
    else:
        message_text = f"No more recipes in this category. Restart the bot. 🤖"
    
    query.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=False)

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("refresh", refresh_recipes))
    dp.add_handler(CallbackQueryHandler(button_callback))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

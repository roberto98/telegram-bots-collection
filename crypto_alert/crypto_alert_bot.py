from coinbase.wallet.client import Client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram import ParseMode
from telegram.ext import CommandHandler, Defaults, Updater, Dispatcher, CallbackQueryHandler, CallbackContext, ConversationHandler

COINBASE_KEY = 'your-coinbase-key'
COINBASE_SECRET = 'your-coinbase-secret' 
TELEGRAM_TOKEN = 'your-telegram-bot-token'
coinbase_client = Client(COINBASE_KEY, COINBASE_SECRET)

# Stages
FIRST, SECOND = range(2)

def startCommand(update, context):
	"""Sends a message with three inline buttons attached."""
	keyboard = [
		[InlineKeyboardButton("Track", callback_data='1_track'), InlineKeyboardButton("Contact", callback_data='2_contact')], 
		[InlineKeyboardButton("Help", callback_data='3_help')]
	]

	reply_markup = InlineKeyboardMarkup(keyboard)
	
	#query.edit_message_text(text="Scegli", reply_markup=reply_markup)
	update.message.reply_text('Please choose:', reply_markup=reply_markup)
	return FIRST

	# context.bot.send_message(chat_id=update.effective_chat.id, text='Hello there!')

def startOver(update, context):
	query = update.callback_query
	query.answer()
	keyboard = [
		[InlineKeyboardButton("Track", callback_data='1_track'), InlineKeyboardButton("Contact", callback_data='2')], 
		[InlineKeyboardButton("Help", callback_data='3_help')]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	query.edit_message_text(text="Scegli", reply_markup=reply_markup)
	#update.message.reply_text('Please choose:', reply_markup=reply_markup)
	return FIRST

def helpCommand(update, context):
	query = update.callback_query
	query.answer()
	keyboard = [
		[InlineKeyboardButton("Indietro", callback_data='back')]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	query.edit_message_text(text="Ecco il mio aiuto altrimenti torna indietro", reply_markup=reply_markup)
	return FIRST

def contactCommand(update, context):
	query = update.callback_query
	query.answer()
	keyboard = [
		[InlineKeyboardButton("Indietro", callback_data='back')]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	query.edit_message_text(text="Contattami", reply_markup=reply_markup)
	return FIRST

def priceAlertCallback(context):
	crypto = context.job.context[0]
	sign = context.job.context[1]
	price = context.job.context[2]
	chat_id = context.job.context[3]
	
	send = False
	spot_price = coinbase_client.get_spot_price(currency_pair=crypto + '-EUR')['amount']
	
	if sign == '<':
		if float(price) >= float(spot_price):
			send = True
	else:
		if float(price) <= float(spot_price):
			send = True
	
	if send:
		response = f'👋 {crypto} has surpassed €{price} and has just reached <b>€{spot_price}</b>!'
	
		context.job.schedule_removal()
	
		context.bot.send_message(chat_id=chat_id, text=response)
		

def priceTrack(update, context):
	query = update.callback_query
	query.answer()
	keyboard = [
		[InlineKeyboardButton("Indietro", callback_data='back')]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	query.edit_message_text(text="Scrivi /alert BTC price", reply_markup=reply_markup)
	return FIRST

def priceAlert(update, context):
	keyboard = [
		[InlineKeyboardButton("Indietro", callback_data='back')]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)

	if len(context.args) > 2:
		crypto = context.args[0].upper()
		sign = context.args[1]
		price = context.args[2]
	
		context.job_queue.run_repeating(priceAlertCallback, interval=15, first=15, context=[crypto, sign, price, update.message.chat_id])
		
		response = f"⏳ I will send you a message when the price of {crypto} reaches €{price}, \n"
		response += f"the current price of {crypto} is €{coinbase_client.get_spot_price(currency_pair=crypto + '-EUR')['amount']}"
	else:
		response = '⚠️ Please provide a crypto code and a price value: \n<i>/price_alert {crypto code} {> / &lt;} {price}</i>'
	
	#query.edit_message_text(text=response, reply_markup=reply_markup)
	#context.bot.send_message(chat_id=update.effective_chat.id, text=response)
	update.message.reply_text(response, reply_markup=reply_markup)
	return FIRST
	
	


		
if __name__ == '__main__':
	updater = Updater(token=TELEGRAM_TOKEN, defaults=Defaults(parse_mode=ParseMode.HTML))

	dispatcher = updater.dispatcher

	# Setup conversation handler with the states FIRST and SECOND
	# Use the pattern parameter to pass CallbackQueries with specific
	# data pattern to the corresponding handlers.
	# ^ means "start of line/string"
	# $ means "end of line/string"
	# So ^ABC$ will only allow 'ABC'
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', startCommand)],
		states={
			FIRST: [
				CallbackQueryHandler(priceTrack, pattern='^' + '1_track' + '$'),
				CallbackQueryHandler(helpCommand, pattern='^' + '3_help' + '$'),
				CallbackQueryHandler(startOver, pattern='^' + 'back' + '$'),
			],
		},
		fallbacks=[CommandHandler('start', startCommand)],
	)

	# Add ConversationHandler to dispatcher that will be used for handling updates
	dispatcher.add_handler(conv_handler)

	#dispatcher.add_handler(CommandHandler('start' , startCommand))  #set command handler # Accessed via /start
	dispatcher.add_handler(CommandHandler('alert' , priceAlert))  #set command handler # Accessed via /alert

	updater.start_polling() # Start the bot

	# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
	updater.idle() # Wait for the script to be stopped, this will stop the bot as well
	
	

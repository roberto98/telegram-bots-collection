# pip install python-telegram-bot==13.15

import logging
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import os
import random 
import threading
import functools


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

prefix = ""
data_path = os.path.join(prefix, 'quizPatenteB2023.json')

bot_token = #TODO

def load_questions():
    with open(data_path, 'r') as file:
        data = json.load(file)
    questions = []
    for category, category_questions in data.items():
        for section, section_questions in category_questions.items():
            for question_dict in section_questions:
                questions.append({
                    'question': question_dict['q'],
                    'answer': question_dict['a'],
                    'image': question_dict.get('img', None)
                })
    return questions


class QuizData:
    def __init__(self, question, answer, image):
        self.question = question
        self.answer = answer
        self.image = image

# Global dictionary to store quiz data instances and their corresponding message IDs
quiz_data_dict = {}

def send_quiz(context: CallbackContext):
    questions = load_questions()
    question = random.choice(questions)
    quiz_data = QuizData(question['question'], question['answer'], question['image'])
  
    keyboard = [
        [InlineKeyboardButton("Vero", callback_data='true'),
         InlineKeyboardButton("Falso", callback_data='false')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = context.job.context # Get the chat ID from the job context

    if question['image']:
        message = context.bot.send_photo(chat_id=chat_id, photo=open(os.path.join(prefix, question['image']), 'rb'), caption=f"<b>{question['question']}</b>\n\n#car_question", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        message = context.bot.send_message(chat_id=chat_id, text=f"<b>{question['question']}</b>\n\n#car_question", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    quiz_data_dict[message.message_id] = quiz_data  # Store the quiz data instance with the message ID as the key


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    message_id = query.message.message_id  # Get the message ID of the original message
    quiz_data = quiz_data_dict.pop(message_id)  # Retrieve and remove the corresponding QuizData instance

    answer_text = "Vero" if query.data == "true" else "Falso"
    solution_text = "Vero" if quiz_data.answer else "Falso"

    if quiz_data.image:
        query.edit_message_caption(caption=f"<b>{quiz_data.question}</b>\n\nHai risposto: {answer_text}\n\nLa soluzione è: {solution_text}", parse_mode=ParseMode.HTML)
    else:
        query.edit_message_text(text=f"<b>{quiz_data.question}</b>\n\nHai risposto: {answer_text}\n\nLa soluzione è: {solution_text}", parse_mode=ParseMode.HTML)

def main() -> None:
    updater = Updater(token=bot_token, use_context=True)
    dispatcher = updater.dispatcher

    # Add command and callback handlers
    dispatcher.add_handler(CallbackQueryHandler(button))

    # Add a job queue to schedule the send_quiz function
    job_queue = updater.job_queue
    chat_id = #TODO

    # Schedule the send_quiz function with the chat_id
    job_queue.run_repeating(send_quiz, interval=3600, first=0, context=chat_id)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

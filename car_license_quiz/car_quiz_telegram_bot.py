# pip install python-telegram-bot==13.15
import logging
import json
import os
import random 
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
prefix = ""
data_path = os.path.join(prefix, 'quizPatenteB2023.json')
quiz_state_file = os.path.join(prefix, 'unanswered_quizzes.json')
bot_token = "#TODO"  # Replace with your actual bot token
chat_id = "#TODO"    # Replace with your actual chat ID

class QuizData:
    def __init__(self, question, answer, image, timestamp=None):
        self.question = question
        self.answer = answer
        self.image = image
        self.timestamp = timestamp or time.time()
    
    def to_dict(self):
        """Convert QuizData object to dictionary for JSON serialization"""
        return {
            'question': self.question,
            'answer': self.answer,
            'image': self.image,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create QuizData object from dictionary"""
        return cls(
            question=data['question'],
            answer=data['answer'],
            image=data['image'],
            timestamp=data.get('timestamp')
        )

# Global dictionary to store quiz data instances and their corresponding message IDs
quiz_data_dict = {}

def save_quiz_state():
    """Save the current quiz state to a file"""
    try:
        # Create a serializable representation of the quiz data
        serializable_quiz_data = {}
        for message_id, quiz_data in quiz_data_dict.items():
            serializable_quiz_data[str(message_id)] = quiz_data.to_dict()
        
        # Create a backup of the previous state file if it exists
        if os.path.exists(quiz_state_file):
            backup_file = f"{quiz_state_file}.bak"
            try:
                os.replace(quiz_state_file, backup_file)
            except Exception as e:
                logger.warning(f"Could not create backup file: {e}")
        
        # Write the new state
        with open(quiz_state_file, 'w') as file:
            json.dump(serializable_quiz_data, file)
        logger.info(f"Quiz state saved to {quiz_state_file}")
    except Exception as e:
        logger.error(f"Error saving quiz state: {e}")

def load_quiz_state():
    """Load the quiz state from a file"""
    global quiz_data_dict
    try:
        if os.path.exists(quiz_state_file):
            with open(quiz_state_file, 'r') as file:
                serialized_data = json.load(file)
            
            # Convert the loaded data back to QuizData objects
            temp_quiz_data = {}
            for message_id, quiz_data in serialized_data.items():
                temp_quiz_data[int(message_id)] = QuizData.from_dict(quiz_data)
            
            quiz_data_dict = temp_quiz_data
            logger.info(f"Quiz state loaded from {quiz_state_file} with {len(quiz_data_dict)} unanswered quizzes")
        else:
            logger.info("No quiz state file found, starting fresh")
            quiz_data_dict = {}
    except Exception as e:
        logger.error(f"Error loading quiz state: {e}")
        quiz_data_dict = {}  # Reset if there's an error

def load_questions():
    """Load questions from the JSON file"""
    try:
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
        logger.info(f"Loaded {len(questions)} questions")
        return questions
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return []

def send_quiz(context: CallbackContext):
    """Send a quiz question to the chat"""
    try:
        questions = load_questions()
        if not questions:
            logger.error("No questions available to send")
            return
        
        question = random.choice(questions)
        quiz_data = QuizData(question['question'], question['answer'], question['image'])
      
        keyboard = [
            [InlineKeyboardButton("Vero", callback_data='true'),
             InlineKeyboardButton("Falso", callback_data='false')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        target_chat_id = context.job.context  # Get the chat ID from the job context
        
        # Send the message based on whether there's an image
        if question['image']:
            try:
                image_path = os.path.join(prefix, question['image'])
                with open(image_path, 'rb') as photo:
                    message = context.bot.send_photo(
                        chat_id=target_chat_id, 
                        photo=photo, 
                        caption=f"<b>{question['question']}</b>\n\n#car_question", 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                # Fallback to text-only if image fails
                message = context.bot.send_message(
                    chat_id=target_chat_id, 
                    text=f"<b>{question['question']}</b>\n\n(Image not available)\n\n#car_question", 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.HTML
                )
        else:
            message = context.bot.send_message(
                chat_id=target_chat_id, 
                text=f"<b>{question['question']}</b>\n\n#car_question", 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.HTML
            )
        
        # Store the quiz data and save the state
        quiz_data_dict[message.message_id] = quiz_data
        save_quiz_state()
        logger.info(f"Quiz sent with ID: {message.message_id}")
    except Exception as e:
        logger.error(f"Error in send_quiz: {e}")

def button(update: Update, context: CallbackContext) -> None:
    """Handle button press from inline keyboard"""
    try:
        query = update.callback_query
        query.answer()
        
        message_id = query.message.message_id  # Get the message ID of the original message
        
        # Check if the quiz data exists for this message
        if message_id not in quiz_data_dict:
            logger.warning(f"Quiz data not found for message ID {message_id}")
            query.edit_message_text(text="Sorry, this quiz is no longer available.")
            return
        
        quiz_data = quiz_data_dict.pop(message_id)  # Retrieve and remove the corresponding QuizData instance
        answer_text = "Vero" if query.data == "true" else "Falso"
        solution_text = "Vero" if quiz_data.answer else "Falso"
        
        # Update the message with the answer
        try:
            if quiz_data.image:
                query.edit_message_caption(
                    caption=f"<b>{quiz_data.question}</b>\n\nHai risposto: {answer_text}\n\nLa soluzione è: {solution_text}", 
                    parse_mode=ParseMode.HTML
                )
            else:
                query.edit_message_text(
                    text=f"<b>{quiz_data.question}</b>\n\nHai risposto: {answer_text}\n\nLa soluzione è: {solution_text}", 
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            
        # Save the updated state (quiz removed)
        save_quiz_state()
        logger.info(f"Quiz answered: {message_id}")
    except Exception as e:
        logger.error(f"Error in button handler: {e}")

def restore_unanswered_quizzes(context: CallbackContext):
    """Restore any unanswered quizzes that were saved from previous sessions"""
    try:
        bot = context.bot
        count = 0
        
        # Clone the dict to avoid modifying during iteration
        for message_id, quiz_data in list(quiz_data_dict.items()):
            try:
                # Create new quiz with the same data
                keyboard = [
                    [InlineKeyboardButton("Vero", callback_data='true'),
                     InlineKeyboardButton("Falso", callback_data='false')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if quiz_data.image:
                    try:
                        image_path = os.path.join(prefix, quiz_data.image)
                        with open(image_path, 'rb') as photo:
                            message = bot.send_photo(
                                chat_id=chat_id, 
                                photo=photo, 
                                caption=f"<b>{quiz_data.question}</b>\n\n#car_question (Restored)", 
                                reply_markup=reply_markup, 
                                parse_mode=ParseMode.HTML
                            )
                    except Exception as e:
                        logger.error(f"Error sending restored photo: {e}")
                        message = bot.send_message(
                            chat_id=chat_id, 
                            text=f"<b>{quiz_data.question}</b>\n\n(Image not available)\n\n#car_question (Restored)", 
                            reply_markup=reply_markup, 
                            parse_mode=ParseMode.HTML
                        )
                else:
                    message = bot.send_message(
                        chat_id=chat_id, 
                        text=f"<b>{quiz_data.question}</b>\n\n#car_question (Restored)", 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.HTML
                    )
                
                # Delete the old quiz from the dictionary
                del quiz_data_dict[message_id]
                # Add the new quiz with new message ID
                quiz_data_dict[message.message_id] = quiz_data
                count += 1
            except Exception as e:
                logger.error(f"Error restoring quiz {message_id}: {e}")
        
        # Save the updated state
        if count > 0:
            save_quiz_state()
            logger.info(f"Restored {count} unanswered quizzes")
    except Exception as e:
        logger.error(f"Error in restore_unanswered_quizzes: {e}")

def error_handler(update, context):
    """Log the error and send a message to the developer"""
    logger.error(f"Update {update} caused error: {context.error}")
    try:
        # Send error message to developer (optional)
        context.bot.send_message(
            chat_id=chat_id,
            text=f"An error occurred: {context.error}"
        )
    except:
        pass

def main() -> None:
    """Start the bot"""
    try:
        # Load saved quiz state
        load_quiz_state()
        
        # Create the Updater and pass it your bot's token
        updater = Updater(token=bot_token, use_context=True)
        dispatcher = updater.dispatcher
        
        # Add command and callback handlers
        dispatcher.add_handler(CallbackQueryHandler(button))
        
        # Add error handler
        dispatcher.add_error_handler(error_handler)
        
        # Add a job queue to schedule the send_quiz function
        job_queue = updater.job_queue
        
        # Restore unanswered quizzes from previous sessions
        job_queue.run_once(restore_unanswered_quizzes, 5)  # Wait 5 seconds after startup to restore
        
        # Schedule the send_quiz function with the chat_id
        job_queue.run_repeating(send_quiz, interval=3600, first=10, context=chat_id)
        
        # Start the Bot
        updater.start_polling()
        logger.info("Bot started")
        
        # Run the bot until you press Ctrl-C
        updater.idle()
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")

if __name__ == "__main__":
    main()
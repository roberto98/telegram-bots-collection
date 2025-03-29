# pip install python-telegram-bot==13.15
import logging
import json
import os
import random 
import time
import datetime
import math
import re
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
    """Send a quiz question to the chat with retry logic"""
    try:
        # Check if we already have too many active quizzes
        max_active_quizzes = 300
        if len(quiz_data_dict) >= max_active_quizzes:
            logger.warning(f"Too many active quizzes ({len(quiz_data_dict)}), skipping new quiz")
            return
            
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
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
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
                                parse_mode=ParseMode.HTML,
                                timeout=15  # Increased timeout
                            )
                    except Exception as img_error:
                        logger.warning(f"Error sending photo (attempt {attempt}/{max_attempts}): {img_error}")
                        if attempt == max_attempts:
                            # Final attempt, try text-only as fallback
                            message = context.bot.send_message(
                                chat_id=target_chat_id, 
                                text=f"<b>{question['question']}</b>\n\n(Image not available)\n\n#car_question", 
                                reply_markup=reply_markup, 
                                parse_mode=ParseMode.HTML,
                                timeout=15  # Increased timeout
                            )
                        else:
                            # Try again with image
                            time.sleep(3)  # Wait before retry
                            continue
                else:
                    message = context.bot.send_message(
                        chat_id=target_chat_id, 
                        text=f"<b>{question['question']}</b>\n\n#car_question", 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.HTML,
                        timeout=15  # Increased timeout
                    )
                
                # If we got here, the message was sent successfully
                # Store the quiz data and save the state
                quiz_data_dict[message.message_id] = quiz_data
                save_quiz_state()
                logger.info(f"Quiz sent with ID: {message.message_id}")
                return  # Success, exit the function
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle rate limits specially
                if "flood" in error_str or "too many requests" in error_str:
                    retry_seconds = 30  # Default
                    match = re.search(r'retry in (\d+\.\d+|\d+)', error_str)
                    if match:
                        retry_seconds = float(match.group(1)) + 5  # Add buffer
                    
                    logger.warning(f"Rate limit hit, will retry after {retry_seconds}s")
                    if attempt < max_attempts:
                        # Schedule retry instead of immediate retry
                        context.job_queue.run_once(
                            send_quiz,
                            retry_seconds,
                            context=target_chat_id
                        )
                        return
                elif attempt < max_attempts:
                    # For other errors, try again after short delay
                    logger.warning(f"Error sending quiz (attempt {attempt}/{max_attempts}): {e}")
                    time.sleep(attempt * 2)  # Increasing delay between attempts
                else:
                    logger.error(f"Failed to send quiz after {max_attempts} attempts: {e}")
                    
    except Exception as e:
        logger.error(f"Unexpected error in send_quiz: {e}")
        
        # If we hit an unexpected error, try again later
        try:
            context.job_queue.run_once(
                send_quiz,
                random.randint(60, 120),  # Random delay between 1-2 minutes
                context=context.job.context
            )
        except:
            pass  # If this fails too, just give up

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

def schedule_quiz_restoration(context: CallbackContext):
    """Schedule restoration of quizzes with delay to avoid rate limits"""
    try:
        # Clone the dict to avoid modifying during iteration
        message_ids = list(quiz_data_dict.keys())
        
        if not message_ids:
            logger.info("No quizzes to restore")
            return
            
        logger.info(f"Scheduling restoration of {len(message_ids)} quizzes with delays")
        
        # Schedule quizzes with a delay between each one
        for i, message_id in enumerate(message_ids):
            # Add increasing delay for each quiz (5 seconds between each quiz)
            delay = 5 + (i * 5)  # Start with 5 seconds, then 10, 15, etc.
            context.job_queue.run_once(
                restore_single_quiz,
                delay,
                context={'message_id': message_id, 'attempt': 1}
            )
            
        logger.info(f"Restoration of {len(message_ids)} quizzes has been scheduled")
    except Exception as e:
        logger.error(f"Error scheduling quiz restoration: {e}")

def restore_single_quiz(context: CallbackContext):
    """Restore a single quiz with retry logic for rate limits"""
    try:
        job_context = context.job.context
        message_id = job_context['message_id']
        attempt = job_context['attempt']
        max_attempts = 5
        
        # Check if quiz still exists (might have been answered during delays)
        if message_id not in quiz_data_dict:
            logger.info(f"Quiz {message_id} no longer needs restoration (already answered)")
            return
            
        quiz_data = quiz_data_dict[message_id]
        bot = context.bot
        
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
                            parse_mode=ParseMode.HTML,
                            timeout=10  # Increased timeout
                        )
                except Exception as img_error:
                    logger.warning(f"Error sending restored photo: {img_error}")
                    message = bot.send_message(
                        chat_id=chat_id, 
                        text=f"<b>{quiz_data.question}</b>\n\n(Image not available)\n\n#car_question (Restored)", 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.HTML,
                        timeout=10  # Increased timeout
                    )
            else:
                message = bot.send_message(
                    chat_id=chat_id, 
                    text=f"<b>{quiz_data.question}</b>\n\n#car_question (Restored)", 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.HTML,
                    timeout=10  # Increased timeout
                )
            
            # Success! Update the quiz_data_dict
            # Delete the old quiz from the dictionary
            del quiz_data_dict[message_id]
            # Add the new quiz with new message ID
            quiz_data_dict[message.message_id] = quiz_data
            
            # Save state after each successful restoration
            save_quiz_state()
            logger.info(f"Successfully restored quiz {message_id} -> {message.message_id}")
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a rate limit error
            if "flood" in error_str or "too many requests" in error_str:
                # Extract retry time if available
                retry_seconds = 30  # Default retry time
                match = re.search(r'retry in (\d+\.\d+|\d+)', error_str)
                if match:
                    retry_seconds = float(match.group(1))
                    # Add a small buffer
                    retry_seconds = retry_seconds + 5
                
                if attempt < max_attempts:
                    logger.warning(f"Rate limit hit for quiz {message_id}, retry in {retry_seconds}s (attempt {attempt}/{max_attempts})")
                    # Schedule retry with exponential backoff
                    context.job_queue.run_once(
                        restore_single_quiz,
                        retry_seconds,
                        context={'message_id': message_id, 'attempt': attempt + 1}
                    )
                else:
                    logger.error(f"Failed to restore quiz {message_id} after {max_attempts} attempts")
            
            # Handle connection timeouts with a retry
            elif "timeout" in error_str or "timed out" in error_str:
                if attempt < max_attempts:
                    retry_seconds = 10 * attempt  # Increasing delay for timeouts
                    logger.warning(f"Connection timeout for quiz {message_id}, retry in {retry_seconds}s (attempt {attempt}/{max_attempts})")
                    context.job_queue.run_once(
                        restore_single_quiz,
                        retry_seconds,
                        context={'message_id': message_id, 'attempt': attempt + 1}
                    )
                else:
                    logger.error(f"Failed to restore quiz {message_id} after {max_attempts} attempts due to timeouts")
            else:
                logger.error(f"Error restoring quiz {message_id}: {e}")
                
    except Exception as e:
        logger.error(f"Unexpected error in restore_single_quiz: {e}")

def start_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued"""
    try:
        update.message.reply_text(
            "Benvenuto al quiz della Patente B! Riceverai quiz con cadenza oraria.\n"
            "Usa /quiz per ricevere un quiz ora.\n"
            "Usa /help per maggiori informazioni."
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued"""
    try:
        update.message.reply_text(
            "Comandi disponibili:\n"
            "/start - Inizia ad usare il bot\n"
            "/quiz - Richiedi un quiz immediatamente\n"
            "/help - Mostra questo messaggio di aiuto\n\n"
            "I quiz vengono inviati automaticamente ogni ora."
        )
    except Exception as e:
        logger.error(f"Error in help command: {e}")

def quiz_command(update: Update, context: CallbackContext) -> None:
    """Send a quiz immediately when the command /quiz is issued"""
    try:
        # Limit how often users can request manual quizzes (prevent spam)
        user_id = update.effective_user.id
        user_chat_id = update.effective_chat.id
        
        # Check if this is an authorized chat
        if str(user_chat_id) != str(chat_id):
            update.message.reply_text("Questo bot è configurato per funzionare solo in chat specifiche.")
            logger.warning(f"Unauthorized quiz request from chat {user_chat_id} (user {user_id})")
            return
            
        # For simplicity, we just pass the job context directly to send_quiz
        logger.info(f"Manual quiz requested by user {user_id}")
        context.job_queue.run_once(send_quiz, 1, context=user_chat_id)
        update.message.reply_text("Quiz in arrivo!")
    except Exception as e:
        logger.error(f"Error in quiz command: {e}")
        update.message.reply_text("Si è verificato un errore nell'invio del quiz.")

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

def schedule_hourly_quiz(context: CallbackContext):
    """Schedule quizzes at exact hours (00 minutes)"""
    try:
        # Log the scheduling
        next_time = context.job.next_t.strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Next quiz scheduled for {next_time}")
        
        # Send the quiz
        send_quiz(context)
    except Exception as e:
        logger.error(f"Error in schedule_hourly_quiz: {e}")

def main() -> None:
    """Start the bot"""
    try:
        # Load saved quiz state
        load_quiz_state()
        
        # Create the Updater and pass it your bot's token
        # For python-telegram-bot 13.15, we use the proper format for request_kwargs
        updater = Updater(token=bot_token, use_context=True, request_kwargs={
            'read_timeout': 30,
            'connect_timeout': 30
        })
        
        dispatcher = updater.dispatcher
        
        # Add command handlers
        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("quiz", quiz_command))
        
        # Add callback handler for button responses
        dispatcher.add_handler(CallbackQueryHandler(button))
        
        # Add error handler
        dispatcher.add_error_handler(error_handler)
        
        # Add a job queue to schedule the send_quiz function
        job_queue = updater.job_queue
        
        # Schedule quiz restoration with proper rate limiting
        job_queue.run_once(schedule_quiz_restoration, 5)  # Wait 5 seconds after startup to schedule restoration
        
        # Schedule quizzes at exact hours (19:00, 20:00, etc.)
        # Calculate minutes and seconds until the next hour
        now = datetime.datetime.now()
        minutes_to_next_hour = 60 - now.minute
        seconds_to_next_hour = minutes_to_next_hour * 60 - now.second
        
        # Schedule the first quiz to happen at the next hour
        first_quiz_delay = seconds_to_next_hour
        if first_quiz_delay < 180:  # If less than 3 minutes to next hour
            # Add an hour to give time for restorations to complete
            first_quiz_delay += 3600
            
        logger.info(f"First quiz will be sent in {math.ceil(first_quiz_delay/60)} minutes")
        job_queue.run_once(send_quiz, first_quiz_delay, context=chat_id)
        
        # Then schedule ongoing quizzes at the top of every hour
        for hour in range(24):  # Schedule for each hour of the day (0-23)
            job_queue.run_daily(
                schedule_hourly_quiz, 
                time=datetime.time(hour=hour, minute=0),
                days=(0, 1, 2, 3, 4, 5, 6),
                context=chat_id
            )
        
        # Start the Bot
        updater.start_polling(drop_pending_updates=True)  # Ignore updates that occurred while the bot was offline
        logger.info("Bot started")
        
        # Run the bot until you press Ctrl-C
        updater.idle()
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")

if __name__ == "__main__":
    main()
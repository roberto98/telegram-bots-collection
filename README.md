# 🤖 My Telegram Bot Collection

A repository containing various Telegram bots I've developed over the years. These bots serve different purposes, from educational quizzes to content generation for social media.

## 📋 Table of Contents

- [Car License Quiz Bot](#car-license-quiz-bot)
- [YC-Style Instagram Content Generator](#yc-style-instagram-content-generator)
- [Setup and Installation](#setup-and-installation)
- [Contributing](#contributing)
- [License](#license)

## 🚗 Car License Quiz Bot

### Overview

This bot helps users prepare for their driving license exam (Italian Patente B) by sending quiz questions at regular intervals. The bot uses a database of questions extracted from official exam materials and provides immediate feedback on user answers.

### Features

- Sends a random question every hour
- Questions may include images for traffic signs and road situations
- Simple True/False answer format via interactive buttons
- Immediate feedback after answering
- Contains a comprehensive database of updated 2023 questions

### Technical Implementation

The bot is built using:
- Python with python-telegram-bot library (v13.15)
- JSON database for storing questions, answers, and associated images
- Scheduled messaging using job queues
- Inline keyboard for interactive responses

## 📱 YC-Style Instagram Content Generator

### Overview

This bot automatically generates and posts startup/entrepreneurship content to Instagram in the style of Y Combinator advice. It creates both posts and stories with practical, actionable advice for founders, along with real-world examples.

### Features

- Generates content on 200+ startup-related topics
- Creates both carousel posts (with multiple slides) and stories
- Automatically posts to Instagram on a schedule (once per 24 hours)
- Content includes titles, descriptions, and practical examples
- Uses templates for consistent branding
- Mimics the direct, practical style of Y Combinator advice

### Technical Implementation

The bot leverages:
- OpenAI's GPT models to generate content in Paul Graham/YC style
- PIL (Python Imaging Library) for image generation with custom templates
- Instagram Graph API for automated posting
- Imgur API for temporary image hosting
- Structured error handling and logging
- Environment variables for secure credential management

## 🔧 Setup and Installation

### Prerequisites

- Python 3.7+
- Telegram Bot Token (obtained from [@BotFather](https://t.me/botfather))
- For YC-Style bot:
  - OpenAI API key
  - Instagram Business Account
  - Facebook Developer Account with Instagram Graph API access
  - Imgur Client ID

### Installation

1. Clone this repository
```bash
git clone https://github.com/your-username/telegram-bots-collection.git
cd telegram-bots-collection
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables in a `.env` file:
```
# For Car Quiz Bot
TELEGRAM_TOKEN=your_telegram_token
CHAT_ID=your_target_chat_id

# For YC-Style Instagram Bot
OPENAI_TOKEN=your_openai_api_key
IMGUR_CLIENT_ID=your_imgur_client_id
INSTA_USER_ID=your_instagram_user_id
INSTA_ACCESS_TOKEN=your_instagram_access_token
```

4. Run the desired bot:
```bash
# For Car Quiz Bot
python car_quiz_telegram_bot.py

# For YC-Style Instagram Bot
python instagram_content_generator.py
```

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/your-username/telegram-bots-collection/issues).

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

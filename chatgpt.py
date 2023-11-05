import openai
from pyngrok import ngrok
from quart import Quart, request
from telegram import Update, Bot

from config import OPENAI_API_KEY, TELEGRAM_GPT_BOT_TOKEN

# Initialize Quart app
app = Quart(__name__)
PORT = 5000
# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Initialize Telegram Bot
bot_token = TELEGRAM_GPT_BOT_TOKEN
whitelist = {5676905887, 6467542001, 5473331549}
MESSAGES = {
    'working': 'Working on your request. Please wait...',
    'error': 'Oops! Something went wrong. Please try again.',
    'not_whitelisted': 'You are not whitelisted. Please request access from Ahsan',
}


class TelegramBot:
    def __init__(self, token):
        self.chat_id = None
        self.bot = Bot(token=token)

    async def send_message(self, message):
        return await self.bot.sendMessage(chat_id=self.chat_id, text=message, parse_mode='markdown')

    async def get_file(self, file_id):
        return await self.bot.getFile(file_id)

    def set_chat_id(self, chat_id):
        self.chat_id = chat_id


@app.route('/webhook', methods=['POST'])
async def webhook():
    bot_instance = TelegramBot(bot_token)
    update_data = await request.json

    update = Update.de_json(update_data, bot_instance.bot)
    chat_id = update.message.chat_id
    bot_instance.set_chat_id(chat_id)

    if chat_id not in whitelist:
        await bot_instance.send_message(message=MESSAGES['not_whitelisted'] + "\n\n" + str(chat_id))
        return 'OK'
    await bot_instance.send_message(message=MESSAGES['working'])

    if update.message.text not in [None, '', '/start']:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user",
                 "content": f"Can you answer  the following with bullet points?\n{update.message.text}"}
            ]
        )

        await bot_instance.send_message(message=response.choices[0]['message']['content'])

    return 'OK'


if __name__ == '__main__':
    bot_instance = TelegramBot(bot_token)
    url = ngrok.connect(PORT).public_url
    hook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook?url={url}/webhook"
    print(' * Tunnel URL:', hook_url)
    app.run(port=PORT, debug=True)
    # asyncio.run(testme())

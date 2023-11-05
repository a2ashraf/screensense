import os

import openai
import pytesseract
from PIL import Image
from pyngrok import ngrok
from quart import Quart, request
from telegram import Update, Bot

from config import OPENAI_API_KEY, TELEGRAM_BOT_TOKEN

# Initialize Quart app
app = Quart(__name__)
PORT = 5000
# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Initialize Telegram Bot
bot_token = TELEGRAM_BOT_TOKEN

MESSAGES = {
    'file_received': 'File received. Processing...',
    'working': 'Working on your request. Please wait...',
    'extracted': 'Here is the text extracted: ',
    'summarized': 'Here is the summary:',
    'error': 'Oops! Something went wrong. Please try again.',
    'error_processing_image': 'Error processing image: ',
    # Add other messages as needed
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


class ImageProcessor:
    def __init__(self, bot: TelegramBot):
        self.bot = bot

    async def summarize(self, image: Image) -> str:
        await self.bot.send_message(message=MESSAGES['working'])

        try:
            # Try OCR on the original image
            text = pytesseract.image_to_string(image)
        except pytesseract.pytesseract.TesseractError as e:
            # Check if the error is related to image size
            if "Image too large" in str(e):
                # Resize the image. This example resizes it to half the original dimensions
                image = image.resize((image.width // 2, image.height // 2))
                try:
                    # Try OCR again on the resized image
                    text = pytesseract.image_to_string(image)
                except pytesseract.pytesseract.TesseractError as e2:
                    # If it fails again, return an error message
                    return f"Error processing image: {e2}"
            else:
                # If it's another error, return that error message
                return f"Error processing image: {e}"

        await self.bot.send_message(message=MESSAGES['extracted'])

        if len(text) > 4095:
            for x in range(0, len(text), 4095):
                await self.bot.send_message(message=text[x:x + 4095])
        else:
            await self.bot.send_message(message=text)

        # If no errors, proceed with summarization using OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user",
                 "content": f"Can you summarize the following into bulleted points?\n{text}"}
            ]
        )

        # Return summarized points
        return response['choices'][0]['message']['content'].strip()

    @staticmethod
    async def get_image_from_file_id(bot: TelegramBot, file_id):
        img_path = f"./saved_image_{file_id}.png"
        await (await bot.get_file(file_id)).download_to_drive(img_path)
        return Image.open(img_path)


@app.route('/webhook', methods=['POST'])
async def webhook():
    bot_instance = TelegramBot(bot_token)
    image_processor = ImageProcessor(bot_instance)
    update_data = await request.json

    if not is_valid_update(update_data):
        return "Invalid data", 400  # 400 Bad Request

    update = Update.de_json(update_data, bot_instance.bot)
    chat_id = update.message.chat_id
    bot_instance.set_chat_id(chat_id)

    await bot_instance.send_message(MESSAGES['file_received'])
    file_id = None
    # Check if the message contains a photo
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    # Check if the message contains a document
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await bot_instance.send_message(message="No photo or document found in the message.")

    if file_id:
        image = await get_image_from_file_id(file_id, bot_instance)
        file_name = f"./saved_image_{file_id}.png"

        try:
            image.verify()
            screenshot = Image.open(file_name)
            summary = await image_processor.summarize(screenshot)
            if MESSAGES['error_processing_image'] in summary:
                await bot_instance.send_message(message=summary + " \n\n_Error Found in image_ - *Please try again*")
                return 'OK'
            await bot_instance.send_message(message=MESSAGES['summarized'])
            await bot_instance.send_message(message=summary)
        except Exception as e:
            await bot_instance.send_message(message=MESSAGES['error'])
            await bot_instance.send_message(message=str(e))
        finally:
            os.remove(file_name)

    return 'OK'


async def testme():
    bot_instance = TelegramBot(bot_token)
    image_processor = ImageProcessor(bot_instance)
    file_name = f"./saved_image_{1}.png"
    screenshot = Image.open(file_name)
    try:
        screenshot.verify()
        image = Image.open(file_name)
        # image.save('saved_image_2.png')# Reload the image after verifying
        summary = await image_processor.summarize(image)
    except Exception as e:
        print(f"Invalid image: {e}")


async def get_image_from_file_id(file_id, bot: TelegramBot):
    img_path = f"./saved_image_{file_id}.png"
    await (await bot.get_file(file_id)).download_to_drive(img_path)
    return Image.open(img_path)


def is_valid_update(data):
    # Check if the data has a message and the message has text or photo or document
    return 'message' in data and (
            'text' in data['message'] or 'photo' in data['message'] or 'document' in data['message'])


if __name__ == '__main__':
    bot_instance = TelegramBot(bot_token)
    url = ngrok.connect(PORT).public_url
    hook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook?url={url}/webhook"
    print(' * Tunnel URL:', hook_url)
    app.run(port=PORT, debug=True)
    # asyncio.run(testme())

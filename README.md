# screensense
Share screen shot telegram bot and get OCR'd text and OpenAI summary.

Requirements: 
 You need to create a telegram bot via bot father. And provide the bot token inside config.py; You need to provide you openai key in that file as well.
 
After installing the dependencies and updating the config.py file with your tokens, you can run this project with 
python main.py, 

This will start the server and initialize ngrok (making your server public to the world)
You must establish a webhook into your both. This is simplified for you by just clicking the url generated for you in the logs
For example: https://api.telegram.org/bot903194:JqJ57AcBXfQtxgfZNiKRe/setWebhook?url=https://1570-142-198-49-245.ngrok-free.app/webhook

After that, your telegram bot will receive messages and post them to this service which will process and reply accordingly.

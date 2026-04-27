import asyncio
from telegram import Bot

async def get_chat_id():
    bot = Bot(token='8766987969:AAH791WMrN-6sEmv6G16vDzK0bzhq2G8Vkg')
    updates = await bot.get_updates(limit=5)
    for u in updates:
        if u.message:
            print(f"Chat ID: {u.message.chat.id} | Username: {u.message.from_user.username}")
    if not updates:
        print("No updates found. User needs to start a chat with the bot first.")

if __name__ == "__main__":
    asyncio.run(get_chat_id())
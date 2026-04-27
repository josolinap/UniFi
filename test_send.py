import asyncio
from telegram import Bot

async def test_send():
    bot = Bot(token='8766987969:AAH791WMrN-6sEmv6G16vDzK0bzhq2G8Vkg')
    try:
        await bot.send_message(chat_id=8016929549, text="Test from UniFi Monitor!")
        print("Message sent to 8016929549!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_send())
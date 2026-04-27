"""Quick test script to verify LLM and Telegram work."""

import asyncio
import os

# Set environment
os.environ['TELEGRAM_BOT_TOKEN'] = '8766987969:AAH791WMrN-6sEmv6G16vDzK0bzhq2G8Vkg'
os.environ['TELEGRAM_OWNER_CHAT_ID'] = '8016929549'
os.environ['NVIDIA_API_KEY'] = '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'
os.environ['UNIFI_API_KEY'] = 'zpIBiIiCvV9IiP-HHf-BY1sTKBolFWvu'

# Test LLM
from src.llm_client import NIMClient

print("Testing LLM...")
with NIMClient() as client:
    resp = client.chat("Say hi!")
    print(f"LLM Response: {resp.content[:100]}")

# Test Telegram message
print("\nTesting Telegram...")
from telegram import Bot

async def send_test():
    bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
    await bot.send_message(
        chat_id=os.environ['TELEGRAM_OWNER_CHAT_ID'],
        text="Test message from UniFi Monitor!"
    )
    print("Telegram message sent!")

asyncio.run(send_test())

print("\nAll tests passed!")
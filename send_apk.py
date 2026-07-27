import asyncio
from telegram import Bot
import config
import os


async def send_apk():
    bot = Bot(token=config.BOT_TOKEN)
    apk_path = os.path.join(os.path.dirname(__file__),
                           "apk", "app", "build", "outputs", "apk", "debug", "app-debug.apk")

    if os.path.exists(apk_path):
        with open(apk_path, "rb") as f:
            await bot.send_document(
                chat_id=config.ADMIN_ID,
                document=f,
                filename="MobKomRobot.apk",
                caption="📱 MobKom Robot APK\n\nУстанови на телефон"
            )
        print("APK sent!")
    else:
        print("APK not found")


if __name__ == "__main__":
    asyncio.run(send_apk())

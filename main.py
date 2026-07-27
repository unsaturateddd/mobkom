import asyncio
import threading
from bot import setup_bot
from database import init_db, cleanup_expired_tokens
from websocket_server import start_ws_server
from download_server import start_download_server


async def cleanup_loop():
    while True:
        cleanup_expired_tokens()
        await asyncio.sleep(300)


async def run_bot():
    app = setup_bot()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("  Telegram bot is running...")
    await asyncio.Event().wait()


async def main():
    init_db()
    print("=" * 50)
    print("  MobKom Robot v2.0")
    print("=" * 50)

    # Запуск сервера загрузки в отдельном потоке
    download_thread = threading.Thread(target=start_download_server, daemon=True)
    download_thread.start()
    print("  📥 Download server: http://0.0.0.0:8080")

    # Запуск всех сервисов
    await asyncio.gather(
        run_bot(),
        start_ws_server(),
        cleanup_loop()
    )


if __name__ == "__main__":
    asyncio.run(main())

# signal_handler.py — Обработка сигналов и авто-откуп

import asyncio
import random
import time
from datetime import datetime
import database as db
import config
from websocket_server import send_to_phone, connected_phones


async def handle_incoming_signal(phone_id, sender, body):
    """Обработка входящего SMS"""
    # Сохраняем сигнал
    db.add_signal(phone_id, f"{sender}: {body}")

    # Проверяем ответ от 8464
    if sender == config.REPLY_NUMBER:
        if config.CONFIRM_TEXT in body:
            # Сигнал подтверждён — ищем активные откупы
            await process_confirmed_signal(body)
        elif config.RURU_TEXT in body:
            # Оплата не прошла — логируем
            await process_ruru_error(body)


async def process_confirmed_signal(body):
    """Обработка подтверждённого сигнала"""
    # Находим всех трейдеров с активным получением сигналов
    users = db.get_all_users_with_signal()

    for user in users:
        # Отправляем сигнал в Telegram
        from telegram import Bot
        bot = Bot(token=config.BOT_TOKEN)
        try:
            await bot.send_message(
                chat_id=user["user_id"],
                text=f"📡 СИГНАЛ ПОЛУЧЕН!\n\n{body}\n\nВремя: {datetime.now().strftime('%H:%M:%S')}"
            )
        except:
            pass

        # Проверяем авто-откуп
        purchases = db.get_purchases(user["user_id"])
        for purchase in purchases:
            if purchase["enabled"]:
                await execute_auto_buy(user["user_id"], purchase)


async def process_ruru_error(body):
    """Обработка ошибки РУРУ"""
    print(f"  [SIGNAL] РУРУ: {body[:50]}")


async def execute_auto_buy(trader_id, purchase):
    """Выполнение авто-откупа"""
    # Находим свободный телефон
    phones = db.get_phones(trader_id=trader_id)
    online_phones = [p for p in phones if p["status"] == "online"]

    if not online_phones:
        db.log(trader_id, "auto_buy_failed", "No online phones")
        return

    phone = online_phones[0]
    phone_id = phone["phone_id"]

    # Отправляем SMS
    message = f"{purchase['card']} {purchase['amount']}"
    success = await send_to_phone(phone_id, "send_sms",
                                   number=config.SMS_NUMBER,
                                   message=message)

    if success:
        db.add_transaction(trader_id, phone_id, purchase["card"],
                          purchase["amount"], "pending")
        db.log(trader_id, "auto_buy_sent", f"Card: {purchase['card'][:8]}... Amount: {purchase['amount']}")

        # Запускаем таймер ожидания ответа
        asyncio.create_task(wait_for_response(trader_id, phone_id, purchase))


async def wait_for_response(trader_id, phone_id, purchase, timeout=30):
    """Ожидание ответа от 8464"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Проверяем последние SMS
        # В реальной реализации здесь будет проверка через WebSocket
        await asyncio.sleep(1)

    # Таймаут — обработка
    db.log(trader_id, "auto_buy_timeout", f"Card: {purchase['card'][:8]}...")


async def process_phone_response(phone_id, sender, body):
    """Обработка ответа от телефона"""
    if sender == config.REPLY_NUMBER:
        if config.CONFIRM_TEXT in body:
            # Успешная оплата — отправляем подтверждение
            import random
            digit = str(random.randint(1, 9))
            await send_to_phone(phone_id, "send_sms",
                               number=config.REPLY_NUMBER,
                               message=digit)
            db.log(None, "payment_confirmed", f"Sent digit: {digit}")

        elif config.RURU_TEXT in body:
            # Оплата не прошла — стоп
            db.log(None, "payment_failed", body[:50])

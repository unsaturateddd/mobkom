# signal_processor.py — Полный цикл обработки сигналов

import asyncio
import random
import time
from datetime import datetime
import database as db
import config
from logger import log_signal, log_purchase


async def process_signal(phone_id, sender, body):
    """
    Полный цикл обработки входящего SMS:
    1. Сохраняем сигнал
    2. Проверяем тип ответа
    3. Уведомляем трейдеров
    4. Запускаем авто-откуп если нужно
    """

    # Сохраняем сигнал в БД
    db.add_signal(phone_id, f"{sender}: {body}")
    log_signal("sms_received", f"From: {sender}, Body: {body[:50]}")

    # ── Ответ от 8464 ──

    if sender == config.REPLY_NUMBER:
        await handle_8464_response(phone_id, body)

    # ── Ответ от 7878 ──

    elif sender == config.SMS_NUMBER:
        await handle_7878_response(phone_id, body)


async def handle_8464_response(phone_id, body):
    """Обработка ответа от 8464 — мгновенная рассылка всем"""
    from telegram import Bot
    bot = Bot(token=config.BOT_TOKEN)

    # ── Перевод в Таджикистан (Успешно) ──

    if config.CONFIRM_TEXT in body:
        log_signal("signal_confirmed", body[:80])

        # Получаем ВСЕХ трейдеров с активным получением сигналов
        traders = db.get_all_users_with_signal()

        if not traders:
            log_signal("signal_no_receivers", "No traders with active signal reception")
            digit = str(random.randint(1, 9))
            return digit

        # Мгновенная рассылка ВСЕМ одновременно (asyncio.gather)
        tasks = []
        for trader in traders:
            tasks.append(send_signal_to_trader(bot, trader["user_id"], body))

        # Ждём отправки всем (параллельно, не последовательно)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Считаем успешные отправки
        sent_count = sum(1 for r in results if r is True)
        log_signal("signal_broadcast", f"Sent to {sent_count}/{len(traders)} traders")

        # Запускаем авто-откуп для трейдеров с активным авто-откупом
        await trigger_auto_buy_on_signal()

        # Отправляем подтверждение 1-9
        digit = str(random.randint(1, 9))
        return digit

    # ── РУРУ (Оплата не произведена) ──

    elif config.RURU_TEXT in body:
        log_signal("ruru_error", body[:80])

        # Мгновенная рассылка об ошибке всем
        traders = db.get_all_users_with_signal()
        tasks = []
        for trader in traders:
            tasks.append(send_ruru_to_trader(bot, trader["user_id"], body))
        await asyncio.gather(*tasks, return_exceptions=True)

        # Логируем ошибку
        db.log(None, "ruru_error", body[:100])


async def send_signal_to_trader(bot, trader_id, body):
    """Отправка сигнала одному трейдеру"""
    try:
        await bot.send_message(
            chat_id=trader_id,
            text=f"📡 **СИГНАЛ ПОЛУЧЕН!**\n\n"
                 f"Статус: ✅ Успешно\n"
                 f"Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
                 f"Детали:\n{body[:100]}",
            parse_mode="HTML"
        )
        log_signal("signal_sent", f"To {trader_id}")
        return True
    except Exception as e:
        log_signal("signal_send_error", f"To {trader_id}: {e}")
        return False


async def send_ruru_to_trader(bot, trader_id, body):
    """Отправка об ошибке одному трейдеру"""
    try:
        await bot.send_message(
            chat_id=trader_id,
            text=f"❌ **ОШИБКА ОПЛАТЫ**\n\n"
                 f"Статус: ❌ Оплата не прошла\n"
                 f"Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
                 f"Детали:\n{body[:100]}",
            parse_mode="HTML"
        )
        return True
    except Exception:
        return False


async def handle_7878_response(phone_id, body):
    """Обработка ответа от 7878"""
    print(f"  📨 [{datetime.now().strftime('%H:%M:%S')}] Ответ от 7878: {body[:50]}...")

    # Проверяем на ошибки
    if "неверная информация" in body.lower():
        print(f"  ⚠️ [{datetime.now().strftime('%H:%M:%S')}] Ошибка: неверная информация")
        db.log(None, "7878_error", body[:100])


async def trigger_auto_buy_on_signal():
    """Запуск авто-откупа при получении сигнала"""
    # Проверка глобального флага
    if not config.AUTO_BUY_ENABLED:
        log_signal("auto_buy_disabled", "Auto-buy is globally disabled")
        return

    # Находим всех трейдеров с активным авто-откупом
    traders = db.get_all_users_with_signal()

    for trader in traders:
        settings = db.get_trader_settings(trader["user_id"])
        if settings and settings.get("auto_buy_enabled"):
            # Находим активные откупы трейдера
            purchases = db.get_purchases(trader["user_id"])
            active_purchases = [p for p in purchases if p["enabled"]]

            for purchase in active_purchases:
                print(f"  🎯 [{datetime.now().strftime('%H:%M:%S')}] Авто-откуп для {trader['user_id']}: {purchase['card'][:8]}...")
                # Запускаем откуп (через WebSocket)
                await execute_purchase(trader["user_id"], purchase)


async def execute_purchase(trader_id, purchase):
    """Выполнение откупа"""
    from websocket_server import connected_phones, send_to_phone

    # Находим телефон трейдера
    phones = db.get_phones(trader_id=trader_id)
    online_phones = [p for p in phones if p["status"] == "online"]

    if not online_phones:
        print(f"  ❌ [{datetime.now().strftime('%H:%M:%S')}] Нет онлайн телефонов для трейдера {trader_id}")
        db.log(trader_id, "purchase_failed", "No online phones")
        return

    phone = online_phones[0]
    phone_id = phone["phone_id"]

    # Отправляем SMS на 7878
    message = f"{purchase['card']} {purchase['amount']}"
    success = await send_to_phone(phone_id, "send_sms",
                                   number=config.SMS_NUMBER,
                                   message=message)

    if success:
        db.add_transaction(trader_id, phone_id, purchase["card"],
                          purchase["amount"], "pending")
        db.log(trader_id, "purchase_sent", f"Card: {purchase['card'][:8]}... Amount: {purchase['amount']}")
        print(f"  📤 [{datetime.now().strftime('%H:%M:%S')}] SMS отправлено: {message}")

        # Запускаем таймер ожидания ответа
        asyncio.create_task(wait_for_purchase_response(trader_id, phone_id, purchase))
    else:
        db.log(trader_id, "purchase_failed", "Phone not responding")


async def wait_for_purchase_response(trader_id, phone_id, purchase, timeout=60):
    """Ожидание ответа на откуп"""
    from telegram import Bot
    bot = Bot(token=config.BOT_TOKEN)

    start_time = time.time()
    while time.time() - start_time < timeout:
        # Проверяем статус транзакции
        # В реальной реализации здесь будет проверка через WebSocket
        await asyncio.sleep(2)

    # Таймаут
    print(f"  ⏰ [{datetime.now().strftime('%H:%M:%S')}] Таймаут ответа на откуп")
    db.log(trader_id, "purchase_timeout", f"Card: {purchase['card'][:8]}...")

    # Уведомляем трейдера
    try:
        await bot.send_message(
            chat_id=trader_id,
            text=f"⏰ **ТАЙМАУТ ОТКУПА**\n\n"
                 f"Карта: {purchase['card'][:8]}...\n"
                 f"Сумма: {purchase['amount']}\n"
                 f"Не получен ответ в течение {timeout} сек",
            parse_mode="HTML"
        )
    except Exception:
        pass

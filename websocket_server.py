import asyncio
import json
import websockets
import time
from datetime import datetime
import database as db
import config
from logger import log_ws

# Хранилище подключённых телефонов
connected_phones = {}

# Rate limiting: {phone_id: [timestamps]}
rate_limits = {}
RATE_LIMIT = 10
RATE_WINDOW = 60

# Статистика сервера
server_stats = {
    "start_time": time.time(),
    "total_connections": 0,
    "total_messages": 0,
    "total_sms_sent": 0,
    "total_signals": 0
}


def check_rate_limit(phone_id):
    now = time.time()
    if phone_id not in rate_limits:
        rate_limits[phone_id] = []
    rate_limits[phone_id] = [t for t in rate_limits[phone_id] if now - t < RATE_WINDOW]
    if len(rate_limits[phone_id]) >= RATE_LIMIT:
        return False
    rate_limits[phone_id].append(now)
    return True


def get_uptime():
    seconds = int(time.time() - server_stats["start_time"])
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}ч {minutes}м"


async def handler(websocket):
    phone_id = None
    trader_id = None
    authenticated = False
    server_stats["total_connections"] += 1

    # Логируем подключение
    client = websocket.remote_address
    print(f"  🔌 [WS] New connection from {client}")

    try:
        # Таймаут на авторизацию (30 секунд)
        try:
            first_msg = await asyncio.wait_for(websocket.recv(), timeout=30)
            data = json.loads(first_msg)

            if data.get("action") == "register":
                token = data.get("token")
                imei = data.get("imei", "unknown")
                model = data.get("model", "unknown")

                token_data = db.validate_qr_token(token)
                if token_data:
                    trader_id = token_data["trader_id"]
                    phone_id = db.register_phone(imei, model)
                    db.assign_phone(phone_id, trader_id=trader_id)
                    connected_phones[phone_id] = websocket
                    authenticated = True

                    await websocket.send(json.dumps({
                        "action": "registered",
                        "phone_id": phone_id,
                        "trader_id": trader_id,
                        "status": "ok"
                    }))
                    db.log(trader_id, "phone_connected", f"{model} ({imei})")
                    log_ws("phone_connected", f"{model} ({imei}) -> trader {trader_id}", phone_id=phone_id)
                else:
                    log_ws("auth_failed", f"Invalid token: {token[:8]}...")
                    await websocket.send(json.dumps({
                        "action": "error",
                        "message": "Invalid or expired token"
                    }))
                    await websocket.close(1008, "Invalid token")
                    return
            else:
                await websocket.close(1008, "Not registered")
                return

        except asyncio.TimeoutError:
            print(f"  ⏰ [WS] Таймаут авторизации")
            await websocket.close(1008, "Timeout")
            return

        # Основной цикл
        async for message in websocket:
            if not authenticated:
                await websocket.close(1008, "Not authenticated")
                return

            server_stats["total_messages"] += 1

            if not check_rate_limit(phone_id):
                await websocket.send(json.dumps({
                    "action": "error",
                    "message": "Rate limit exceeded"
                }))
                continue

            data = json.loads(message)
            action = data.get("action")

            if action == "heartbeat":
                battery = data.get("battery", 0)
                db.update_phone_status(phone_id, "online", battery)
                await websocket.send(json.dumps({"action": "heartbeat_ok"}))

            elif action == "sms_sent":
                task_id = data.get("task_id")
                status = data.get("status")
                server_stats["total_sms_sent"] += 1
                db.log(trader_id, "sms_sent", f"Task: {task_id}, Status: {status}")
                log_ws("sms_sent", f"Task: {task_id}, Status: {status}", phone_id=phone_id)

            elif action == "sms_received":
                body = data.get("body", "")
                sender = data.get("from", "")
                server_stats["total_signals"] += 1
                db.add_signal(phone_id, f"{sender}: {body}")
                log_ws("sms_received", f"From: {sender}, Body: {body[:50]}", phone_id=phone_id)

                # Обработка через signal_processor
                from signal_processor import process_signal
                digit = await process_signal(phone_id, sender, body)

                # Если получен ответ от 8464 — отправляем подтверждение
                if digit:
                    await send_to_phone(phone_id, "send_sms",
                                       number=config.REPLY_NUMBER,
                                       message=digit)
                    print(f"  📤 [WS] Подтверждение: {digit}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"  🔴 [WS] Connection closed: {e}")
    except Exception as e:
        print(f"  ❌ [WS] Error: {type(e).__name__}: {e}")
    finally:
        if phone_id and phone_id in connected_phones:
            del connected_phones[phone_id]
            if phone_id in rate_limits:
                del rate_limits[phone_id]
            db.update_phone_status(phone_id, "offline")
            print(f"  🔴 [WS] Телефон отключён: {phone_id}")


async def send_to_phone(phone_id, action, **kwargs):
    ws = connected_phones.get(phone_id)
    if ws:
        try:
            await ws.send(json.dumps({"action": action, **kwargs}))
            return True
        except:
            pass
    return False


async def broadcast_sms(number, message):
    sent = 0
    for phone_id, ws in connected_phones.items():
        try:
            await ws.send(json.dumps({
                "action": "send_sms",
                "task_id": f"task_{int(time.time())}_{phone_id}",
                "number": number,
                "message": message
            }))
            sent += 1
        except:
            pass
    return sent


def get_health_status():
    """Проверка состояния сервера"""
    online = len(connected_phones)
    return {
        "status": "ok",
        "uptime": get_uptime(),
        "phones_online": online,
        "total_connections": server_stats["total_connections"],
        "total_messages": server_stats["total_messages"],
        "total_sms_sent": server_stats["total_sms_sent"],
        "total_signals": server_stats["total_signals"]
    }


async def start_ws_server():
    print(f"  🚀 [WS] WebSocket сервер запущен на {config.WS_HOST}:{config.WS_PORT}")
    
    # Обработка HEAD запросов от Render health check
    async def process_request(path, request_headers):
        # Если это не WebSocket запрос, отвечаем 200 OK
        if "Upgrade" not in request_headers or request_headers["Upgrade"].lower() != "websocket":
            return 200, {}, b"OK"
        # Продолжаем с WebSocket handshake
        return None
    
    try:
        async with websockets.serve(
            handler, 
            config.WS_HOST, 
            config.WS_PORT,
            process_request=process_request
        ):
            await asyncio.Future()
    except Exception as e:
        print(f"  ❌ [WS] Ошибка: {e}")
        # Fallback без process_request
        async with websockets.serve(handler, config.WS_HOST, config.WS_PORT):
            await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(start_ws_server())

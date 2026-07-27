import asyncio
import json
import websockets


async def test_full_flow():
    """Тест полного цикла: WebSocket подключение + SMS"""
    uri = "ws://localhost:8765"

    try:
        async with websockets.connect(uri) as ws:
            print("1. Подключение к серверу...")

            # Регистрация
            await ws.send(json.dumps({
                "action": "register",
                "token": "test_token_123",
                "imei": "123456789012345",
                "model": "Samsung A52"
            }))

            response = json.loads(await ws.recv())
            print(f"2. Ответ: {response}")

            # Heartbeat
            for i in range(3):
                await ws.send(json.dumps({
                    "action": "heartbeat",
                    "battery": 85
                }))
                await asyncio.sleep(1)

            print("3. Heartbeat отправлен")

            # Имитация получения SMS
            await ws.send(json.dumps({
                "action": "sms_received",
                "from": "8464",
                "body": "Перевод в Таджикистан: к оплате 14790 руб."
            }))

            print("4. SMS имитировано")
            print("Тест завершён успешно!")

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(test_full_flow())

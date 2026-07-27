import asyncio
import json
import websockets


async def test_client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Регистрация по QR токену
        await websocket.send(json.dumps({
            "action": "register",
            "token": "test_token",
            "imei": "123456789012345",
            "model": "Samsung A52"
        }))

        response = await websocket.recv()
        print(f"Response: {response}")

        # Heartbeat
        while True:
            await websocket.send(json.dumps({
                "action": "heartbeat",
                "battery": 85
            }))
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(test_client())

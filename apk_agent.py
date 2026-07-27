# MobKom APK — WebSocket клиент
# Этот код будет встроен в Android приложение

import asyncio
import json
import websockets
import subprocess
import re
import time
from datetime import datetime

# Настройки сервера
SERVER_URL = "ws://YOUR_SERVER_IP:8765"


class PhoneAgent:
    def __init__(self):
        self.phone_id = None
        self.trader_id = None
        self.ws = None
        self.running = False

    async def connect(self, token, imei, model):
        """Подключение к серверу по QR токену"""
        try:
            self.ws = await websockets.connect(SERVER_URL)
            await self.ws.send(json.dumps({
                "action": "register",
                "token": token,
                "imei": imei,
                "model": model
            }))
            response = json.loads(await self.ws.recv())
            if response.get("status") == "ok":
                self.phone_id = response["phone_id"]
                self.trader_id = response["trader_id"]
                print(f"Registered: {self.phone_id}")
                return True
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    async def heartbeat_loop(self):
        """Отправка heartbeat каждые 5 секунд"""
        while self.running:
            try:
                await self.ws.send(json.dumps({
                    "action": "heartbeat",
                    "battery": self.get_battery()
                }))
                await asyncio.sleep(5)
            except:
                break

    async def listen_for_commands(self):
        """Прослушивание команд от сервера"""
        while self.running:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                await self.handle_command(data)
            except:
                break

    async def handle_command(self, data):
        """Обработка команд от сервера"""
        action = data.get("action")

        if action == "send_sms":
            task_id = data.get("task_id")
            number = data.get("number")
            message = data.get("message")

            success = self.send_sms(number, message)

            await self.ws.send(json.dumps({
                "action": "sms_sent",
                "task_id": task_id,
                "status": "ok" if success else "failed"
            }))

    def send_sms(self, number, message):
        """Отправка SMS через Android API"""
        try:
            cmd = f'service call isms 5 i32 0 s16 "com.android.mms" s16 "{number}" s16 "null" s16 "{message}" s16 "null" s16 "null"'
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
            return result.returncode == 0
        except:
            return False

    def get_battery(self):
        """Получение уровня батареи"""
        try:
            result = subprocess.run(
                "cat /sys/class/power_supply/battery/capacity",
                shell=True, capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip())
        except:
            return 0

    async def run(self, token, imei, model):
        """Запуск агента"""
        if await self.connect(token, imei, model):
            self.running = True
            await asyncio.gather(
                self.heartbeat_loop(),
                self.listen_for_commands()
            )


# Точка входа для Android
if __name__ == "__main__":
    agent = PhoneAgent()
    # Токен будет получен из QR сканера
    TOKEN = "your_token_here"
    IMEI = "your_imei_here"
    MODEL = "your_model_here"
    asyncio.run(agent.run(TOKEN, IMEI, MODEL))

# Деплой MobKom Robot на VPS

## 1. Подготовка сервера

```bash
# Подключение
ssh root@YOUR_VPS_IP

# Обновление системы
apt update && apt upgrade -y

# Установка Python
apt install python3 python3-pip -y

# Установка зависимостей
pip3 install python-telegram-bot websockets qrcode[pil] fastapi uvicorn jinja2 aiosqlite
```

## 2. Загрузка файлов

```bash
# Создание папки
mkdir -p /opt/mobkomrobot
cd /opt/mobkomrobot

# Копирование файлов (с ПК)
scp -r C:\Users\unsat\Desktop\mobkomrobot\* root@YOUR_VPS_IP:/opt/mobkomrobot/
```

## 3. Настройка

```bash
# Редактирование конфига
nano config.py

# Замена IP в APK
# В WebSocketService.java заменить SERVER_URL на:
# ws://YOUR_VPS_IP:8765
```

## 4. Запуск

```bash
# Тестовый запуск
python3 main.py

# Фоновый запуск (screen)
screen -S mobkom
python3 main.py

# Отсоединение: Ctrl+A, D
# Подключение: screen -r mobkom
```

## 5. Автозапуск

```bash
# Создание сервиса
cat > /etc/systemd/system/mobkom.service << EOF
[Unit]
Description=MobKom Robot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/mobkomrobot
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Активация
systemctl enable mobkom
systemctl start mobkom
```

## 6. Открытие портов

```bash
# Firewall
ufw allow 8765/tcp  # WebSocket
ufw allow 8000/tcp  # Web панель
ufw allow 8080/tcp  # Download server
ufw enable
```

## 7. Тестирование

1. Открой web панель: http://YOUR_VPS_IP:8000
2. Войди с паролем: mobkom2024
3. Проверь бота в Telegram
4. Скачай APK по ссылке
5. Подключи телефон через QR

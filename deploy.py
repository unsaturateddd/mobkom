import paramiko
import os
import time


def deploy():
    VPS_HOST = "150.241.123.18"
    VPS_USER = "root"
    VPS_PASS = "t92VEC8Ds8o6"
    LOCAL_DIR = r"C:\Users\unsat\Desktop\mobkomrobot"

    print("Подключение к VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("Подключено!")

    # Обновление системы
    print("Обновление системы...")
    ssh.exec_command("apt update && apt upgrade -y")
    time.sleep(5)

    # Установка Python
    print("Установка Python...")
    ssh.exec_command("apt install python3 python3-pip -y")
    time.sleep(5)

    # Установка зависимостей
    print("Установка зависимостей...")
    ssh.exec_command("pip3 install python-telegram-bot websockets 'qrcode[pil]' fastapi uvicorn jinja2 aiosqlite")
    time.sleep(10)

    # Создание директории
    print("Создание директории...")
    ssh.exec_command("mkdir -p /opt/mobkomrobot/logs")

    # Загрузка файлов
    print("Загрузка файлов...")
    sftp = ssh.open_sftp()

    files = [
        "main.py", "config.py", "database.py", "bot.py",
        "websocket_server.py", "signal_processor.py", "web_panel.py",
        "logger.py", "download_server.py"
    ]

    for f in files:
        local_path = os.path.join(LOCAL_DIR, f)
        remote_path = f"/opt/mobkomrobot/{f}"
        if os.path.exists(local_path):
            sftp.put(local_path, remote_path)
            print(f"  Загружен: {f}")

    # Загрузка шаблонов
    ssh.exec_command("mkdir -p /opt/mobkomrobot/web/templates")
    time.sleep(1)

    templates_dir = os.path.join(LOCAL_DIR, "web", "templates")
    if os.path.exists(templates_dir):
        for f in os.listdir(templates_dir):
            if f.endswith(".html"):
                local_path = os.path.join(templates_dir, f)
                remote_path = f"/opt/mobkomrobot/web/templates/{f}"
                sftp.put(local_path, remote_path)
                print(f"  Загружен: {f}")

    sftp.close()

    # Настройка IP в конфиге
    print("Настройка IP...")
    ssh.exec_command(f"sed -i 's/0.0.0.0/{VPS_HOST}/g' /opt/mobkomrobot/config.py")

    # Создание сервиса
    print("Создание сервиса...")
    service_cmd = """cat > /etc/systemd/system/mobkom.service << 'EOF'
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
EOF"""
    ssh.exec_command(service_cmd)
    time.sleep(2)

    # Запуск сервиса
    print("Запуск сервиса...")
    ssh.exec_command("systemctl daemon-reload")
    ssh.exec_command("systemctl enable mobkom")
    ssh.exec_command("systemctl start mobkom")
    time.sleep(3)

    # Проверка статуса
    stdin, stdout, stderr = ssh.exec_command("systemctl status mobkom --no-pager")
    print(stdout.read().decode())

    # Открытие портов
    print("Настройка防火айвола...")
    ssh.exec_command("ufw allow 8765/tcp")
    ssh.exec_command("ufw allow 8000/tcp")
    ssh.exec_command("ufw allow 8080/tcp")
    ssh.exec_command("echo y | ufw enable")

    ssh.close()
    print("\n" + "=" * 50)
    print("Деплой завершён!")
    print(f"Web панель: http://{VPS_HOST}:8000")
    print(f"WebSocket: ws://{VPS_HOST}:8765")
    print(f"APK ссылка: http://{VPS_HOST}:8080/app-debug.apk")
    print("=" * 50)


if __name__ == "__main__":
    deploy()

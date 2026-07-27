import paramiko
import time

VPS_HOST = "150.241.123.18"
VPS_USER = "root"
VPS_PASS = "t92VEC8Ds8o6"

print("Подключение к VPS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for attempt in range(5):
    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=60)
        print("Подключено!")
        break
    except Exception as e:
        print(f"Попытка {attempt+1}: {e}")
        time.sleep(5)

# Загрузка исправленного download_server.py
sftp = ssh.open_sftp()
local_path = r"C:\Users\unsat\Desktop\mobkomrobot\download_server.py"
remote_path = "/opt/mobkomrobot/download_server.py"
sftp.put(local_path, remote_path)
sftp.close()
print("download_server.py загружен")

# Загрузка обновлённых файлов
files = ["main.py", "config.py", "database.py", "bot.py",
         "websocket_server.py", "signal_processor.py", "web_panel.py", "logger.py"]
for f in files:
    sftp = ssh.open_sftp()
    sftp.put(f"C:\\Users\\unsat\\Desktop\\mobkomrobot\\{f}", f"/opt/mobkomrobot/{f}")
    sftp.close()
    print(f"  {f} загружен")

# Перезапуск сервиса
ssh.exec_command("systemctl restart mobkom")
time.sleep(3)

# Проверка статуса
stdin, stdout, stderr = ssh.exec_command("systemctl status mobkom --no-pager | head -10")
print(stdout.read().decode())

ssh.close()
print("Готово!")

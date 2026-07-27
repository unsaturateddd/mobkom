# MobKom Robot v2.0 — Текущий статус

## ✅ Готово к деплою

### Функционал
- Telegram бот (роли, меню, профиль)
- WebSocket сервер (авторизация, rate limit)
- База данных (users, phones, purchases, logs)
- Получение сигналов (мгновенная рассылка)
- Раздача сигналов (APK + QR)
- Админ-панель (статистика, логи, роли)
- Веб-панель (dashboard, users, phones, signals, logs)
- Логирование в файлы

### Файлы
```
mobkomrobot/
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── database.py          # БД
├── bot.py               # Telegram бот
├── websocket_server.py  # WebSocket
├── signal_processor.py  # Обработка сигналов
├── web_panel.py         # Веб-панель
├── logger.py            # Логирование
├── apk/                 # Android проект
├── web/templates/       # HTML шаблоны
├── DEPLOY.md            # Инструкция деплоя
└── TASKS.md             # Задачи
```

## 🔲 Следующий шаг

1. **Купить VPS** (Hetzner CX32, €8/мес)
2. **Задеплоить** по инструкции DEPLOY.md
3. **Пересобрать APK** с URL сервера
4. **Протестировать** полный цикл

## ⏸ Заблокировано
- Авто-откуп (пока тестируем сигналы)

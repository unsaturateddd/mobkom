# MobKom Robot APK

## Сборка APK

### Через Android Studio:
1. Откройте папку `apk` в Android Studio
2. Дождитесь синхронизации Gradle
3. Build → Build Bundle(s) / APK(s) → Build APK(s)
4. APK появится в `app/build/outputs/apk/debug/`

### Через терминал:
```bash
cd apk
./gradlew assembleDebug
```

## Установка на телефон:
1. Скопируйте APK на телефон
2. Откройте файл → Установить
3. Разрешите установку из неизвестных источников

## Настройка сервера:
Отредактируйте `WebSocketService.java`:
```java
private static final String SERVER_URL = "ws://YOUR_SERVER_IP:8765";
```

## Разрешения:
- Камера (для сканирования QR)
- SMS (отправка/получение)
- Интернет (WebSocket подключение)

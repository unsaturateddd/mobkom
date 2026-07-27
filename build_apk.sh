#!/bin/bash
# build_apk.sh - Сборка APK

echo "=== MobKom Robot APK Builder ==="

# Проверка Android SDK
if [ -z "$ANDROID_HOME" ]; then
    echo "ANDROID_HOME не задан. Установите Android SDK."
    exit 1
fi

# Сборка
cd apk
./gradlew assembleDebug

# Копирование APK
if [ -f "app/build/outputs/apk/debug/app-debug.apk" ]; then
    cp app/build/outputs/apk/debug/app-debug.apk ../mobkom-robot.apk
    echo "APK собран: mobkom-robot.apk"
else
    echo "Ошибка сборки"
    exit 1
fi

# Android APK — Структура проекта

mobkomrobot/apk/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/mobkom/robot/
│   │   │   │   ├── MainActivity.java
│   │   │   │   ├── QRScannerActivity.java
│   │   │   │   ├── WebSocketService.java
│   │   │   │   ├── SMSService.java
│   │   │   │   └── models/
│   │   │   │       └── Phone.java
│   │   │   ├── res/
│   │   │   │   ├── layout/
│   │   │   │   │   ├── activity_main.xml
│   │   │   │   │   └── activity_qr_scanner.xml
│   │   │   │   └── values/
│   │   │   │       └── strings.xml
│   │   │   └── AndroidManifest.xml
│   │   └── androidTest/
│   └── build.gradle
├── build.gradle
├── settings.gradle
└── gradle.properties

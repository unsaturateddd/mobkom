package com.mobkom.robot;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {

    private static final int PERMISSION_REQUEST_CODE = 100;
    private TextView statusText;
    private Button scanButton;

    private WebSocketService wsService;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        statusText = findViewById(R.id.statusText);
        scanButton = findViewById(R.id.scanButton);

        checkPermissions();

        wsService = new WebSocketService();

        scanButton.setOnClickListener(v -> {
            Intent intent = new Intent(this, QRScannerActivity.class);
            startActivityForResult(intent, 101);
        });

        updateStatus("Нажмите для сканирования QR");
    }

    private void checkPermissions() {
        String[] permissions = {
            Manifest.permission.CAMERA,
            Manifest.permission.SEND_SMS,
            Manifest.permission.READ_SMS,
            Manifest.permission.RECEIVE_SMS,
            Manifest.permission.READ_PHONE_STATE
        };

        for (String permission : permissions) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, permissions, PERMISSION_REQUEST_CODE);
                return;
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 101 && resultCode == RESULT_OK && data != null) {
            String token = data.getStringExtra("token");
            connectToServer(token);
        }
    }

    private void connectToServer(String token) {
        String imei = android.os.Build.SERIAL;
        String model = android.os.Build.MODEL;

        Log.d("MobKom", "Token: " + token);
        Log.d("MobKom", "IMEI: " + imei);
        Log.d("MobKom", "Model: " + model);

        updateStatus("Подключение к серверу...");

        wsService.connect(token, imei, model, new WebSocketService.Callback() {
            @Override
            public void onConnected(String phoneId, String traderId) {
                Log.d("MobKom", "Connected! Phone: " + phoneId + ", Trader: " + traderId);
                runOnUiThread(() -> updateStatus("✅ Устройство успешно добавлено!\nID: " + traderId));
            }

            @Override
            public void onDisconnected() {
                runOnUiThread(() -> updateStatus("❌ Отключено от сервера"));
            }

            @Override
            public void onSmsRequest(String taskId, String number, String message) {
                // SMS обрабатывается в фоне
            }
        });
    }

    private void updateStatus(String status) {
        statusText.setText(status);
    }
}

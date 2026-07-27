package com.mobkom.robot;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.google.zxing.integration.android.IntentIntegrator;
import com.google.zxing.integration.android.IntentResult;

public class QRScannerActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Запуск сканера QR кодов
        IntentIntegrator integrator = new IntentIntegrator(this);
        integrator.setDesiredBarcodeFormats(IntentIntegrator.QR_CODE);
        integrator.setPrompt("Сканируйте QR код из Telegram бота");
        integrator.setCameraId(0);
        integrator.setBeepEnabled(false);
        integrator.initiateScan();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        IntentResult result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data);
        if (result != null) {
            if (result.getContents() == null) {
                Toast.makeText(this, "Сканирование отменено", Toast.LENGTH_SHORT).show();
                setResult(RESULT_CANCELED);
            } else {
                String token = result.getContents();
                Toast.makeText(this, "QR код считан: " + token, Toast.LENGTH_SHORT).show();

                Intent intent = new Intent();
                intent.putExtra("token", token);
                setResult(RESULT_OK, intent);
            }
        }
        finish();
    }
}

package com.mobkom.robot;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.telephony.SmsManager;
import android.telephony.SmsMessage;
import android.util.Log;

public class SMSService {

    private static final String TAG = "SMSService";
    private Context context;
    private SMSReceiver smsReceiver;
    private SMSListener listener;

    public interface SMSListener {
        void onSmsReceived(String from, String body);
    }

    public SMSService(Context context) {
        this.context = context;
        this.smsReceiver = new SMSReceiver();
    }

    public void setListener(SMSListener listener) {
        this.listener = listener;
    }

    public void startListening() {
        IntentFilter filter = new IntentFilter("android.provider.Telephony.SMS_RECEIVED");
        context.registerReceiver(smsReceiver, filter);
        Log.d(TAG, "SMS listener started");
    }

    public void stopListening() {
        if (smsReceiver != null) {
            context.unregisterReceiver(smsReceiver);
        }
    }

    public void sendSms(String number, String message, SMSCallback callback) {
        try {
            SmsManager smsManager = SmsManager.getDefault();
            smsManager.sendTextMessage(number, null, message, null, null);
            Log.d(TAG, "SMS sent to " + number + ": " + message);
            if (callback != null) {
                callback.onResult(true);
            }
        } catch (Exception e) {
            Log.e(TAG, "SMS send failed", e);
            if (callback != null) {
                callback.onResult(false);
            }
        }
    }

    public interface SMSCallback {
        void onResult(boolean success);
    }

    private class SMSReceiver extends BroadcastReceiver {
        @Override
        public void onReceive(Context context, Intent intent) {
            Bundle bundle = intent.getExtras();
            if (bundle != null) {
                Object[] pdus = (Object[]) bundle.get("pdus");
                if (pdus != null) {
                    for (Object pdu : pdus) {
                        SmsMessage smsMessage = SmsMessage.createFromPdu((byte[]) pdu);
                        String from = smsMessage.getDisplayOriginatingAddress();
                        String body = smsMessage.getDisplayMessageBody();

                        Log.d(TAG, "SMS from " + from + ": " + body);

                        if (listener != null) {
                            listener.onSmsReceived(from, body);
                        }
                    }
                }
            }
        }
    }
}

package com.mobkom.robot;

import android.util.Log;
import org.json.JSONObject;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.concurrent.TimeUnit;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;

public class WebSocketService {

    private static final String TAG = "WebSocketService";
    private static String SERVER_URL = "ws://31.76.50.43:8765";

    private WebSocket webSocket;
    private Callback callback;
    private boolean connected = false;

    // Установка URL сервера
    public static void setServerUrl(String url) {
        SERVER_URL = url;
    }

    public interface Callback {
        void onConnected(String phoneId, String traderId);
        void onDisconnected();
        void onSmsRequest(String taskId, String number, String message);
    }

    public void connect(String token, String imei, String model, Callback callback) {
        this.callback = callback;

        OkHttpClient client = new OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .writeTimeout(0, TimeUnit.MILLISECONDS)
            .connectTimeout(15, TimeUnit.SECONDS)
            .build();

        String url = SERVER_URL;
        Log.d(TAG, "Connecting to: " + url);

        Request request = new Request.Builder()
            .url(url)
            .build();

        webSocket = client.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                Log.d(TAG, "Connected to server");
                // Отправка регистрации
                try {
                    JSONObject msg = new JSONObject();
                    msg.put("action", "register");
                    msg.put("token", token);
                    msg.put("imei", imei);
                    msg.put("model", model);
                    webSocket.send(msg.toString());
                } catch (Exception e) {
                    Log.e(TAG, "Register error", e);
                }
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                try {
                    JSONObject data = new JSONObject(text);
                    String action = data.getString("action");

                    if (action.equals("registered")) {
                        connected = true;
                        String phoneId = data.getString("phone_id");
                        String traderId = data.getString("trader_id");
                        callback.onConnected(phoneId, traderId);
                        startHeartbeat();
                    } else if (action.equals("send_sms")) {
                        String taskId = data.getString("task_id");
                        String number = data.getString("number");
                        String message = data.getString("message");
                        callback.onSmsRequest(taskId, number, message);
                    } else if (action.equals("heartbeat_ok")) {
                        Log.d(TAG, "Heartbeat OK");
                    }
                } catch (Exception e) {
                    Log.e(TAG, "Message parse error", e);
                }
            }

            @Override
            public void onClosed(WebSocket webSocket, int code, String reason) {
                connected = false;
                callback.onDisconnected();
                Log.d(TAG, "Disconnected: " + reason);
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                connected = false;
                callback.onDisconnected();
                Log.e(TAG, "Connection failed: " + t.getMessage());
                if (response != null) {
                    Log.e(TAG, "Response code: " + response.code());
                }
                // Реконнект через 5 секунд
                reconnect(token, imei, model);
            }
        });
    }

    private void reconnect(String token, String imei, String model) {
        new Thread(() -> {
            try {
                Thread.sleep(5000);
                connect(token, imei, model, callback);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }).start();
    }

    public void reportSmsSent(String taskId, boolean success) {
        if (webSocket != null) {
            try {
                JSONObject msg = new JSONObject();
                msg.put("action", "sms_sent");
                msg.put("task_id", taskId);
                msg.put("status", success ? "ok" : "failed");
                webSocket.send(msg.toString());
            } catch (Exception e) {
                Log.e(TAG, "Report error", e);
            }
        }
    }

    public void reportSmsReceived(String from, String body) {
        if (webSocket != null) {
            try {
                JSONObject msg = new JSONObject();
                msg.put("action", "sms_received");
                msg.put("from", from);
                msg.put("body", body);
                webSocket.send(msg.toString());
            } catch (Exception e) {
                Log.e(TAG, "Report error", e);
            }
        }
    }

    private void startHeartbeat() {
        new Thread(() -> {
            while (connected) {
                try {
                    JSONObject msg = new JSONObject();
                    msg.put("action", "heartbeat");
                    msg.put("battery", getBatteryLevel());
                    webSocket.send(msg.toString());
                    Thread.sleep(5000);
                } catch (Exception e) {
                    break;
                }
            }
        }).start();
    }

    private int getBatteryLevel() {
        // Получение уровня батареи
        return 100;
    }

    public void disconnect() {
        connected = false;
        if (webSocket != null) {
            webSocket.close(1000, "Client disconnect");
        }
    }
}

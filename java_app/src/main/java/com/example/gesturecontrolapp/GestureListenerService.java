package com.example.gesturecontrolapp;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.pm.ServiceInfo;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.AssetFileDescriptor;
import android.media.AudioManager;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import android.view.KeyEvent;

import androidx.annotation.Nullable;
import androidx.core.app.ActivityCompat;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

import com.hivemq.client.mqtt.MqttClient;
import com.hivemq.client.mqtt.mqtt5.Mqtt5AsyncClient;
import com.hivemq.client.mqtt.datatypes.MqttQos;
import com.hivemq.client.mqtt.MqttGlobalPublishFilter;

import org.tensorflow.lite.Interpreter;

import java.io.FileInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

public class GestureListenerService extends Service {

    private static final String MQTT_BROKER = "broker.hivemq.com";
    private static final int MQTT_PORT = 1883;
    private static final String MQTT_TOPIC_SUBSCRIBE = "sharvin_gestures/data_for_phone";
    private static final String TFLITE_MODEL_PATH = "gesture_model.tflite";
    private static final String NOTIFICATION_CHANNEL_ID = "GestureControlChannel";
    private static final int FOREGROUND_NOTIFICATION_ID = 1; // For the persistent notification
    private static final int ACTION_NOTIFICATION_ID = 2;     // For the "gesture detected" notification
    private static final int NUM_FEATURES = 63;
    private static final String[] GESTURE_LABELS = {
            "NO_HAND", "SCROLL_UP", "SCROLL_DOWN", "SWIPE_LEFT",
            "SWIPE_RIGHT", "PLAY_PAUSE", "BACK_NAV"
    };

    private Mqtt5AsyncClient mqttClient;
    private Interpreter tfliteInterpreter;

    private String currentStableGesture = "NO_HAND";
    private String pendingGesture = "NO_HAND";
    private int pendingGestureCount = 0;
    private static final int GESTURE_STABILITY_THRESHOLD = 3;

    private float tflite_input_scale = 0.0f;
    private int tflite_input_zero_point = 0;
    private float tflite_output_scale = 0.0f;
    private int tflite_output_zero_point = 0;

    private ByteBuffer inputBuffer = null;
    private ByteBuffer outputBuffer = null;

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null; // We don't need binding
    }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.i("GestureListenerService", "Service Creating...");

        try {
            tfliteInterpreter = loadTFLiteModel();

            tflite_input_scale = tfliteInterpreter.getInputTensor(0).quantizationParams().getScale();
            tflite_input_zero_point = tfliteInterpreter.getInputTensor(0).quantizationParams().getZeroPoint();
            tflite_output_scale = tfliteInterpreter.getOutputTensor(0).quantizationParams().getScale();
            tflite_output_zero_point = tfliteInterpreter.getOutputTensor(0).quantizationParams().getZeroPoint();

            int inputSize = tfliteInterpreter.getInputTensor(0).numBytes();
            int outputSize = tfliteInterpreter.getOutputTensor(0).numBytes();
            inputBuffer = ByteBuffer.allocateDirect(inputSize).order(ByteOrder.nativeOrder());
            outputBuffer = ByteBuffer.allocateDirect(outputSize).order(ByteOrder.nativeOrder());

            Log.i("TFLite", "Model loaded successfully by service.");
        } catch (Exception e) {
            Log.e("TFLite", "Error loading TFLite model in service.", e);
            stopSelf(); // Stop the service if the model can't load
            return;
        }

        connectToMqtt();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.i("GestureListenerService", "Service Starting...");

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(FOREGROUND_NOTIFICATION_ID,
                    createPersistentNotification("Connecting to broker..."),
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        } else {
            startForeground(FOREGROUND_NOTIFICATION_ID,
                    createPersistentNotification("Connecting to broker..."));
        }

        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.w("GestureListenerService", "Service Destroying...");
        if (mqttClient != null && mqttClient.getState().isConnected()) {
            mqttClient.disconnect();
        }
        if (tfliteInterpreter != null) {
            tfliteInterpreter.close();
        }
    }

    private Notification createPersistentNotification(String text) {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0, notificationIntent, PendingIntent.FLAG_IMMUTABLE);

        return new NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
                .setContentTitle("Gesture Control is Active")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_menu_send) // Use your app's icon
                .setContentIntent(pendingIntent)
                .setOngoing(true) // Makes it non-swipeable
                .build();
    }

    private void updatePersistentNotification(String text) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        manager.notify(FOREGROUND_NOTIFICATION_ID, createPersistentNotification(text));
    }



    private Interpreter loadTFLiteModel() throws IOException {
        AssetFileDescriptor fileDescriptor = this.getAssets().openFd(TFLITE_MODEL_PATH);
        FileInputStream inputStream = new FileInputStream(fileDescriptor.getFileDescriptor());
        FileChannel fileChannel = inputStream.getChannel();
        long startOffset = fileDescriptor.getStartOffset();
        long declaredLength = fileDescriptor.getDeclaredLength();
        ByteBuffer modelBuffer = fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength);
        return new Interpreter(modelBuffer);
    }

    private void connectToMqtt() {
        mqttClient = MqttClient.builder()
                .useMqttVersion5()
                .identifier("AndroidApp-Service-" + UUID.randomUUID().toString())
                .serverHost(MQTT_BROKER)
                .serverPort(MQTT_PORT)
                .automaticReconnectWithDefaultConfig()
                .addDisconnectedListener(context -> {
                    Log.w("MQTT", "Connection Lost!");
                    updatePersistentNotification("MQTT Disconnected.");
                })
                .buildAsync();

        mqttClient.publishes(MqttGlobalPublishFilter.ALL, publish -> {
            byte[] payloadBytes = publish.getPayloadAsBytes();
            String payloadString = new String(payloadBytes, StandardCharsets.UTF_8);

            runInference(payloadString);
        });

        try {
            mqttClient.connect()
                    .whenComplete((connAck, throwable) -> {
                        if (throwable != null) {
                            Log.e("MQTT", "Connection Failure!", throwable);
                            updatePersistentNotification("MQTT Connection Failed.");
                        } else {
                            Log.i("MQTT", "Connection Success!");
                            updatePersistentNotification("Connected. Listening for gestures.");
                            subscribeToTopic();
                        }
                    });
        } catch (Exception e) {
            Log.e("MQTT", "Connection Error", e);
            updatePersistentNotification("MQTT Connection Error.");
        }
    }

    private void subscribeToTopic() {
        mqttClient.subscribeWith()
                .topicFilter(MQTT_TOPIC_SUBSCRIBE)
                .qos(MqttQos.AT_LEAST_ONCE)
                .send()
                .whenComplete((subAck, throwable) -> {
                    if (throwable != null) {
                        Log.e("MQTT", "Subscription failed!", throwable);
                        updatePersistentNotification("MQTT Subscription Failed.");
                    } else {
                        Log.i("MQTT", "Subscribed successfully!");
                    }
                });
    }

    private void runInference(String dataString) {
        if (tfliteInterpreter == null || dataString == null || dataString.isEmpty()) {
            return;
        }

        try {
            String[] stringValues = dataString.split(",");
            if (stringValues.length != NUM_FEATURES) {
                Log.w("Inference", "Malformed data packet. Got " + stringValues.length + " features.");
                return;
            }

            inputBuffer.clear();
            for (int i = 0; i < NUM_FEATURES; i++) {
                float floatVal = Float.parseFloat(stringValues[i]);
                byte int8Val = (byte) ((floatVal / tflite_input_scale) + tflite_input_zero_point);
                inputBuffer.put(int8Val);
            }

            outputBuffer.clear();
            tfliteInterpreter.run(inputBuffer, outputBuffer);

            outputBuffer.rewind();
            float[] dequantizedScores = new float[GESTURE_LABELS.length];

            for (int i = 0; i < GESTURE_LABELS.length; i++) {
                byte quantizedScore = outputBuffer.get(i);
                dequantizedScores[i] = (quantizedScore - tflite_output_zero_point) * tflite_output_scale;
            }

            int predictedClassId = -1;
            float maxScore = -Float.MAX_VALUE;
            for (int i = 0; i < GESTURE_LABELS.length; i++) {
                if (dequantizedScores[i] > maxScore) {
                    maxScore = dequantizedScores[i];
                    predictedClassId = i;
                }
            }

            if (predictedClassId == -1) {
                Log.w("Inference", "Prediction failed to find a max score.");
                return;
            }

            String predictedGesture = GESTURE_LABELS[predictedClassId];


            if (!predictedGesture.equals(pendingGesture)) {
                pendingGesture = predictedGesture;
                pendingGestureCount = 1;
            } else {
                pendingGestureCount++;
            }

            if (predictedGesture.equals("NO_HAND")) {
                if (!currentStableGesture.equals("NO_HAND")) {
                    Log.i("Inference", "Hand removed, resetting stable gesture.");
                }
                currentStableGesture = "NO_HAND";
                pendingGesture = "NO_HAND";
                pendingGestureCount = 0;
                return; // Do nothing
            }

            if (pendingGestureCount >= GESTURE_STABILITY_THRESHOLD) {

                if (!pendingGesture.equals(currentStableGesture)) {
                    Log.i("Inference", "New STABLE Gesture Detected: " + pendingGesture);
                    handleGesture(pendingGesture);
                    currentStableGesture = pendingGesture; // Set this as the new stable gesture
                }
            }

        } catch (Exception e) {
            Log.e("Inference", "Error during inference", e);
        }
    }

    private void handleGesture(String gesture) {
        if (gesture.equals("NO_HAND")) {
            return;
        }

        showActionNotification(gesture);

        if (gesture.equals("PLAY_PAUSE")) {
            Log.i("HandleGesture", "Handling PLAY_PAUSE");
            try {
                AudioManager am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
                if (am != null) {
                    am.dispatchMediaKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE));
                    am.dispatchMediaKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE));
                }
            } catch (Exception e) {
                Log.e("HandleGesture", "Error dispatching media key", e);
            }
        } else {
            Log.i("HandleGesture", "Broadcasting gesture to service: " + gesture);
            Intent intent = new Intent(MyGestureService.ACTION_PERFORM_GESTURE);
            intent.putExtra(MyGestureService.GESTURE_COMMAND, gesture);
            intent.setPackage(getPackageName());
            sendBroadcast(intent);
        }
    }

    private void showActionNotification(String gesture) {
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_menu_send)
                .setContentTitle("Gesture Detected!")
                .setContentText(gesture)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setOnlyAlertOnce(true)
                .setAutoCancel(true); // Will disappear after being tapped

        NotificationManagerCompat notificationManager = NotificationManagerCompat.from(this);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ActivityCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                Log.w("Notification", "POST_NOTIFICATIONS permission not granted.");
                return;
            }
        }
        notificationManager.notify(ACTION_NOTIFICATION_ID, builder.build());
    }
}
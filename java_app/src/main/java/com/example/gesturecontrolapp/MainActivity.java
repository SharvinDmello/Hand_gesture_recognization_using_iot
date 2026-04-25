package com.example.gesturecontrolapp;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import android.Manifest; // IMPORTANT

public class MainActivity extends AppCompatActivity {

    private static final String NOTIFICATION_CHANNEL_ID = "GestureControlChannel";
    private static final int NOTIFICATION_PERMISSION_CODE = 101;

    private Button btnStartService;
    private Button btnStopService;
    private TextView statusLabel;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        statusLabel = findViewById(R.id.status_label);
        btnStartService = findViewById(R.id.btn_start_service);
        btnStopService = findViewById(R.id.btn_stop_service);

        statusLabel.setText("Service is not running.");

        createNotificationChannel();

        requestNotificationPermission();

        btnStartService.setOnClickListener(v -> {
            startService();
            statusLabel.setText("Service Started.");
        });

        btnStopService.setOnClickListener(v -> {
            stopService();
            statusLabel.setText("Service Stopped.");
        });
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.POST_NOTIFICATIONS}, NOTIFICATION_PERMISSION_CODE);
            }
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            CharSequence name = "Gesture Control Channel";
            String description = "Channel for gesture control notifications";
            int importance = NotificationManager.IMPORTANCE_LOW; // Low so it's not noisy
            NotificationChannel channel = new NotificationChannel(NOTIFICATION_CHANNEL_ID, name, importance);
            channel.setDescription(description);
            NotificationManager notificationManager = getSystemService(NotificationManager.class);
            notificationManager.createNotificationChannel(channel);
        }
    }

    private void startService() {
        Log.i("MainActivity", "Starting service...");
        Intent serviceIntent = new Intent(this, GestureListenerService.class);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    private void stopService() {
        Log.i("MainActivity", "Stopping service...");
        Intent serviceIntent = new Intent(this, GestureListenerService.class);
        stopService(serviceIntent);
    }

}
package com.example.gesturecontrolapp; // Make sure this matches your package name

import androidx.core.content.ContextCompat;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Path;
import android.os.Build; // This import is fine, but not strictly needed for the fix
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.widget.Toast;


public class MyGestureService extends AccessibilityService {

    public static final String ACTION_PERFORM_GESTURE = "ACTION_PERFORM_GESTURE";
    public static final String GESTURE_COMMAND = "GESTURE_COMMAND";

    private GestureCommandReceiver gestureCommandReceiver;

    private class GestureCommandReceiver extends BroadcastReceiver {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (intent.getAction() != null && intent.getAction().equals(ACTION_PERFORM_GESTURE)) {
                String gesture = intent.getStringExtra(GESTURE_COMMAND);
                Log.i("MyGestureService", "Received command: " + gesture);

                new Thread(() -> {
                    Log.i("MyGestureService", "PERFORMING GESTURE: " + gesture);
                    switch (gesture) {
                        case "SCROLL_UP":
                            performScrollUp();
                            break;
                        case "SCROLL_DOWN":
                            performScrollDown();
                            break;
                        case "SWIPE_LEFT":
                            performSwipeLeft();
                            break;
                        case "SWIPE_RIGHT":
                            performSwipeRight();
                            break;
                        case "BACK_NAV":
                            performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK);
                            break;
                        case "PLAY_PAUSE":
                            Log.w("MyGestureService", "PLAY_PAUSE command received, but should be handled by listener service.");
                            break;
                    }
                }).start(); // Don't forget to start the thread!
            }
        }
    }

    @Override
    public void onServiceConnected() {
        super.onServiceConnected();
        Log.i("MyGestureService", "Accessibility Service Connected!");
        Toast.makeText(this, "Gesture Control Service Enabled!", Toast.LENGTH_SHORT).show();

        gestureCommandReceiver = new GestureCommandReceiver();
        IntentFilter filter = new IntentFilter(ACTION_PERFORM_GESTURE);


        ContextCompat.registerReceiver(this, gestureCommandReceiver, filter, ContextCompat.RECEIVER_NOT_EXPORTED);

    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (gestureCommandReceiver != null) {
            unregisterReceiver(gestureCommandReceiver);
        }
        Log.w("MyGestureService", "Accessibility Service Destroyed.");
    }


    private void performScrollUp() {
        DisplayMetrics displayMetrics = getResources().getDisplayMetrics();
        int middleX = displayMetrics.widthPixels / 2;
        int startY = (int) (displayMetrics.heightPixels * 0.25); // from 25%
        int endY = (int) (displayMetrics.heightPixels * 0.75);   // to 75%
        performSwipe(middleX, startY, middleX, endY);
    }

    private void performScrollDown() {
        DisplayMetrics displayMetrics = getResources().getDisplayMetrics();
        int middleX = displayMetrics.widthPixels / 2;
        int startY = (int) (displayMetrics.heightPixels * 0.75); // from 75%
        int endY = (int) (displayMetrics.heightPixels * 0.25);   // to 25%
        performSwipe(middleX, startY, middleX, endY);
    }

    private void performSwipeLeft() {
        DisplayMetrics displayMetrics = getResources().getDisplayMetrics();
        int middleY = displayMetrics.heightPixels / 2;
        int startX = (int) (displayMetrics.widthPixels * 0.75); // from 75%
        int endX = (int) (displayMetrics.widthPixels * 0.25);   // to 25%
        performSwipe(startX, middleY, endX, middleY);
    }

    private void performSwipeRight() {
        DisplayMetrics displayMetrics = getResources().getDisplayMetrics();
        int middleY = displayMetrics.heightPixels / 2;
        int startX = (int) (displayMetrics.widthPixels * 0.25); // from 25%
        int endX = (int) (displayMetrics.widthPixels * 0.75);   // to 75%
        performSwipe(startX, middleY, endX, middleY);
    }

    private void performSwipe(int x1, int y1, int x2, int y2) {
        Path path = new Path();
        path.moveTo(x1, y1);
        path.lineTo(x2, y2);

        GestureDescription.Builder gestureBuilder = new GestureDescription.Builder();
        gestureBuilder.addStroke(new GestureDescription.StrokeDescription(path, 0, 300));

        dispatchGesture(gestureBuilder.build(), new GestureResultCallback() {
            @Override
            public void onCompleted(GestureDescription gestureDescription) {
                super.onCompleted(gestureDescription);
                Log.i("MyGestureService", "Gesture COMPLETED.");
            }

            @Override
            public void onCancelled(GestureDescription gestureDescription) {
                super.onCancelled(gestureDescription);
                Log.e("MyGestureService", "Gesture CANCELLED.");
            }
        }, null);
    }


    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
    }

    @Override
    public void onInterrupt() {
    }
}
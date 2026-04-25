# Gesture Control System

A comprehensive gesture recognition system that uses computer vision to detect hand gestures and control remote devices via MQTT. The system bridges a Python-based computer vision application, an ESP32 microcontroller, and an Android application.

## 🚀 Features
- **Real-time hand gesture detection** using MediaPipe and OpenCV.
- **7 Distinct Gestures**: Scroll Up/Down, Swipe Left/Right, Play/Pause, Back Navigation, and No Hand.
- **Deep Learning Model**: Custom-trained Neural Network (TensorFlow/Keras) for high-accuracy classification.
- **IoT Integration**: Uses MQTT to transmit gesture data and landmarks across devices (`broker.hivemq.com`).
- **Cross-Platform**:
  - **Python Host**: Running CV and Inference.
  - **ESP32**: Serving as an MQTT bridge/relay.
  - **Android App**: Receives gesture commands for control.

## 📂 Project Structure

### Python (Host PC)
- `DataCollection.py`: Script to capture hand landmarks and create a dataset (`gesture_data.csv`).
- `ModelTraining.py`: Trains a Neural Network on the collected data and saves the model (`gesture_model.h5`) and scaler (`scaler.pkl`).
- `landmark_sender_esp32.py`: Captures webcam feed, extracts landmarks, scales them, and publishes to MQTT (`sharvin_gestures/landmarks`).
- `realtime_test.py`: For testing the model prediction in real-time.

### Embedded (ESP32)
- `Models/esp32_classifier_wifi/`: Arduino sketch for ESP32.
  - Connects to Wi-Fi and MQTT.
  - Subscribes to `sharvin_gestures/landmarks`.
  - Relays data to `sharvin_gestures/data_for_phone`.

### Android (Mobile App)
- `app/`: Android Studio project.
- **MainActivity**: Manages the UI and Notification permissions.
- **GestureListenerService**: background service to listen for MQTT messages and trigger actions.

## 🛠️ Setup & Usage

### 1. Python Environment
Install dependencies:
```bash
pip install opencv-python mediapipe numpy pandas tensorflow scikit-learn paho-mqtt
```

Run the Data Collection (if training new model):
```bash
python DataCollection.py
```

Train the Model:
```bash
python ModelTraining.py
```

Start the Gesture Sender:
```bash
python landmark_sender_esp32.py
```

### 2. ESP32 Setup
1. Open `Models/esp32_classifier_wifi/esp32_classifier_wifi.ino` in Arduino IDE.
2. Update `ssid` and `password` with your Wi-Fi credentials.
3. Upload to your ESP32 board.
4. Ensure the ESP32 is powered and connected to Wi-Fi.

### 3. Android App
1. Open the `app` folder in Android Studio.
2. Build and install the APK on your Android device.
3. Open the app and click "Start Service" to begin listening for gestures.

## 📡 MQTT Topics
- **Subscribe**: `sharvin_gestures/landmarks` (landmarks from Python)
- **Publish**: `sharvin_gestures/data_for_phone` (relayed to Phone)

## 🤝 Contribution
Feel free to submit issues and enhancement requests.

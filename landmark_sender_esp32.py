import cv2
import mediapipe as mp
import numpy as np
import pickle
import os
import paho.mqtt.client as mqtt # Import MQTT client
import time

SCALER_PATH = os.path.join('Models', 'scaler.pkl')

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_PUBLISH = "sharvin_gestures/landmarks"

SEND_INTERVAL = 0.1 # Send data roughly every 100ms

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

def connect_mqtt():
    """Connects to the MQTT broker."""
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="LaptopSender")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start() # Start a background thread to handle network
        print(f"Connected to MQTT Broker: {MQTT_BROKER}")
        return client
    except Exception as e:
        print(f"Failed to connect to MQTT Broker: {e}")
        return None

def load_scaler():
    """Loads the pre-trained StandardScaler object."""
    try:
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
        print(f"Scaler loaded successfully from {SCALER_PATH}")
        return scaler
    except FileNotFoundError:
        print(f"FATAL ERROR: Scaler file not found at {SCALER_PATH}")
        print("Ensure 'model_training.py' ran successfully.")
        return None
    except Exception as e:
        print(f"Error loading scaler: {e}")
        return None

def extract_and_scale_keypoints(results, scaler):
    """
    Extracts landmarks, scales them, and returns the 63 scaled values as a string.
    Returns None if no hand is detected.
    """
    if results.multi_hand_landmarks:
        try:
            hand = results.multi_hand_landmarks[0]
            raw_keypoints = np.array([[lm.x, lm.y, lm.z] for lm in hand.landmark]).flatten()

            scaled_keypoints = scaler.transform(raw_keypoints.reshape(1, -1))

            return ",".join(map(str, scaled_keypoints.flatten()))
        except Exception as e:
            print(f"Error during landmark scaling: {e}")
            return None # Return None on error
    else:
        return None

def main():
    scaler = load_scaler()
    if scaler is None:
        return

    mqtt_client = connect_mqtt()
    if mqtt_client is None:
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    last_send_time = 0

    with mp_hands.Hands(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5) as hands:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Ignoring empty camera frame.")
                continue

            frame = cv2.flip(frame, 1) # Mirror image
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            current_time = time.time()
            if current_time - last_send_time >= SEND_INTERVAL:
                data_string = extract_and_scale_keypoints(results, scaler)
                
                if data_string is not None:
                    result = mqtt_client.publish(MQTT_TOPIC_PUBLISH, data_string)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        print(f"Data PUBLISHED to {MQTT_TOPIC_PUBLISH} (Size: {len(data_string)})")
                    else:
                        print(f"Failed to publish data: {mqtt.error_string(result.rc)}")
                else:
                    print("No hand detected. Not publishing.")
                
                last_send_time = current_time

            cv2.imshow('Laptop Landmark Sender (MQTT)', frame)

            if cv2.waitKey(5) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    mqtt_client.loop_stop() # Stop the MQTT background thread
    mqtt_client.disconnect()
    print("MQTT disconnected. Webcam stopped.")

if __name__ == '__main__':
    main()


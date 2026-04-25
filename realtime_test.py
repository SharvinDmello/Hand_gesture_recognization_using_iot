import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
import pickle
import os
import sys

MODEL_FILE_PATH = os.path.join('Models', 'gesture_model.h5')
SCALER_FILE_PATH = os.path.join('Models', 'scaler.pkl')
NUM_FEATURES = 21 * 3

GESTURE_CLASSES_MAP = {
    0: 'NO_HAND / IDLE',        
    1: 'SCROLL_UP',
    2: 'SCROLL_DOWN',
    3: 'SWIPE_LEFT',
    4: 'SWIPE_RIGHT',
    5: 'PLAY_PAUSE',
    6: 'BACK_NAV',
}

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def load_ml_artifacts():
    """Loads the trained Keras model and the scaler object."""
    try:
        model = tf.keras.models.load_model(MODEL_FILE_PATH)
        print(f"Model loaded successfully from {MODEL_FILE_PATH}")
        
        with open(SCALER_FILE_PATH, 'rb') as f:
            scaler = pickle.load(f)
        print(f"Scaler loaded successfully from {SCALER_FILE_PATH}")
        
        return model, scaler
    except FileNotFoundError as e:
        print(f"Error: Required file not found: {e.filename}")
        print("Please ensure data_collection.py and model_training.py were run successfully.")
        sys.exit(1)

def extract_keypoints(results):
    """
    Extracts the normalized 21 hand landmarks (x, y, z) into a flattened 1D array.
    Returns a NumPy array of 63 zeros if no hand is detected.
    """
    keypoints = np.zeros(NUM_FEATURES) # Initialize with zeros (for NO_HAND/NO_DETECTION)
    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        keypoints = np.array([[lm.x, lm.y, lm.z] for lm in hand.landmark]).flatten()
    
    return keypoints


def run_realtime_test():
    """Initializes model, opens webcam, and displays real-time gesture prediction."""
    
    model, scaler = load_ml_artifacts()
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam (Camera index 0).")
        sys.exit(1)

    print("\nStarting Real-Time Gesture Recognition Test...")
    print("Press 'q' to exit the video feed.")

    with mp_hands.Hands(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        max_num_hands=1) as hands:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.flip(frame, 1) # Mirror the image for intuitive use
            
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = hands.process(image_rgb)
            image_rgb.flags.writeable = True

            predicted_gesture = GESTURE_CLASSES_MAP[0] # Default to NO_HAND / IDLE

            if results.multi_hand_landmarks:
                
                keypoints = extract_keypoints(results)
                
                keypoints_reshaped = keypoints.reshape(1, -1)
                
                keypoints_scaled = scaler.transform(keypoints_reshaped)

                predictions = model.predict(keypoints_scaled, verbose=0)
                
                predicted_class_id = np.argmax(predictions)
                
                predicted_gesture = GESTURE_CLASSES_MAP.get(predicted_class_id, "UNKNOWN")
                
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
                    )

            cv2.putText(frame, f"Gesture: {predicted_gesture}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            
            cv2.imshow('Real-Time Gesture Test', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    print("Test finished.")

if __name__ == '__main__':
    run_realtime_test()

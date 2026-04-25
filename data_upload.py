import cv2
import mediapipe as mp
import numpy as np
import pickle
import os
import sys
import json
from psycopg import connect, sql
import time

SCALER_FILE_PATH = os.path.join('Models', 'scaler.pkl')
NUM_FEATURES = 21 * 3 # 63 total features (21 landmarks * 3 coordinates)

NEON_DB_CONNECTION_STRING = 'postgresql://your_neonDB_creds'

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def load_scaler():
    """Loads the scaler object saved during model training."""
    try:
        with open(SCALER_FILE_PATH, 'rb') as f:
            scaler = pickle.load(f)
        print(f"Scaler loaded successfully from {SCALER_FILE_PATH}")
        return scaler
    except FileNotFoundError as e:
        print(f"Error: Scaler file not found: {e.filename}")
        print("Please ensure model_training.py was run successfully and scaler.pkl exists.")
        sys.exit(1)

def extract_keypoints(results):
    """
    Extracts the normalized 21 hand landmarks (x, y, z) into a flattened 1D array.
    Returns a NumPy array of 63 zeros if no hand is detected.
    """
    keypoints = np.zeros(NUM_FEATURES) 
    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        keypoints = np.array([[lm.x, lm.y, lm.z] for lm in hand.landmark]).flatten()
    
    return keypoints

def upload_raw_features(conn, features_list):
    """Inserts the raw, scaled feature vector into the 'raw_features' table."""
    try:
        features_json = json.dumps(features_list)
        
        with conn.cursor() as cur:
            insert_query = sql.SQL("""
                INSERT INTO raw_features (features) 
                VALUES (%s);
            """)
            cur.execute(insert_query, (features_json,))
        conn.commit()
    except Exception as e:
        print(f"DB Insert Error: {e}")


def run_data_upload():
    """Initializes and runs the real-time feature extraction and database upload loop."""
    
    if NEON_DB_CONNECTION_STRING == "YOUR_NEON_DB_CONNECTION_STRING":
        print("FATAL ERROR: Please replace 'YOUR_NEON_DB_CONNECTION_STRING' with your actual Neon connection string.")
        sys.exit(1)

    scaler = load_scaler()
    db_conn = None
    try:
        db_conn = connect(NEON_DB_CONNECTION_STRING)
        print("Database connection established successfully.")
    except Exception as e:
        print(f"FATAL DB ERROR: Could not connect to Neon DB. Check connection string and network. Error: {e}")
        sys.exit(1)


    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sys.exit(1)

    print("\nStarting Real-Time Feature Upload...")
    print("This script pushes raw hand features to the 'raw_features' table.")
    print("Press 'q' to exit the video feed.")

    with mp_hands.Hands(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        max_num_hands=1) as hands:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: 
                break

            frame = cv2.flip(frame, 1) 
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = hands.process(image_rgb)
            image_rgb.flags.writeable = True

            raw_keypoints = extract_keypoints(results)
            
            keypoints_reshaped = raw_keypoints.reshape(1, -1)
            keypoints_scaled = scaler.transform(keypoints_reshaped) 
            
            features_to_upload = keypoints_scaled[0].tolist()

            upload_raw_features(db_conn, features_to_upload)

            cv2.putText(frame, "STATUS: UPLOADING RAW DATA...", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Features: {len(features_to_upload)}", (20, 80), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            cv2.imshow('Raw Data Uploader', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            time.sleep(0.05) 

    cap.release()
    cv2.destroyAllWindows()
    if db_conn:
        db_conn.close()
    print("Data upload finished. Database connection closed.")

if __name__ == '__main__':
    run_data_upload()

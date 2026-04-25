import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping
import numpy as np
import os
import pickle
import sys

CSV_FILE_PATH = os.path.join('Data', 'gesture_data.csv')
MODEL_FILE_PATH = os.path.join('Models', 'gesture_model.h5')
SCALER_FILE_PATH = os.path.join('Models', 'scaler.pkl')
TEST_SIZE = 0.2     # 20% of data used for testing/validation
RANDOM_SEED = 42
NUM_CLASSES = 7     # Total number of gestures (0 to 6)
NUM_FEATURES = 63   # 21 landmarks * 3 coordinates (x, y, z)

def build_model():
    """
    Defines and compiles the sequential Keras Neural Network model.
    Uses three fully connected layers, suitable for classifying flattened landmark data.
    """
    print("\nBuilding Neural Network Model...")
    model = Sequential([
        Dense(128, activation='relu', input_shape=(NUM_FEATURES,)),
        Dense(64, activation='relu'),
        Dense(32, activation='relu'),
        Dense(NUM_CLASSES, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy', 
        metrics=['accuracy']
    )
    print(model.summary())
    return model

def train_model():
    """Loads data, preprocesses, trains the model, and saves the final artifacts."""
    print("Starting Model Training Phase...")
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        print(f"Loaded {len(df)} total samples from {CSV_FILE_PATH}")
    except FileNotFoundError:
        print(f"Error: Data file not found at {CSV_FILE_PATH}.")
        print("ACTION REQUIRED: Please ensure you ran data_collection.py first.")
        sys.exit(1)

    X = df.drop('class_id', axis=1).values
    y = df['class_id'].values

    if len(X) < 100 or len(np.unique(y)) < 2:
        print("Error: Dataset size is too small or only contains one class. Cannot train model.")
        sys.exit(1)

    y_categorical = to_categorical(y, num_classes=NUM_CLASSES)

    X_train, X_test, y_train_cat, y_test_cat = train_test_split(
        X, y_categorical, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=y
    )
    print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples.")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    if not os.path.exists(os.path.dirname(SCALER_FILE_PATH)):
        os.makedirs(os.path.dirname(SCALER_FILE_PATH))

    with open(SCALER_FILE_PATH, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"Normalization Scaler saved to {SCALER_FILE_PATH}")
    
    model = build_model()
    
    early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    print("\nTraining started (Max 100 epochs, will stop early if performance plateaus)...")
    model.fit(
        X_train_scaled,
        y_train_cat,
        epochs=100, 
        batch_size=32,
        validation_data=(X_test_scaled, y_test_cat),
        callbacks=[early_stopping],
        verbose=1
    )
    print("Training finished.")

    loss, accuracy = model.evaluate(X_test_scaled, y_test_cat, verbose=0)
    print("\n--- Model Evaluation ---")
    print(f"Test Loss: {loss:.4f}")
    print(f"Test Accuracy: {accuracy*100:.2f}%")
    
    model.save(MODEL_FILE_PATH)
    print(f"\nModel successfully saved to {MODEL_FILE_PATH}")

if __name__ == '__main__':
    train_model()

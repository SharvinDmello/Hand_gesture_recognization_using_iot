import tensorflow as tf
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

KERAS_MODEL_PATH = os.path.join('Models', 'gesture_model.h5')
TFLITE_MODEL_PATH = os.path.join('Models', 'gesture_model.tflite')
C_ARRAY_MODEL_PATH = os.path.join('Models', 'gesture_model_data.h') # Output C header file
CSV_FILE_PATH = os.path.join('Data', 'gesture_data.csv') # Needed for representative dataset

def hex_to_c_array(hex_data, var_name):
    c_str = ''
    c_str += '#ifndef ' + var_name.upper() + '_H\n'
    c_str += '#define ' + var_name.upper() + '_H\n\n'
    c_str += '\nunsigned int ' + var_name + '_len = ' + str(len(hex_data)) + ';\n'
    c_str += 'alignas(8) const unsigned char ' + var_name + '[] = {'
    hex_array = []
    for i, val in enumerate(hex_data) :
        hex_str = format(val, '#04x')
        if (i + 1) < len(hex_data):
            hex_str += ','
        if (i + 1) % 12 == 0:
            hex_str += '\n '
        hex_array.append(hex_str)
    c_str += '\n ' + format(' '.join(hex_array)) + '\n};\n\n'
    c_str += '#endif //' + var_name.upper() + '_H'
    return c_str


def convert_model():
    print("--- Starting Model Conversion ---")

    try:
        model = tf.keras.models.load_model(KERAS_MODEL_PATH)
        print(f"Successfully loaded Keras model from: {KERAS_MODEL_PATH}")
    except Exception as e:
        print(f"Error loading Keras model: {e}")
        return

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT] # Enable default optimizations (includes quantization)

    try:
        df = pd.read_csv(CSV_FILE_PATH)
        features = df.drop('class_id', axis=1).values
        representative_data = features[:100].astype(np.float32)

        def representative_dataset_gen():
            for i in range(len(representative_data)):
              yield [representative_data[i:i+1]]

        converter.representative_dataset = representative_dataset_gen
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.int8  # or tf.uint8 depending on your model needs
        converter.inference_output_type = tf.int8 # or tf.uint8

        print("Representative dataset loaded for quantization.")
    except Exception as e:
        print(f"Warning: Could not load or process representative dataset from {CSV_FILE_PATH}. Quantization might be less optimal. Error: {e}")
        pass # Continue without representative data if loading fails


    try:
        tflite_model_quant = converter.convert()
        with open(TFLITE_MODEL_PATH, 'wb') as f:
            f.write(tflite_model_quant)
        print(f"Successfully converted and saved TFLite model (quantized) to: {TFLITE_MODEL_PATH}")
        print(f"TFLite model size: {os.path.getsize(TFLITE_MODEL_PATH) / 1024:.2f} KB")
    except Exception as e:
        print(f"Error during TFLite conversion: {e}")
        return

    try:
        c_array_content = hex_to_c_array(tflite_model_quant, "gesture_model_data")

        with open(C_ARRAY_MODEL_PATH, 'w') as f:
            f.write(c_array_content)
        print(f"Successfully converted TFLite model to C array: {C_ARRAY_MODEL_PATH}")
    except Exception as e:
        print(f"Error converting TFLite model to C array: {e}")
        return

    print("--- Model Conversion Complete ---")

if __name__ == '__main__':
    print(f"Using TensorFlow version: {tf.__version__}")
    convert_model()
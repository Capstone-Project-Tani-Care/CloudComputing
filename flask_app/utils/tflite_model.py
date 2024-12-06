import tensorflow as tf
from google.cloud import storage
import numpy as np
import json
from typing import Dict, Any
import os

def load_class_names(json_path: str = './utils/class_names.json') -> Dict[str, Dict[int, str]]:

    try:
        with open(json_path, 'r') as f:
            # Load class names from JSON
            class_data = json.load(f)
            
            # Convert string keys to integers for class indices
            formatted_data = {}
            for plant, classes in class_data.items():
                formatted_data[plant] = {int(k): v for k, v in classes.items()}
            
            return formatted_data
    except Exception as e:
        print(f"Error loading class names from {json_path}: {e}")
        raise e

def load_tflite_model_from_gcs(bucket_name: str, model_name: str):

    try:
        client = storage.Client.from_service_account_json("bucket.json")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"models/{model_name}")

        model_content = blob.download_as_bytes()
        interpreter = tf.lite.Interpreter(model_content=model_content)
        interpreter.allocate_tensors()
        return interpreter
    except Exception as e:
        print(f"Error loading model {model_name} from GCS: {e}")
        raise e

def run_tflite_inference(interpreter: tf.lite.Interpreter, input_data: np.ndarray) -> Dict[str, Any]:

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    predictions = interpreter.get_tensor(output_details[0]['index'])[0]
    
    return predictions
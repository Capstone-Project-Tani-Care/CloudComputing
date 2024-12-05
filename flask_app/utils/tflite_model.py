import tensorflow as tf
from google.cloud import storage
import numpy as np

from google.cloud import storage
import tensorflow as tf

def load_tflite_model_from_gcs(bucket_name, model_name):

    try:
        client = storage.Client.from_service_account_json("bucket.json")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"models/{model_name}")

        # Read the TFLite model directly into memory
        model_content = blob.download_as_bytes()
        interpreter = tf.lite.Interpreter(model_content=model_content)
        interpreter.allocate_tensors()
        return interpreter
    except Exception as e:
        print(f"Error loading model {model_name} from GCS: {e}")
        raise e


def run_tflite_inference(interpreter, input_data):

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Set the input tensor
    interpreter.set_tensor(input_details[0]['index'], input_data)

    # Run inference
    interpreter.invoke()

    # Get the output tensor
    output_data = interpreter.get_tensor(output_details[0]['index'])
    return output_data

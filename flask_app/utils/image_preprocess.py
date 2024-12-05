from PIL import Image
import numpy as np

def preprocess_image(image_path, target_size):

    image = Image.open(image_path).convert('RGB')
    image = image.resize(target_size)
    image_array = np.array(image, dtype=np.float32)

    # Normalize the image data to [0, 1] if required by the model
    image_array = image_array / 255.0
    image_array = np.expand_dims(image_array, axis=0)  # Add batch dimension
    return image_array

# import os
# import numpy as np
# from PIL import Image
# import tensorflow as tf
# from tensorflow.keras import layers, Input, Model
# from tensorflow.keras.applications import ResNet50
# from tensorflow.keras.applications.resnet50 import preprocess_input

# ML_DIR = os.path.join(os.path.dirname(__file__), "..", "ml_model")

# IMG_SIZE = 224

# LABELS = {
#     0: "benign",
#     1: "malignant",
#     2: "normal",
# }

# MODEL_CONFIG = {
#     "ultrasound": {
#         "path":     os.path.join(ML_DIR, "breast_cancer_resnet50.keras"),
#         "version":  "ultrasound_resnet50_v1",
#         "img_size": IMG_SIZE,
#     },
#     # "mammogram": {
#     #     "path":     os.path.join(ML_DIR, "mammogram_resnet50.keras"),
#     #     "version":  "mammogram_resnet50_v1",
#     #     "img_size": IMG_SIZE,
#     # },
# }

# _models = {
#     "ultrasound": None,
# }


# # ══════════════════════════════════════════════════════════
# #  BUILD EXACT ARCHITECTURE + LOAD WEIGHTS
# #  Rebuilds the exact same architecture the DL team used:
# #  ResNet50 → GAP → Dense(256, relu) → Dropout(0.4) → Dense(3, softmax)
# #  Then loads weights directly from the .keras file
# # ══════════════════════════════════════════════════════════

# def get_model(image_type):
#     if image_type not in MODEL_CONFIG:
#         raise ValueError(f"Unknown image type: '{image_type}'. Must be 'ultrasound' or 'mammogram'.")

#     if _models[image_type] is None:
#         config     = MODEL_CONFIG[image_type]
#         model_path = config["path"]
#         img_size   = config["img_size"]

#         if not os.path.exists(model_path):
#             raise FileNotFoundError(
#                 f"Model file not found: {model_path}\n"
#                 f"Please place the {image_type} model in the ml_model/ folder."
#             )

#         # 1. Rebuild exact same architecture as DL team
#         base_model           = ResNet50(
#             weights      = "imagenet",
#             include_top  = False,
#             input_shape  = (img_size, img_size, 3)
#         )
#         base_model.trainable = False

#         inputs  = Input(shape=(img_size, img_size, 3))
#         x       = base_model(inputs, training=False)
#         x       = layers.GlobalAveragePooling2D()(x)
#         x       = layers.Dense(256, activation="relu")(x)
#         x       = layers.Dropout(0.4)(x)
#         outputs = layers.Dense(3, activation="softmax")(x)
#         model   = Model(inputs, outputs)

#         model.compile(
#             optimizer = tf.keras.optimizers.Adam(learning_rate=1e-4),
#             loss      = "categorical_crossentropy",
#             metrics   = ["accuracy"]
#         )

#         # 2. Load the trained weights from the .keras file
#         model.load_weights(model_path)

#         _models[image_type] = model
#         print(f"[ml_service] {image_type} model loaded successfully.")

#     return _models[image_type]


# # ══════════════════════════════════════════════════════════
# #  PREPROCESS — identical to DL team's code
# # ══════════════════════════════════════════════════════════

# def preprocess_image(image_path, img_size):
#     img = Image.open(image_path).convert("RGB")
#     img = img.resize((img_size, img_size))

#     arr = np.array(img, dtype=np.float32)
#     arr = np.expand_dims(arr, axis=0)
#     arr = preprocess_input(arr)

#     return arr


# # ══════════════════════════════════════════════════════════
# #  PREDICT — identical to DL team's code
# #  + adds probabilities for all 3 classes
# # ══════════════════════════════════════════════════════════

# def predict(image_path, image_type):
#     config   = MODEL_CONFIG[image_type]
#     model    = get_model(image_type)
#     img_size = config["img_size"]

#     input_tensor    = preprocess_image(image_path, img_size)
#     predictions     = model.predict(input_tensor, verbose=0)[0]
#     predicted_index = int(np.argmax(predictions))
#     predicted_class = LABELS[predicted_index]
#     confidence      = float(np.max(predictions))

#     probabilities = {
#         LABELS[i]: round(float(predictions[i]) * 100, 2)
#         for i in range(len(LABELS))
#     }

#     return {
#         "predicted_class": predicted_class,
#         "confidence":      round(confidence * 100, 2),
#         "probabilities":   probabilities,
#         "model_version":   config["version"],
#     }








import os
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras import layers, Input, Model
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from huggingface_hub import hf_hub_download

ML_DIR = os.path.join(os.path.dirname(__file__), "..", "ml_model")
os.makedirs(ML_DIR, exist_ok=True)

IMG_SIZE = 224

LABELS = {
    0: "benign",
    1: "malignant",
    2: "normal",
}

MODEL_CONFIG = {
    "ultrasound": {
        "hf_repo":  "MAI1222/breast_cancer_resnet50 ",   # ← your HF repo
        "filename": "breast_cancer_resnet50.keras",
        "version":  "ultrasound_resnet50_v1",
        "img_size": IMG_SIZE,
    },
}

_models = {
    "ultrasound": None,
}


def _download_model_if_needed(config):
    """
    Downloads model from Hugging Face if not already on disk.
    On Render — downloads once per deployment.
    """
    local_path = os.path.join(ML_DIR, config["filename"])

    if not os.path.exists(local_path):
        print(f"[ml_service] Downloading model from Hugging Face...")
        hf_hub_download(
            repo_id   = config["hf_repo"],
            filename  = config["filename"],
            local_dir = ML_DIR,
            token     = os.getenv("HF_TOKEN"),   # from Render env vars
        )
        print(f"[ml_service] Model downloaded to {local_path}")

    return local_path


def get_model(image_type):
    if image_type not in MODEL_CONFIG:
        raise ValueError(f"Unknown image type: '{image_type}'. Must be 'ultrasound' or 'mammogram'.")

    if _models[image_type] is None:
        config     = MODEL_CONFIG[image_type]
        model_path = _download_model_if_needed(config)
        img_size   = config["img_size"]

        # Rebuild exact architecture
        base_model           = ResNet50(weights="imagenet", include_top=False, input_shape=(img_size, img_size, 3))
        base_model.trainable = False

        inputs  = Input(shape=(img_size, img_size, 3))
        x       = base_model(inputs, training=False)
        x       = layers.GlobalAveragePooling2D()(x)
        x       = layers.Dense(256, activation="relu")(x)
        x       = layers.Dropout(0.4)(x)
        outputs = layers.Dense(3, activation="softmax")(x)
        model   = Model(inputs, outputs)

        model.compile(
            optimizer = tf.keras.optimizers.Adam(learning_rate=1e-4),
            loss      = "categorical_crossentropy",
            metrics   = ["accuracy"]
        )

        model.load_weights(model_path)
        _models[image_type] = model
        print(f"[ml_service] {image_type} model ready.")

    return _models[image_type]


def preprocess_image(image_path, img_size):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((img_size, img_size))
    arr = np.array(img, dtype=np.float32)
    arr = np.expand_dims(arr, axis=0)
    arr = preprocess_input(arr)
    return arr


def predict(image_path, image_type):
    config        = MODEL_CONFIG[image_type]
    model         = get_model(image_type)
    img_size      = config["img_size"]
    input_tensor  = preprocess_image(image_path, img_size)
    predictions   = model.predict(input_tensor, verbose=0)[0]
    predicted_index = int(np.argmax(predictions))
    predicted_class = LABELS[predicted_index]
    confidence      = float(np.max(predictions))

    probabilities = {
        LABELS[i]: round(float(predictions[i]) * 100, 2)
        for i in range(len(LABELS))
    }

    return {
        "predicted_class": predicted_class,
        "confidence":      round(confidence * 100, 2),
        "probabilities":   probabilities,
        "model_version":   config["version"],
    }
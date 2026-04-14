import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure     = True
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_FILE_SIZE_MB   = 10


# ══════════════════════════════════════════════════════════
#  VALIDATE
# ══════════════════════════════════════════════════════════

def validate_scan_image(file):
    """
    Returns (True, None) if valid, (False, error_message) if not.
    """
    if not file or file.filename == "":
        return False, "No file provided."

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}."

    file.seek(0, 2)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)

    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB."

    return True, None


# ══════════════════════════════════════════════════════════
#  UPLOAD
#  → Organized by image type and patient
# ══════════════════════════════════════════════════════════

def upload_scan_image(file, patient_id, image_type):
    """
    Uploads a scan image to Cloudinary.
    Stored under: breast_cancer/scans/<image_type>/<patient_id>/

    Args:
        file       (FileStorage): uploaded file
        patient_id (str):         patient's user_id
        image_type (str):         "ultrasound" or "mammogram"

    Returns:
        (image_url, public_id)
    """
    result = cloudinary.uploader.upload(
        file,
        folder          = f"breast_cancer/scans/{image_type}/{patient_id}",
        resource_type   = "image",
        allowed_formats = list(ALLOWED_EXTENSIONS),
        transformation  = [{"quality": "auto", "fetch_format": "auto"}],
    )

    return result["secure_url"], result["public_id"]


# ══════════════════════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════════════════════

def delete_scan_image(public_id):
    """Deletes an image from Cloudinary by its public_id."""
    cloudinary.uploader.destroy(public_id, resource_type="image")
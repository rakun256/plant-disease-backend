from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
import io
from app.core.exceptions import InvalidImageException
from app.core.config import settings

async def validate_and_open_image(file: UploadFile) -> Image.Image:
    if file.content_type not in settings.allowed_image_types_list:
        raise InvalidImageException(f"Unsupported file type: {file.content_type}")
    
    content = await file.read()
    if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise InvalidImageException(f"File size exceeds {settings.MAX_IMAGE_SIZE_MB}MB")
        
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()  # verify it's an image
        image = Image.open(io.BytesIO(content)) # open again for actual use
        return image
    except UnidentifiedImageError:
        raise InvalidImageException("Uploaded file is not a valid image")

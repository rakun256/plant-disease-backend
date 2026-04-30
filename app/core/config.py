from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Plant Disease Classifier API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str
    
    MODEL_PATH: str = "models/apple_disease_model.pth"
    LOW_CONFIDENCE_THRESHOLD: float = 0.70
    IMAGE_MIN_WIDTH: int = 224
    IMAGE_MIN_HEIGHT: int = 224
    IMAGE_DARK_THRESHOLD: float = 50.0
    IMAGE_BRIGHT_THRESHOLD: float = 215.0
    IMAGE_LOW_CONTRAST_THRESHOLD: float = 25.0
    IMAGE_BLUR_THRESHOLD: float = 20.0
    IMAGE_QUALITY_ACCEPTABLE_THRESHOLD: float = 0.60
    IMAGE_QUALITY_CRITICAL_WARNING_CAP: float = 0.49
    IMAGE_FOREGROUND_DARK_THRESHOLD: float = 10.0
    IMAGE_FOREGROUND_MIN_RATIO: float = 0.05
    IMAGE_FOREGROUND_MAX_RATIO: float = 0.98
    ENABLE_GRADCAM: bool = True
    GRADCAM_MAX_IMAGE_SIZE: int = 512
    GRADCAM_ALPHA: float = 0.45
    GRADCAM_TARGET_LAYER: str = "layer4"
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png"

    @property
    def allowed_image_types_list(self) -> List[str]:
        return self.ALLOWED_IMAGE_TYPES.split(",")

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

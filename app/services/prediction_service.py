from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.utils.file_utils import validate_and_open_image
from app.ml.transforms import preprocess_image
from app.ml.inference import predict
from app.ml.model_loader import ml_manager
from app.ml.class_names import CLASS_MAPPING
from app.schemas.prediction import GradCamExplanationResponse, ImageQualityResponse, PredictionResponse
from app.services.gradcam_service import generate_gradcam_explanation
from app.services.image_quality_service import assess_image_quality
from app.core.config import settings
from app.core.constants import LOW_CONFIDENCE_WARNING_MESSAGE, SUPPORTED_CLASSES, WARNING_MESSAGE
from app.models.prediction import Prediction
from app.models.user import User
from app.utils.logger import logger
import json
import time
from typing import Optional

async def process_prediction(
    file: UploadFile,
    save_result: bool,
    user: User,
    db: Session,
    include_explanation: bool = False,
) -> PredictionResponse:
    # 1. Validation and Read
    image = await validate_and_open_image(file)
    
    # 2. Preprocess
    image_quality = assess_image_quality(image)
    tensor = preprocess_image(image)
    
    # 3. Inference
    inference_start = time.perf_counter()
    predicted_class, confidence, scores = predict(tensor)
    inference_time_ms = round((time.perf_counter() - inference_start) * 1000, 2)
    is_low_confidence = confidence < settings.LOW_CONFIDENCE_THRESHOLD
    warning_messages = [LOW_CONFIDENCE_WARNING_MESSAGE if is_low_confidence else WARNING_MESSAGE]
    if not image_quality.is_quality_acceptable:
        warning_messages.extend(image_quality.quality_warnings)
    explanation = _build_explanation(include_explanation, tensor, image, predicted_class, warning_messages)
    warning = " ".join(warning_messages)
    
    # 4. Save to DB (Optional)
    if save_result and user:
        prediction_record = Prediction(
            user_id=user.id,
            image_name=file.filename,
            predicted_class=predicted_class,
            confidence=confidence,
            inference_time_ms=inference_time_ms,
            is_low_confidence=is_low_confidence,
            image_width=image_quality.width,
            image_height=image_quality.height,
            image_brightness_score=image_quality.brightness_score,
            image_contrast_score=image_quality.contrast_score,
            image_blur_score=image_quality.blur_score,
            image_quality_score=image_quality.quality_score,
            is_quality_acceptable=image_quality.is_quality_acceptable,
            quality_warnings_json=json.dumps(image_quality.quality_warnings),
            scores_json=json.dumps(scores),
            model_version=ml_manager.model_version
        )
        db.add(prediction_record)
        db.commit()

    return PredictionResponse(
        model_version=ml_manager.model_version,
        predicted_class=predicted_class,
        confidence=confidence,
        inference_time_ms=inference_time_ms,
        is_low_confidence=is_low_confidence,
        scores=scores,
        supported_classes=SUPPORTED_CLASSES,
        warning=warning,
        image_quality=ImageQualityResponse(**image_quality.to_dict()),
        explanation=explanation
    )


def _build_explanation(
    include_explanation: bool,
    tensor,
    image,
    predicted_class: str,
    warning_messages: list,
) -> Optional[GradCamExplanationResponse]:
    if not include_explanation:
        return None

    if not settings.ENABLE_GRADCAM:
        warning_messages.append("Grad-CAM explanation is currently disabled.")
        return None

    if not ml_manager.is_loaded or ml_manager.model is None:
        warning_messages.append("Grad-CAM explanation could not be generated because the model is not loaded.")
        return None

    class_to_index = {class_name: index for index, class_name in CLASS_MAPPING.items()}
    predicted_class_index = class_to_index.get(predicted_class)
    if predicted_class_index is None:
        warning_messages.append("Grad-CAM explanation could not be generated for the predicted class.")
        return None

    try:
        return generate_gradcam_explanation(
            model=ml_manager.model,
            tensor=tensor,
            original_image=image,
            predicted_class_index=predicted_class_index,
            class_name=predicted_class,
            device=ml_manager.device,
            target_layer_name=settings.GRADCAM_TARGET_LAYER,
        )
    except Exception as exc:
        logger.exception(f"Grad-CAM generation failed: {exc}")
        warning_messages.append("Grad-CAM explanation could not be generated for this image.")
        return None

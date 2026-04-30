from typing import Optional

from app.schemas.prediction import ImageQualityResponse, InputAssessmentResponse


LOW_CONFIDENCE_REASON = "LOW_CONFIDENCE"
LOW_IMAGE_QUALITY_REASON = "LOW_IMAGE_QUALITY"


def build_input_assessment(
    is_low_confidence: bool,
    image_quality: Optional[ImageQualityResponse],
) -> InputAssessmentResponse:
    reason_codes = []
    message_parts = []

    if is_low_confidence:
        reason_codes.append(LOW_CONFIDENCE_REASON)
        message_parts.append(
            "The model confidence is low, so this image may be outside the supported apple leaf classes."
        )

    if image_quality is not None and not image_quality.is_quality_acceptable:
        reason_codes.append(LOW_IMAGE_QUALITY_REASON)
        if image_quality.quality_warnings:
            message_parts.extend(image_quality.quality_warnings)
        else:
            message_parts.append("The image quality may reduce prediction reliability.")

    is_supported_input_likely = len(reason_codes) == 0
    should_show_prediction = is_supported_input_likely

    if not message_parts:
        message_parts.append("The image appears suitable for the supported apple leaf classification task.")

    return InputAssessmentResponse(
        is_supported_input_likely=is_supported_input_likely,
        should_show_prediction=should_show_prediction,
        reason_codes=reason_codes,
        message=" ".join(message_parts),
    )

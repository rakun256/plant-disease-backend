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

    has_critical_quality_warning = False
    if image_quality is not None:
        has_critical_quality_warning = _has_critical_quality_warning(image_quality.quality_warnings)

    if image_quality is not None and (not image_quality.is_quality_acceptable or has_critical_quality_warning):
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


def _has_critical_quality_warning(warnings: list[str]) -> bool:
    if not warnings:
        return False
    critical_markers = (
        "too dark",
        "too bright",
        "low contrast",
        "blurry",
        "resolution is low",
    )
    for warning in warnings:
        warning_lower = warning.lower()
        if any(marker in warning_lower for marker in critical_markers):
            return True
    return False

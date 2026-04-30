from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from PIL import Image

from app.core.config import settings


@dataclass
class ImageQualityResult:
    width: int
    height: int
    brightness_score: float
    contrast_score: float
    blur_score: float
    quality_score: float
    is_quality_acceptable: bool
    quality_warnings: List[str]

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "brightness_score": self.brightness_score,
            "contrast_score": self.contrast_score,
            "blur_score": self.blur_score,
            "quality_score": self.quality_score,
            "is_quality_acceptable": self.is_quality_acceptable,
            "quality_warnings": self.quality_warnings,
        }


def assess_image_quality(image: Image.Image) -> ImageQualityResult:
    image = image.convert("RGB")
    width, height = image.size
    grayscale = np.asarray(image.convert("L"), dtype=np.float32)

    brightness_score, contrast_score = _compute_brightness_contrast(grayscale)
    blur_score = round(_calculate_gradient_variance(grayscale), 2)

    quality_warnings = []
    resolution_ok = width >= settings.IMAGE_MIN_WIDTH and height >= settings.IMAGE_MIN_HEIGHT
    brightness_ok = settings.IMAGE_DARK_THRESHOLD <= brightness_score <= settings.IMAGE_BRIGHT_THRESHOLD
    contrast_ok = contrast_score >= settings.IMAGE_LOW_CONTRAST_THRESHOLD
    blur_ok = blur_score >= settings.IMAGE_BLUR_THRESHOLD

    if not resolution_ok:
        quality_warnings.append("The image resolution is low. Please upload a larger image.")
    if brightness_score < settings.IMAGE_DARK_THRESHOLD:
        quality_warnings.append("The image is too dark. Please use better lighting.")
    if brightness_score > settings.IMAGE_BRIGHT_THRESHOLD:
        quality_warnings.append("The image is too bright. Please avoid overexposed lighting.")
    if not contrast_ok:
        quality_warnings.append("The image has low contrast. Try taking the photo with a clearer background.")
    if not blur_ok:
        quality_warnings.append("The image appears blurry. Please retake the photo with a steady camera.")

    has_critical_warning = bool(quality_warnings)

    quality_score = round(
        (
            _resolution_component(width, height)
            + _brightness_component(brightness_score)
            + _threshold_component(contrast_score, settings.IMAGE_LOW_CONTRAST_THRESHOLD)
            + _threshold_component(blur_score, settings.IMAGE_BLUR_THRESHOLD)
        )
        / 4,
        2,
    )

    if has_critical_warning:
        quality_score = round(min(quality_score, settings.IMAGE_QUALITY_CRITICAL_WARNING_CAP), 2)

    return ImageQualityResult(
        width=width,
        height=height,
        brightness_score=brightness_score,
        contrast_score=contrast_score,
        blur_score=blur_score,
        quality_score=quality_score,
        is_quality_acceptable=(
            quality_score >= settings.IMAGE_QUALITY_ACCEPTABLE_THRESHOLD and not has_critical_warning
        ),
        quality_warnings=quality_warnings,
    )


def _compute_brightness_contrast(grayscale: np.ndarray) -> Tuple[float, float]:
    mask_threshold = settings.IMAGE_FOREGROUND_DARK_THRESHOLD
    min_ratio = settings.IMAGE_FOREGROUND_MIN_RATIO
    max_ratio = settings.IMAGE_FOREGROUND_MAX_RATIO
    mask = grayscale > mask_threshold
    mask_ratio = float(np.mean(mask))

    if min_ratio <= mask_ratio <= max_ratio:
        pixels = grayscale[mask]
    else:
        pixels = grayscale.ravel()

    brightness_score = round(float(np.mean(pixels)), 2)
    contrast_score = round(float(np.std(pixels)), 2)
    return brightness_score, contrast_score


def _calculate_gradient_variance(grayscale: np.ndarray) -> float:
    gradient_y, gradient_x = np.gradient(grayscale)
    gradient_magnitude = np.sqrt((gradient_x ** 2) + (gradient_y ** 2))
    return float(np.var(gradient_magnitude))


def _resolution_component(width: int, height: int) -> float:
    width_ratio = min(width / settings.IMAGE_MIN_WIDTH, 1)
    height_ratio = min(height / settings.IMAGE_MIN_HEIGHT, 1)
    return round(min(width_ratio, height_ratio), 2)


def _brightness_component(brightness_score: float) -> float:
    if brightness_score < settings.IMAGE_DARK_THRESHOLD:
        ratio = max(brightness_score / settings.IMAGE_DARK_THRESHOLD, 0)
        return round(ratio * ratio, 2)
    if brightness_score > settings.IMAGE_BRIGHT_THRESHOLD:
        overexposed_range = 255 - settings.IMAGE_BRIGHT_THRESHOLD
        ratio = max((255 - brightness_score) / overexposed_range, 0)
        return round(ratio * ratio, 2)
    return 1


def _threshold_component(score: float, threshold: float) -> float:
    return round(min(score / threshold, 1), 2)

import base64
import io
import time
from typing import Any, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from app.core.config import settings
from app.schemas.prediction import GradCamExplanationResponse


GRADCAM_DISCLAIMER = (
    "Grad-CAM is an approximate visual explanation of model attention and is not a "
    "replacement for expert agricultural diagnosis."
)


def generate_gradcam_explanation(
    model: torch.nn.Module,
    tensor: torch.Tensor,
    original_image: Image.Image,
    predicted_class_index: int,
    class_name: str,
    device: torch.device,
    target_layer_name: str = None,
) -> GradCamExplanationResponse:
    started_at = time.perf_counter()
    target_layer_name = target_layer_name or settings.GRADCAM_TARGET_LAYER
    target_layer = _resolve_target_layer(model, target_layer_name)
    activations = {}
    gradients = {}

    def forward_hook(module: torch.nn.Module, module_input: Tuple[Any], module_output: torch.Tensor):
        activations["value"] = module_output

    def backward_hook(module: torch.nn.Module, grad_input: Tuple[Any], grad_output: Tuple[torch.Tensor]):
        gradients["value"] = grad_output[0]

    forward_handle = target_layer.register_forward_hook(forward_hook)
    backward_handle = target_layer.register_full_backward_hook(backward_hook)

    was_training = model.training
    model.eval()

    try:
        model.zero_grad(set_to_none=True)
        input_tensor = tensor.to(device)
        outputs = model(input_tensor)
        score = outputs[:, predicted_class_index].sum()
        score.backward()

        heatmap = _build_heatmap(activations["value"], gradients["value"])
        explanation_image = _resize_for_explanation(original_image.convert("RGB"))
        heatmap_image = _heatmap_to_image(heatmap, explanation_image.size)
        overlay_image = _create_overlay(explanation_image, heatmap_image)
        explanation_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

        return GradCamExplanationResponse(
            method="Grad-CAM",
            target_class=class_name,
            target_layer=target_layer_name,
            image_format="png",
            overlay_image_base64=_image_to_base64_png(overlay_image),
            heatmap_image_base64=_image_to_base64_png(heatmap_image),
            disclaimer=GRADCAM_DISCLAIMER,
            explanation_time_ms=explanation_time_ms,
        )
    finally:
        forward_handle.remove()
        backward_handle.remove()
        model.zero_grad(set_to_none=True)
        if was_training:
            model.train()


def _resolve_target_layer(model: torch.nn.Module, target_layer_name: str) -> torch.nn.Module:
    layer = model
    for part in target_layer_name.split("."):
        if not hasattr(layer, part):
            raise ValueError(f"Grad-CAM target layer '{target_layer_name}' was not found")
        layer = getattr(layer, part)
    return layer


def _build_heatmap(activations: torch.Tensor, gradients: torch.Tensor) -> np.ndarray:
    weights = gradients.mean(dim=(2, 3), keepdim=True)
    cam = (weights * activations).sum(dim=1, keepdim=True)
    cam = F.relu(cam)
    cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
    cam = cam.squeeze().detach().cpu().numpy()
    cam_min = float(cam.min())
    cam_max = float(cam.max())
    if cam_max - cam_min <= 1e-8:
        return np.zeros_like(cam, dtype=np.float32)
    return ((cam - cam_min) / (cam_max - cam_min)).astype(np.float32)


def _resize_for_explanation(image: Image.Image) -> Image.Image:
    image = image.copy()
    image.thumbnail(
        (settings.GRADCAM_MAX_IMAGE_SIZE, settings.GRADCAM_MAX_IMAGE_SIZE),
        Image.Resampling.LANCZOS,
    )
    return image


def _heatmap_to_image(heatmap: np.ndarray, size: Tuple[int, int]) -> Image.Image:
    heatmap_image = Image.fromarray(np.uint8(heatmap * 255), mode="L").resize(size, Image.Resampling.BILINEAR)
    heatmap_array = np.asarray(heatmap_image, dtype=np.float32) / 255.0
    red = np.clip(255 * heatmap_array, 0, 255)
    green = np.clip(255 * (1 - np.abs(heatmap_array - 0.5) * 2), 0, 255)
    blue = np.clip(255 * (1 - heatmap_array), 0, 255)
    color_array = np.stack([red, green, blue], axis=-1).astype(np.uint8)
    return Image.fromarray(color_array, mode="RGB")


def _create_overlay(image: Image.Image, heatmap_image: Image.Image) -> Image.Image:
    alpha = max(0.0, min(settings.GRADCAM_ALPHA, 1.0))
    return Image.blend(image, heatmap_image, alpha)


def _image_to_base64_png(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

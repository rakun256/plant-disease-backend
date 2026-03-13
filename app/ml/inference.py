import torch
from app.ml.model_loader import ml_manager
from app.ml.class_names import CLASS_MAPPING
from typing import Dict, Tuple

def predict(tensor: torch.Tensor) -> Tuple[str, float, Dict[str, float]]:
    if not ml_manager.is_loaded or ml_manager.model is None:
        raise RuntimeError("Model is not loaded. Cannot perform inference.")

    with torch.no_grad():
        tensor = tensor.to(ml_manager.device)
        outputs = ml_manager.model(tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
        
        confidence, predicted_idx = torch.max(probabilities, 0)
        predicted_class = CLASS_MAPPING.get(predicted_idx.item(), "unknown")
        
        scores = {CLASS_MAPPING[i]: probabilities[i].item() for i in range(len(CLASS_MAPPING))}
        
        return predicted_class, confidence.item(), scores

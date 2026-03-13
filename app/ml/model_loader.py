import torch
import torchvision.models as models
import torch.nn as nn
from app.core.config import settings
from app.utils.logger import logger

class ModelManager:
    def __init__(self):
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_version = "resnet50_v1"
        self.is_loaded = False

    def load_model(self):
        try:
            # 3 sınıflı ResNet50 mimarisi oluşturuluyor
            num_classes = 3
            self.model = models.resnet50(weights=None)
            num_ftrs = self.model.fc.in_features
            self.model.fc = nn.Linear(num_ftrs, num_classes)
            
            # Kaydedilen state_dict ağırlıkları modele yükleniyor
            state_dict = torch.load(settings.MODEL_PATH, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            
            self.is_loaded = True
            logger.info(f"Model {self.model_version} successfully loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.is_loaded = False

ml_manager = ModelManager()

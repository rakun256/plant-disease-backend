import os
from pathlib import Path

# Dizinleri oluştur
directories = [
    "app/api/v1", "app/core", "app/db", "app/ml", "app/models",
    "app/repositories", "app/schemas", "app/services", "app/utils",
    "tests"
]
for d in directories:
    os.makedirs(d, exist_ok=True)
    Path(f"{d}/__init__.py").touch()
Path("app/__init__.py").touch()

# === ENV & DOCKER & REQUIREMENTS ===
with open(".env.example", "w") as f:
    f.write("""APP_NAME=Plant Disease Classifier API
APP_VERSION=1.0.0
DEBUG=True
API_V1_PREFIX=/api/v1
SECRET_KEY=supersecretkey_please_change_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=postgresql://user:password@localhost:5432/plant_db
MODEL_PATH=models/apple_disease_model.pth
MAX_IMAGE_SIZE_MB=5
ALLOWED_IMAGE_TYPES=image/jpeg,image/png
""")

with open("requirements.txt", "w") as f:
    f.write("""fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
pydantic-settings
python-multipart
pillow
torch
torchvision
python-jose[cryptography]
passlib[bcrypt]
alembic
pytest
httpx
""")

with open("Dockerfile", "w") as f:
    f.write("""FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları (psycopg2 ve Pillow için gerekebilir)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

with open("docker-compose.yml", "w") as f:
    f.write("""version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: plant_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/plant_db
      - SECRET_KEY=supersecretkey_please_change_in_production
    depends_on:
      - db

volumes:
  postgres_data:
""")

with open("README.md", "w") as f:
    f.write("""# Plant Disease Classifier Backend

Flutter mobil uygulaması için geliştirilmiş, Apple Leaf (Elma Yaprağı) hastalıklarını tespit eden (Healthy, Rust, Scab) FastAPI tabanlı backend.

## Kurulum
1. `python3 -m venv venv` ve `source venv/bin/activate` ile sanal ortam oluşturun.
2. `pip install -r requirements.txt` komutuyla bağımlılıkları yükleyin.
3. `.env.example` dosyasını `.env` olarak kopyalayarak veritabanı değişkenlerini ayarlayın.
4. `alembic init alembic` ve ardından migration dosyalarınızı oluşturarak `alembic upgrade head` ile veritabanını güncelleyin.
5. `uvicorn app.main:app --reload` ile projeyi başlatın.
6. `http://localhost:8000/docs` üzerinden Swagger arayüzüne erişebilirsiniz.

## Docker ile Kurulum
`docker-compose up --build` komutunu çalıştırarak veritabanı ve API'yi anında ayağa kaldırabilirsiniz.
""")

# === CORE ===
with open("app/core/config.py", "w") as f:
    f.write("""from pydantic_settings import BaseSettings, SettingsConfigDict
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
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png"

    @property
    def allowed_image_types_list(self) -> List[str]:
        return self.ALLOWED_IMAGE_TYPES.split(",")

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
""")

with open("app/core/constants.py", "w") as f:
    f.write("""# ML Constants
SUPPORTED_CLASSES = ["healthy", "rust", "scab"]
WARNING_MESSAGE = "The model currently only supports apple leaf classes from the specified academic dataset."

# Auth Constants
ALGORITHM = "HS256"
""")

with open("app/core/security.py", "w") as f:
    f.write("""from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
from app.core.config import settings
from app.core.constants import ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
""")

with open("app/core/exceptions.py", "w") as f:
    f.write("""from fastapi import HTTPException, status

class CredentialsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

class InvalidImageException(HTTPException):
    def __init__(self, detail: str = "Invalid image format"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
""")

# === DB ===
with open("app/db/database.py", "w") as f:
    f.write("""from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""")

# === MODELS ===
with open("app/models/base.py", "w") as f:
    f.write("""from sqlalchemy.orm import declarative_base
Base = declarative_base()
""")

with open("app/models/user.py", "w") as f:
    f.write("""from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
""")

with open("app/models/prediction.py", "w") as f:
    f.write("""from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime, timezone
from app.models.base import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_name = Column(String)
    predicted_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    scores_json = Column(Text)  # JSON string
    model_version = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
""")

# === SCHEMAS ===
with open("app/schemas/auth.py", "w") as f:
    f.write("""from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool

    class Config:
        from_attributes = True
""")

with open("app/schemas/prediction.py", "w") as f:
    f.write("""from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime

class PredictionResponse(BaseModel):
    model_version: str
    predicted_class: str
    confidence: float
    scores: Dict[str, float]
    supported_classes: List[str]
    warning: str

class PredictionHistoryResponse(BaseModel):
    id: int
    image_name: str
    predicted_class: str
    confidence: float
    model_version: str
    created_at: datetime
    scores: Dict[str, float]

    class Config:
        from_attributes = True
""")

with open("app/schemas/disease.py", "w") as f:
    f.write("""from pydantic import BaseModel
from typing import List

class DiseaseInfoResponse(BaseModel):
    name: str
    slug: str
    description: str
    recommendations: List[str]
    disclaimer: str
""")

# === ML ===
with open("app/ml/class_names.py", "w") as f:
    f.write("""CLASS_MAPPING = {
    0: "healthy",
    1: "rust",
    2: "scab"
}
""")

with open("app/ml/transforms.py", "w") as f:
    f.write("""from torchvision import transforms
from PIL import Image

def get_transforms():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

def preprocess_image(image: Image.Image):
    image = image.convert('RGB')
    transform = get_transforms()
    tensor = transform(image)
    return tensor.unsqueeze(0) # Add batch dimension
""")

with open("app/ml/model_loader.py", "w") as f:
    f.write("""import torch
from app.core.config import settings
from app.utils.logger import logger

class ModelManager:
    def __init__(self):
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_version = "mock_v1"
        self.is_loaded = False

    def load_model(self):
        try:
            # Gerçek model yükleme simülasyonu
            # self.model = torch.load(settings.MODEL_PATH, map_location=self.device)
            # self.model.eval()
            # self.model_version = "v1.0.0"
            self.model = None # Yüklenemediği durum için mock
            self.is_loaded = True
            logger.info(f"Model loaded on {self.device} (Mock Mode Active if path not found)")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.is_loaded = False

ml_manager = ModelManager()
""")

with open("app/ml/inference.py", "w") as f:
    f.write("""import torch
from app.ml.model_loader import ml_manager
from app.ml.class_names import CLASS_MAPPING
from typing import Dict, Tuple

def predict(tensor: torch.Tensor) -> Tuple[str, float, Dict[str, float]]:
    # Mock fallback, eğer model yüklenememişse
    if ml_manager.model is None:
        scores = {"healthy": 0.1, "rust": 0.85, "scab": 0.05}
        return "rust", 0.85, scores

    with torch.no_grad():
        tensor = tensor.to(ml_manager.device)
        outputs = ml_manager.model(tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
        
        confidence, predicted_idx = torch.max(probabilities, 0)
        predicted_class = CLASS_MAPPING.get(predicted_idx.item(), "unknown")
        
        scores = {CLASS_MAPPING[i]: probabilities[i].item() for i in range(len(CLASS_MAPPING))}
        
        return predicted_class, confidence.item(), scores
""")

# === UTILS VE LOGGING ===
with open("app/utils/logger.py", "w") as f:
    f.write("""import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("plant_disease_api")
""")

with open("app/utils/file_utils.py", "w") as f:
    f.write("""from fastapi import UploadFile
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
""")

# === REPOSITORIES AND SERVICES ===
with open("app/api/dependencies.py", "w") as f:
    f.write("""from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.exceptions import CredentialsException
from jose import jwt, JWTError
from app.core.config import settings
from app.core.constants import ALGORITHM
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise CredentialsException()
    except JWTError:
        raise CredentialsException()
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise CredentialsException()
    return user
""")

with open("app/services/prediction_service.py", "w") as f:
    f.write("""from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.utils.file_utils import validate_and_open_image
from app.ml.transforms import preprocess_image
from app.ml.inference import predict
from app.ml.model_loader import ml_manager
from app.schemas.prediction import PredictionResponse
from app.core.constants import SUPPORTED_CLASSES, WARNING_MESSAGE
from app.models.prediction import Prediction
from app.models.user import User
import json

async def process_prediction(file: UploadFile, save_result: bool, user: User, db: Session) -> PredictionResponse:
    # 1. Validation and Read
    image = await validate_and_open_image(file)
    
    # 2. Preprocess
    tensor = preprocess_image(image)
    
    # 3. Inference
    predicted_class, confidence, scores = predict(tensor)
    
    # 4. Save to DB (Optional)
    if save_result and user:
        prediction_record = Prediction(
            user_id=user.id,
            image_name=file.filename,
            predicted_class=predicted_class,
            confidence=confidence,
            scores_json=json.dumps(scores),
            model_version=ml_manager.model_version
        )
        db.add(prediction_record)
        db.commit()

    return PredictionResponse(
        model_version=ml_manager.model_version,
        predicted_class=predicted_class,
        confidence=confidence,
        scores=scores,
        supported_classes=SUPPORTED_CLASSES,
        warning=WARNING_MESSAGE
    )
""")

# === ENDPOINTS ===
with open("app/api/v1/health.py", "w") as f:
    f.write("""from fastapi import APIRouter
from app.core.config import settings
from app.ml.model_loader import ml_manager

router = APIRouter()

@router.get("/")
def health_check():
    return {
        "status": "ok",
        "model_loaded": ml_manager.is_loaded,
        "version": settings.APP_VERSION
    }
""")

with open("app/api/v1/predictions.py", "w") as f:
    f.write("""from fastapi import APIRouter, File, UploadFile, Depends, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.services.prediction_service import process_prediction
from app.schemas.prediction import PredictionResponse
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=PredictionResponse, summary="Predict disease from leaf image")
async def predict_image(
    file: UploadFile = File(...),
    save_result: bool = Form(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"
    Upload an image of an apple leaf to get a disease prediction.
    Supported types: JPEG, PNG. Max size: 5MB
    \"\"\"
    return await process_prediction(file, save_result, current_user, db)
""")

with open("app/api/v1/history.py", "w") as f:
    f.write("""from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionHistoryResponse
import json

router = APIRouter()

@router.get("/", response_model=List[PredictionHistoryResponse])
def get_prediction_history(
    skip: int = 0, limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    predictions = db.query(Prediction).filter(Prediction.user_id == current_user.id).offset(skip).limit(limit).all()
    
    results = []
    for p in predictions:
        results.append(PredictionHistoryResponse(
            id=p.id,
            image_name=p.image_name,
            predicted_class=p.predicted_class,
            confidence=p.confidence,
            model_version=p.model_version,
            created_at=p.created_at,
            scores=json.loads(p.scores_json) if p.scores_json else {}
        ))
    return results
""")

with open("app/api/v1/diseases.py", "w") as f:
    f.write("""from fastapi import APIRouter, HTTPException
from app.schemas.disease import DiseaseInfoResponse

router = APIRouter()

DISEASES_DB = {
    "healthy": {
        "name": "Healthy Apple Leaf", "slug": "healthy",
        "description": "The leaf shows no signs of disease.",
        "recommendations": ["Maintain a regular spray schedule.", "Ensure proper watering."],
        "disclaimer": "This is an AI prediction, consult an agricultural expert."
    },
    "rust": {
        "name": "Cedar Apple Rust", "slug": "rust",
        "description": "A fungal disease causing yellow-orange spots.",
        "recommendations": ["Apply appropriate fungicide.", "Remove nearby cedar rust galls."],
        "disclaimer": "This is an AI prediction, consult an agricultural expert."
    },
    "scab": {
        "name": "Apple Scab", "slug": "scab",
        "description": "Fungal disease causing olive-green to black spots.",
        "recommendations": ["Apply fungicide preventatively.", "Clear fallen infected leaves."],
        "disclaimer": "This is an AI prediction, consult an agricultural expert."
    }
}

@router.get("/{slug}", response_model=DiseaseInfoResponse)
def get_disease_info(slug: str):
    data = DISEASES_DB.get(slug.lower())
    if not data:
        raise HTTPException(status_code=404, detail="Disease not found")
    return data
""")

with open("app/main.py", "w") as f:
    f.write("""from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import health, predictions, history, diseases
from app.ml.model_loader import ml_manager

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend for Deep Learning based Plant Disease Classification (Apple Leaf)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Geliştirme için Flutter isteklerine izin (Production'da daraltılmalı)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    ml_manager.load_model()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})

app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}/health", tags=["Health"])
app.include_router(predictions.router, prefix=f"{settings.API_V1_PREFIX}/predictions", tags=["Predictions"])
app.include_router(history.router, prefix=f"{settings.API_V1_PREFIX}/history", tags=["History"])
app.include_router(diseases.router, prefix=f"{settings.API_V1_PREFIX}/diseases", tags=["Diseases"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Plant Disease Classifier API"}
""")

print("Proje klasör yapısı ve temel dosyalar oluşturuldu!")

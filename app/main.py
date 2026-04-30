from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import analytics, health, predictions, history, diseases, auth
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
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Auth"])
app.include_router(predictions.router, prefix=f"{settings.API_V1_PREFIX}/predictions", tags=["Predictions"])
app.include_router(history.router, prefix=f"{settings.API_V1_PREFIX}/history", tags=["History"])
app.include_router(diseases.router, prefix=f"{settings.API_V1_PREFIX}/diseases", tags=["Diseases"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Plant Disease Classifier API"}

@app.head("/")
def head_root():
    return None

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.auth import router as auth_router
from app.routes.unsubscribe import router as unsubscribe_router

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title="Email Bot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(unsubscribe_router)


@app.get("/")
def root():
    return {"status": "ok", "app": "Email Bot API"}


@app.get("/health")
def health():
    return {"status": "ok"}

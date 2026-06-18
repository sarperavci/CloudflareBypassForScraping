import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict

from .routes import setup_routes, lifespan


class HealthResponse(BaseModel):
    status: str
    version: str
    features: list


class CookieResponse(BaseModel):
    cookies: Dict[str, str]
    user_agent: str


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cloudflare Bypasser",
        description="CloakBrowser-based Cloudflare bypasser with request mirroring",
        version="2.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    setup_routes(app)
    return app
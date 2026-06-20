import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cf_bypasser.utils.constants import APP_VERSION
from .routes import setup_routes, lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cloudflare Bypasser",
        description="CloakBrowser-based Cloudflare bypasser with request mirroring",
        version=APP_VERSION,
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

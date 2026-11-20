"""App factory. Every package under app/features/ that exposes `router` is mounted automatically,
so adding a feature never requires editing this file (see docs/adr/0003)."""

import importlib
import pkgutil
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db, features


def discover_routers():
    for module in sorted(pkgutil.iter_modules(features.__path__), key=lambda m: m.name):
        if not module.ispkg:
            continue
        try:
            router_module = importlib.import_module(f"{features.__name__}.{module.name}.router")
        except ModuleNotFoundError:
            continue
        router = getattr(router_module, "router", None)
        if router is not None:
            yield module.name, router


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Multi-agent Notes API", lifespan=lifespan)
    for _name, router in discover_routers():
        app.include_router(router)
    return app


app = create_app()

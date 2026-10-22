from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.api.routes import auth, health, dashboard, users, institutions, applications

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting", service=settings.app_name, environment=settings.environment)
    yield
    logger.info("shutting_down", service=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="End-to-end AICTE Approval Workflow Automation, Compliance Monitoring, and Alert Management System",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(institutions.router)
app.include_router(applications.router)

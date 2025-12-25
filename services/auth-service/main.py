from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_router, users_router
from config import settings
from contextlib import asynccontextmanager
from dependencies import get_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Startup
    redis_conn = await get_redis()
    await redis_conn.ping()
    print("✅ Connected to Redis")

    yield

    # Shutdown
    await redis_conn.close()
    print("👋 Closed Redis connection")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": settings.APP_VERSION
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Conecta Plus Auth Service",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

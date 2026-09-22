#create a FastAPI app with CORS middleware and health check router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, collection_points, collection_transactions, health, inventory, materials, sync

settings = get_settings()

app = FastAPI(title=settings.app_name)# gives

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(collection_points.router, prefix=settings.api_v1_prefix)
app.include_router(materials.router, prefix=settings.api_v1_prefix)
app.include_router(collection_transactions.router, prefix=settings.api_v1_prefix)
app.include_router(sync.router, prefix=settings.api_v1_prefix)
app.include_router(inventory.router, prefix=settings.api_v1_prefix)

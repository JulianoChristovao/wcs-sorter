"""
WCS Sorter - Aplicação principal (FastAPI).
Warehouse Control System para integração Sorter ↔ WMS.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, JSONResponse

from app.core.config import settings
from app.routers import auth, sorter, pedidos, mapeamento, usuarios, dashboard, logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    yield
    # Shutdown
    print("🛑 Encerrando aplicação...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Warehouse Control System (WCS) responsável por receber pedidos do WMS, "
        "fornecer decisões de roteamento em tempo real ao sorter e confirmar a "
        "separação de volta ao WMS."
    ),
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
prefix = settings.API_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(sorter.router, prefix=prefix)
app.include_router(pedidos.router, prefix=prefix)
app.include_router(mapeamento.router, prefix=prefix)
app.include_router(usuarios.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(logs.router, prefix=prefix)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Evita resposta 500 sem detalhe (útil quando a migração não foi aplicada)."""
    from fastapi import HTTPException as FastAPIHTTPException
    from starlette.exceptions import HTTPException as StarletteHTTPException

    if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )



@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Bem-vindo ao {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    }
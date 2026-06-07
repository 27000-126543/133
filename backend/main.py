import sys
import os

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
sys.path.insert(0, _root_dir)
sys.path.insert(0, _backend_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from web_config import WebConfig
from database import init_db
from security import init_default_admin
from scheduler import get_scheduler
from models import Base
from database import engine

from routers.auth_router import router as auth_router
from routers.certificate_router import router as certificate_router
from routers.task_router import router as task_router
from routers.employee_router import router as employee_router
from routers.report_router import router as report_router

Base.metadata.create_all(bind=engine)

scheduler = get_scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Certificate Management System...")
    init_db()
    init_default_admin()
    
    scheduler.start()
    print("Scheduler started")
    
    yield
    
    scheduler.shutdown()
    print("Scheduler shutdown")
    print("Certificate Management System shutdown complete")


app = FastAPI(
    title="企业级员工资质证书自动化管理系统",
    description="支持证书OCR识别、合规检查、任务管理、报告生成的全栈Web应用",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=WebConfig.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from config import Config
Config.ensure_dirs()

app.mount("/uploads", StaticFiles(directory=Config.UPLOAD_DIR), name="uploads")
app.mount("/reports", StaticFiles(directory=Config.REPORT_DIR), name="reports")

api_prefix = WebConfig.API_V1_PREFIX
app.include_router(auth_router, prefix=api_prefix)
app.include_router(certificate_router, prefix=api_prefix)
app.include_router(task_router, prefix=api_prefix)
app.include_router(employee_router, prefix=api_prefix)
app.include_router(report_router, prefix=api_prefix)


@app.get("/")
async def root():
    return {
        "message": "企业级员工资质证书自动化管理系统 API",
        "version": "2.0.0",
        "docs": "/docs",
        "api_prefix": api_prefix,
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "scheduler_running": scheduler.scheduler.running if scheduler.use_apscheduler and scheduler.scheduler else True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=WebConfig.BACKEND_HOST,
        port=WebConfig.BACKEND_PORT,
        reload=True,
        log_level="info",
    )

import sys
import os

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
sys.path.insert(0, _root_dir)
sys.path.insert(0, _backend_dir)

import uvicorn
import webbrowser
import threading
import time
import subprocess

from web_config import WebConfig
from config import Config

Config.ensure_dirs()


def start_backend():
    """启动后端服务"""
    print(f"Starting backend server on http://{WebConfig.BACKEND_HOST}:{WebConfig.BACKEND_PORT}")
    uvicorn.run(
        "main:app",
        host=WebConfig.BACKEND_HOST,
        port=WebConfig.BACKEND_PORT,
        reload=False,
        log_level="info",
    )


def start_frontend():
    """启动前端开发服务器"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
    
    if not os.path.exists(frontend_dir):
        print("Frontend directory not found, skipping frontend start")
        return None
    
    package_json = os.path.join(frontend_dir, "package.json")
    if not os.path.exists(package_json):
        print("package.json not found, skipping frontend start")
        return None
    
    try:
        print("Starting frontend dev server...")
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return process
    except Exception as e:
        print(f"Failed to start frontend: {e}")
        return None


def open_browser():
    """在浏览器中打开应用"""
    time.sleep(3)
    
    urls = [
        f"http://localhost:{WebConfig.BACKEND_PORT}/docs",
        "http://localhost:5173",
    ]
    
    for url in urls:
        try:
            webbrowser.open(url)
            print(f"Opened {url} in browser")
            break
        except Exception:
            continue


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Certificate Management System - Full Stack Launcher")
    parser.add_argument("--backend-only", action="store_true", help="Only start backend")
    parser.add_argument("--frontend-only", action="store_true", help="Only start frontend")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--init-demo", action="store_true", help="Initialize demo data first")
    
    args = parser.parse_args()
    
    if args.init_demo:
        print("Initializing demo data...")
        sys.path.insert(0, os.path.dirname(__file__))
        from main import init_db
        from security import init_default_admin
        from database import Base, engine
        
        Base.metadata.create_all(bind=engine)
        init_db()
        init_default_admin()
        
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from main import get_certificate_management_system
        cms = get_certificate_management_system()
        cms.initialize_demo_data()
        print("Demo data initialized")
    
    if args.backend_only:
        start_backend()
    elif args.frontend_only:
        frontend_process = start_frontend()
        if frontend_process:
            if not args.no_browser:
                open_browser()
            frontend_process.wait()
    else:
        if not args.no_browser:
            threading.Thread(target=open_browser, daemon=True).start()
        
        frontend_process = start_frontend()
        
        try:
            start_backend()
        except KeyboardInterrupt:
            if frontend_process:
                frontend_process.terminate()

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")

try:
    from backend.main import app
    print("\n✅ 1. 后端应用导入成功")
    print(f"   - 路由数量: {len(app.routes)}")
except Exception as e:
    print(f"\n❌ 1. 后端应用导入失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

try:
    from config import Config, WebConfig
    print("\n✅ 2. 配置模块导入成功")
    print(f"   - 上传目录: {Config.UPLOAD_DIR}")
    print(f"   - 报告目录: {Config.REPORT_DIR}")
except Exception as e:
    print(f"\n❌ 2. 配置模块导入失败: {type(e).__name__}: {e}")

try:
    from database import init_db, get_db_session
    print("\n✅ 3. 数据库模块导入成功")
except Exception as e:
    print(f"\n❌ 3. 数据库模块导入失败: {type(e).__name__}: {e}")

try:
    from security import init_default_admin, get_password_hash
    print("\n✅ 4. 安全模块导入成功")
except Exception as e:
    print(f"\n❌ 4. 安全模块导入失败: {type(e).__name__}: {e}")

try:
    from scheduler import get_scheduler
    scheduler = get_scheduler()
    print("\n✅ 5. 调度器模块导入成功")
    print(f"   - 使用APScheduler: {scheduler.use_apscheduler}")
except Exception as e:
    print(f"\n❌ 5. 调度器模块导入失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

try:
    from ocr_engine import get_ocr_engine
    ocr_engine = get_ocr_engine()
    print("\n✅ 6. OCR引擎模块导入成功")
    print(f"   - 引擎类型: {ocr_engine.engine_type}")
    print(f"   - 是否可用: {ocr_engine.is_available()}")
except Exception as e:
    print(f"\n❌ 6. OCR引擎模块导入失败: {type(e).__name__}: {e}")

print("\n==================================")
print("导入测试完成！")
print("==================================")

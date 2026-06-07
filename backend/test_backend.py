import sys
import os

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
sys.path.insert(0, _root_dir)
sys.path.insert(0, _backend_dir)

print("Testing backend imports from backend directory...")
print(f"Backend dir: {_backend_dir}")
print(f"Root dir: {_root_dir}")
print(f"sys.path[0]: {sys.path[0]}")
print(f"sys.path[1]: {sys.path[1]}")

try:
    import config
    print(f"\n✅ config module path: {config.__file__}")
    print(f"   Has WebConfig: {hasattr(config, 'WebConfig')}")
except Exception as e:
    print(f"\n❌ config import failed: {e}")

try:
    from main import app
    print("\n✅ 后端应用导入成功")
    print(f"   - 标题: {app.title}")
    print(f"   - 版本: {app.version}")
    print(f"   - 路由数量: {len(app.routes)}")
    
    print("\n📋 API路由列表:")
    for route in app.routes:
        if hasattr(route, 'path') and '/api/v1' in route.path:
            methods = ','.join(route.methods) if hasattr(route, 'methods') else ''
            print(f"   {methods:10} {route.path}")
            
except Exception as e:
    print(f"\n❌ 后端应用导入失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n==================================")
print("后端导入测试完成！")
print("==================================")

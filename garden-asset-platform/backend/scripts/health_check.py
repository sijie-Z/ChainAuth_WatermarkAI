"""
系统健康检查脚本
"""
import os
import sys


def check_python():
    """检查Python环境"""
    print("\n[Python环境]")
    version = sys.version_info
    print(f"  版本: {version.major}.{version.minor}.{version.micro}")
    print(f"  路径: {sys.executable}")

    if version.major >= 3 and version.minor >= 9:
        print("  状态: ✓ 满足要求")
        return True
    else:
        print("  状态: ✗ 版本过低，需要3.9+")
        return False


def check_packages():
    """检查Python包"""
    print("\n[Python依赖包]")

    packages = [
        ('flask', 'Flask'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('flask_jwt_extended', 'Flask-JWT-Extended'),
        ('pillow', 'Pillow'),
        ('geopandas', 'GeoPandas'),
        ('zhipuai', 'ZhipuAI'),
        ('web3', 'Web3'),
        ('redis', 'Redis'),
        ('celery', 'Celery')
    ]

    all_ok = True
    for module, name in packages:
        try:
            __import__(module)
            print(f"  {name}: ✓")
        except ImportError:
            print(f"  {name}: ✗ 未安装")
            all_ok = False

    return all_ok


def check_node():
    """检查Node.js"""
    print("\n[Node.js环境]")

    import subprocess

    try:
        result = subprocess.run(['node', '-v'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  版本: {version}")
            print("  状态: ✓")
            return True
    except:
        pass

    print("  状态: ✗ 未安装")
    return False


def check_npm():
    """检查npm"""
    print("\n[npm]")

    import subprocess

    try:
        result = subprocess.run(['npm', '-v'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  版本: {version}")
            print("  状态: ✓")
            return True
    except:
        pass

    print("  状态: ✗ 未安装")
    return False


def check_database():
    """检查数据库连接"""
    print("\n[数据库]")

    try:
        from app import create_app
        from app.extensions import db

        app = create_app('testing')
        with app.app_context():
            db.session.execute('SELECT 1')
        print("  连接: ✓")
        return True
    except Exception as e:
        print(f"  连接: ✗ {e}")
        return False


def check_redis():
    """检查Redis"""
    print("\n[Redis]")

    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print("  连接: ✓")
        return True
    except:
        print("  连接: ✗ 未运行或未安装")
        return False


def check_directories():
    """检查必要目录"""
    print("\n[必要目录]")

    dirs = [
        './uploads',
        './uploads/originals',
        './uploads/watermarked',
        './uploads/extracted',
        './data/watermark',
        './logs'
    ]

    all_ok = True
    for d in dirs:
        if os.path.exists(d):
            print(f"  {d}: ✓")
        else:
            print(f"  {d}: ✗ 不存在")
            all_ok = False

    return all_ok


def check_env():
    """检查环境变量"""
    print("\n[环境变量]")

    env_vars = [
        'SECRET_KEY',
        'JWT_SECRET_KEY',
        'DATABASE_URL',
        'ZHIPU_API_KEY'
    ]

    all_ok = True
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            masked = value[:8] + '...' if len(value) > 8 else value
            print(f"  {var}: ✓ ({masked})")
        else:
            print(f"  {var}: ✗ 未设置")
            all_ok = False

    return all_ok


def health_check():
    """完整健康检查"""
    print("=" * 60)
    print("系统健康检查")
    print("苏州园林数字资产安全分发与溯源系统")
    print("=" * 60)

    results = []

    results.append(check_python())
    results.append(check_packages())
    results.append(check_node())
    results.append(check_npm())
    results.append(check_database())
    results.append(check_redis())
    results.append(check_directories())
    results.append(check_env())

    print("\n" + "=" * 60)
    if all(results):
        print("状态: ✓ 所有检查通过")
    else:
        print("状态: ✗ 部分检查未通过，请查看上方详情")
    print("=" * 60)

    return all(results)


if __name__ == '__main__':
    health_check()
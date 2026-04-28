#!/usr/bin/env python
"""
一键启动脚本
自动检测环境并启动服务
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def check_python():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python版本过低，需要3.9+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_node():
    """检查Node.js"""
    try:
        result = subprocess.run(['node', '-v'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("❌ Node.js未安装")
    return False


def check_postgres():
    """检查PostgreSQL"""
    try:
        import psycopg2
        print("✅ psycopg2已安装")
        return True
    except ImportError:
        print("⚠️ psycopg2未安装，将使用SQLite")
        return False


def check_redis():
    """检查Redis"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print("✅ Redis连接正常")
        return True
    except:
        print("⚠️ Redis未运行或未安装")
        return False


def install_backend_deps():
    """安装后端依赖"""
    print("\n📦 安装后端依赖...")
    backend_dir = Path(__file__).parent / 'backend'
    os.chdir(backend_dir)

    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print("✅ 后端依赖安装完成")
        return True
    else:
        print(f"❌ 后端依赖安装失败: {result.stderr}")
        return False


def install_frontend_deps():
    """安装前端依赖"""
    print("\n📦 安装前端依赖...")
    frontend_dir = Path(__file__).parent / 'frontend'
    os.chdir(frontend_dir)

    # Windows需要shell=True
    shell = sys.platform == 'win32'
    result = subprocess.run(['npm', 'install'], shell=shell)

    if result.returncode == 0:
        print("✅ 前端依赖安装完成")
        return True
    else:
        print("❌ 前端依赖安装失败")
        return False


def init_database():
    """初始化数据库"""
    print("\n🗄️ 初始化数据库...")
    backend_dir = Path(__file__).parent / 'backend'
    os.chdir(backend_dir)

    result = subprocess.run([sys.executable, 'scripts/init_db.py'])

    return result.returncode == 0


def create_watermark():
    """创建水印文件"""
    print("\n🖼️ 创建水印文件...")
    backend_dir = Path(__file__).parent / 'backend'
    os.chdir(backend_dir)

    result = subprocess.run([sys.executable, 'scripts/create_watermark.py'])

    return result.returncode == 0


def start_backend():
    """启动后端服务"""
    print("\n🚀 启动后端服务...")
    backend_dir = Path(__file__).parent / 'backend'
    os.chdir(backend_dir)

    subprocess.run([sys.executable, 'run.py'])


def start_frontend():
    """启动前端服务"""
    print("\n🚀 启动前端服务...")
    frontend_dir = Path(__file__).parent / 'frontend'
    os.chdir(frontend_dir)

    shell = sys.platform == 'win32'
    subprocess.run(['npm', 'run', 'dev'], shell=shell)


def check_env():
    """检查环境变量文件"""
    backend_dir = Path(__file__).parent / 'backend'
    env_file = backend_dir / '.env'

    if not env_file.exists():
        print("⚠️ .env文件不存在，从示例创建...")
        env_example = backend_dir / '.env.example'
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ 已创建.env文件")
        else:
            print("❌ .env.example文件不存在")
            return False
    else:
        print("✅ .env文件已存在")

    return True


def main():
    parser = argparse.ArgumentParser(description='项目管理脚本')
    parser.add_argument('command', nargs='?', default='check',
                       choices=['check', 'install', 'init', 'backend', 'frontend', 'all'],
                       help='执行命令')

    args = parser.parse_args()

    print("=" * 60)
    print("苏州园林数字资产安全分发与溯源系统")
    print("=" * 60)

    if args.command == 'check':
        print("\n📋 环境检查\n")
        check_python()
        check_node()
        check_postgres()
        check_redis()
        check_env()

    elif args.command == 'install':
        install_backend_deps()
        install_frontend_deps()

    elif args.command == 'init':
        check_env()
        init_database()
        create_watermark()

    elif args.command == 'backend':
        start_backend()

    elif args.command == 'frontend':
        start_frontend()

    elif args.command == 'all':
        print("\n🚀 完整安装流程\n")
        if not check_python():
            return

        install_backend_deps()
        install_frontend_deps()
        check_env()
        init_database()
        create_watermark()

        print("\n" + "=" * 60)
        print("✅ 安装完成！")
        print("=" * 60)
        print("\n启动命令:")
        print("  python start.py backend   # 启动后端")
        print("  python start.py frontend  # 启动前端")
        print("\n默认账号:")
        print("  admin / admin123")


if __name__ == '__main__':
    main()
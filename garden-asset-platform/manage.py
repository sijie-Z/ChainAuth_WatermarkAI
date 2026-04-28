"""
启动脚本集合
提供不同环境的启动方式
"""
import os
import sys
import subprocess
import argparse


def run_backend():
    """启动后端服务"""
    os.chdir('backend')
    subprocess.run([sys.executable, 'run.py'])


def run_frontend():
    """启动前端服务"""
    os.chdir('frontend')
    if sys.platform == 'win32':
        subprocess.run(['npm', 'run', 'dev'], shell=True)
    else:
        subprocess.run(['npm', 'run', 'dev'])


def init_database():
    """初始化数据库"""
    os.chdir('backend')
    subprocess.run([sys.executable, 'scripts/init_db.py'])


def run_tests():
    """运行测试"""
    os.chdir('backend')
    subprocess.run(['pytest', '-v'])


def install_deps():
    """安装依赖"""
    print("安装后端依赖...")
    os.chdir('backend')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

    print("安装前端依赖...")
    os.chdir('../frontend')
    if sys.platform == 'win32':
        subprocess.run(['npm', 'install'], shell=True)
    else:
        subprocess.run(['npm', 'install'])


def docker_up():
    """启动Docker容器"""
    subprocess.run(['docker-compose', 'up', '-d'])


def docker_down():
    """停止Docker容器"""
    subprocess.run(['docker-compose', 'down'])


def main():
    parser = argparse.ArgumentParser(description='项目管理脚本')
    parser.add_argument('command', choices=[
        'backend', 'frontend', 'init', 'test', 'install',
        'docker-up', 'docker-down'
    ], help='执行命令')

    args = parser.parse_args()

    commands = {
        'backend': run_backend,
        'frontend': run_frontend,
        'init': init_database,
        'test': run_tests,
        'install': install_deps,
        'docker-up': docker_up,
        'docker-down': docker_down
    }

    commands[args.command]()


if __name__ == '__main__':
    main()
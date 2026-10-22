"""内存受限环境下的后端测试入口

Windows 开发机上一次性收集/运行全部 pytest 用例容易触发内存压力：
pytest 会把所有测试模块、Flask 应用和算法依赖加载进同一个进程，
进程随后被系统终止（退出码 127/负值），看起来像测试失败。

本脚本改为“每个测试文件一个独立子进程”，串行执行，并限制 OpenBLAS/
OpenMP/NumExpr 线程池，避免单个进程占用过多内存。每个文件的临时目录
放在项目 `.scratch/pytest/runner/` 下，不写到盘符根目录。

用法：
    python scripts/run_tests.py
    python scripts/run_tests.py --pattern test_license*.py --fail-fast
    python scripts/run_tests.py --verbose
"""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = BACKEND_DIR / 'tests'
# worktree 根目录下的 .scratch（与手工 pytest --basetemp 保持一致）
SCRATCH_ROOT = BACKEND_DIR.parents[1] / '.scratch' / 'pytest' / 'runner'

try:
    import psutil
except ImportError:  # psutil 是可选依赖，仅用于显示峰值内存
    psutil = None

PASS_RE = re.compile(r'(\d+) passed')
FAIL_RE = re.compile(r'(\d+) failed')
ERROR_RE = re.compile(r'(\d+) error')


def discover(pattern):
    return sorted(TESTS_DIR.glob(pattern))


def child_env():
    env = os.environ.copy()
    env.update({
        'PYTHONPATH': str(BACKEND_DIR),
        'PYTHONUNBUFFERED': '1',
        'PYTHONUTF8': '1',
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONDONTWRITEBYTECODE': '1',
        # 限制 native 线程池，避免每个进程按 CPU 核数申请大量内存
        'OPENBLAS_NUM_THREADS': '1',
        'OMP_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1',
        'VECLIB_MAXIMUM_THREADS': '1',
        # 测试固定关闭外部能力，避免误加载模型或访问网络
        'AI_ENABLED': 'false',
        'RATELIMIT_ENABLED': 'false',
        'HF_HUB_OFFLINE': '1',
    })
    return env


def monitor_memory(proc, result):
    """后台轮询子进程峰值内存，避免把输出缓冲也读进主进程。"""
    if psutil is None:
        return
    try:
        process = psutil.Process(proc.pid)
    except psutil.Error:
        return
    while proc.poll() is None:
        try:
            result['peak'] = max(
                result.get('peak', 0), process.memory_info().rss
            )
        except psutil.Error:
            break
        time.sleep(0.2)


def run_file(test_file):
    name = test_file.stem
    basetemp = SCRATCH_ROOT / name
    basetemp.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, '-m', 'pytest', str(test_file),
        '-q', '--basetemp', str(basetemp), '-p', 'no:cacheprovider',
    ]
    started = time.time()
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(BACKEND_DIR),
            env=child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
    except OSError as exc:
        return {
            'name': name,
            'returncode': -1,
            'passed': 0,
            'failed': 0,
            'errors': 1,
            'duration': time.time() - started,
            'peak_mb': 0,
            'killed': True,
            'output': f'无法启动测试子进程（通常是可用内存不足）：{exc}',
        }
    result = {'peak': 0}
    if psutil is not None:
        import threading
        thread = threading.Thread(
            target=monitor_memory, args=(proc, result), daemon=True
        )
        thread.start()
    output, _ = proc.communicate()
    duration = time.time() - started

    passed = sum(int(value) for value in PASS_RE.findall(output))
    failed = sum(int(value) for value in FAIL_RE.findall(output))
    errors = sum(int(value) for value in ERROR_RE.findall(output))
    killed = proc.returncode not in (0, 1)
    return {
        'name': name,
        'returncode': proc.returncode,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'duration': duration,
        'peak_mb': round(result.get('peak', 0) / 1024 / 1024),
        'killed': killed,
        'output': output,
    }


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='按测试文件隔离运行后端 pytest')
    parser.add_argument('--pattern', default='test_*.py', help='测试文件 glob')
    parser.add_argument('--fail-fast', action='store_true', help='首个失败后停止')
    parser.add_argument('--verbose', action='store_true', help='失败时输出完整日志')
    parser.add_argument('--tail', type=int, default=40, help='失败时输出的末尾行数')
    args = parser.parse_args()

    files = discover(args.pattern)
    if not files:
        print(f'未找到测试文件: {TESTS_DIR / args.pattern}')
        return 2

    print(f'内存安全测试模式：{len(files)} 个文件，逐文件串行执行')
    print(f'临时目录：{SCRATCH_ROOT}')
    if psutil is None:
        print('提示：未安装 psutil，无法显示峰值内存')

    results = []
    total_started = time.time()
    for index, test_file in enumerate(files, start=1):
        print(f'[{index:>2}/{len(files)}] {test_file.name:<42}', end='', flush=True)
        result = run_file(test_file)
        results.append(result)
        status = 'PASS' if result['returncode'] == 0 else (
            'KILLED' if result['killed'] else 'FAIL'
        )
        memory = f" {result['peak_mb']}MB" if result['peak_mb'] else ''
        counts = (
            f" {result['passed']} passed"
            + (f", {result['failed']} failed" if result['failed'] else '')
            + (f", {result['errors']} error" if result['errors'] else '')
        )
        print(
            f' {status:<6} {result["duration"]:5.1f}s{memory}{counts}',
            flush=True,
        )
        if result['returncode'] != 0:
            tail = result['output'].splitlines()[-args.tail:]
            print('  ' + '\n  '.join(tail) if tail else '  （无输出）')
            if args.verbose:
                print(result['output'])
            if args.fail_fast:
                break

    total_duration = time.time() - total_started
    passed = sum(item['passed'] for item in results)
    failed = sum(item['failed'] for item in results)
    errors = sum(item['errors'] for item in results)
    killed = [item['name'] for item in results if item['killed']]
    bad = [
        item['name'] for item in results
        if item['returncode'] != 0
    ]
    peak = max((item['peak_mb'] for item in results), default=0)

    print('\n' + '=' * 68)
    print(
        f'汇总：{len(results)} 个文件，{passed} passed，'
        f'{failed} failed，{errors} error，耗时 {total_duration:.1f}s，'
        f'单文件峰值 {peak}MB'
    )
    if killed:
        print(f'被系统终止（通常是内存不足）：{", ".join(killed)}')
    if bad:
        print(f'未通过文件：{", ".join(bad)}')
        return 1
    print('全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())

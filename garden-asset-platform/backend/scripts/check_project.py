"""
项目完整性检查脚本
检查所有关键文件是否存在和配置正确
"""
import os
import sys

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 需要检查的关键文件
CRITICAL_FILES = {
    'backend': [
        'app/__init__.py',
        'app/config.py',
        'app/extensions.py',
        'app/models/__init__.py',
        'app/models/user.py',
        'app/models/garden.py',
        'app/models/asset.py',
        'app/models/license.py',
        'app/models/blockchain.py',
        'app/models/log.py',
        'app/models/extra.py',
        'app/models/task.py',
        'app/resources/__init__.py',
        'app/resources/auth.py',
        'app/resources/asset.py',
        'app/resources/garden.py',
        'app/resources/watermark.py',
        'app/resources/blockchain.py',
        'app/resources/tasks.py',
        'app/resources/license.py',
        'app/resources/ai.py',
        'app/services/__init__.py',
        'app/services/watermark_service.py',
        'app/services/blockchain_service.py',
        'app/services/task_service.py',
        'app/services/license_scope.py',
        'app/services/email_service.py',
        'app/services/ai_service.py',
        'algorithm/__init__.py',
        'algorithm/vector/__init__.py',
        'algorithm/vector/embed.py',
        'algorithm/vector/extract.py',
        'algorithm/raster/__init__.py',
        'algorithm/raster/embed.py',
        'algorithm/raster/extract.py',
        'algorithm/utils/__init__.py',
        'algorithm/utils/get_coor.py',
        'algorithm/utils/to_geodataframe.py',
        'algorithm/utils/nc.py',
        'scripts/init_db.py',
        'scripts/create_test_data.py',
        'scripts/create_watermark.py',
        'scripts/health_check.py',
        'scripts/run_tests.py',
        'run.py',
        'requirements.txt',
        '.env.example',
    ],
    'frontend': [
        'src/main.js',
        'src/App.vue',
        'src/router/index.js',
        'src/stores/user.js',
        'src/api/index.js',
        'src/api/modules.js',
        'src/assets/styles/variables.scss',
        'src/assets/styles/main.scss',
        'src/views/home/index.vue',
        'src/views/home/login.vue',
        'src/views/home/register.vue',
        'src/views/asset/list.vue',
        'src/views/asset/detail.vue',
        'src/views/asset/upload.vue',
        'src/views/trace/index.vue',
        'src/views/license/apply.vue',
        'src/views/license/my.vue',
        'src/views/certificate/index.vue',
        'src/views/admin/layout.vue',
        'src/views/admin/dashboard.vue',
        'src/views/admin/assets.vue',
        'src/views/admin/watermark.vue',
        'src/views/admin/license-pending.vue',
        'src/views/admin/license-approved.vue',
        'src/views/admin/blockchain.vue',
        'src/views/admin/tasks.vue',
        'src/views/admin/infringements.vue',
        'src/views/admin/users.vue',
        'package.json',
        'vite.config.js',
        'index.html',
        '.env.development',
    ],
    'root': [
        'README.md',
        'DEVELOPMENT.md',
        'docker-compose.yml',
        'Dockerfile',
        'Makefile',
        'start.py',
    ]
}

def check_files():
    """检查所有关键文件"""
    results = {
        'backend': {'total': 0, 'found': 0, 'missing': []},
        'frontend': {'total': 0, 'found': 0, 'missing': []},
        'root': {'total': 0, 'found': 0, 'missing': []}
    }

    for category, files in CRITICAL_FILES.items():
        if category == 'backend':
            base = os.path.join(PROJECT_ROOT, 'backend')
        elif category == 'frontend':
            base = os.path.join(PROJECT_ROOT, 'frontend')
        else:
            base = PROJECT_ROOT

        for file in files:
            results[category]['total'] += 1
            path = os.path.join(base, file)
            if os.path.exists(path):
                results[category]['found'] += 1
            else:
                results[category]['missing'].append(file)

    return results

def print_report(results):
    """打印检查报告"""
    print("\n" + "=" * 60)
    print("苏州园林数字资产平台 - 项目完整性检查报告")
    print("=" * 60)

    total_all = 0
    found_all = 0

    for category, data in results.items():
        total_all += data['total']
        found_all += data['found']
        percentage = (data['found'] / data['total'] * 100) if data['total'] > 0 else 0

        status = "OK" if data['found'] == data['total'] else "X"
        print(f"\n[{category.upper()}] {status} {data['found']}/{data['total']} ({percentage:.1f}%)")

        if data['missing']:
            print("  缺失文件:")
            for f in data['missing'][:5]:  # 只显示前5个
                print(f"    - {f}")
            if len(data['missing']) > 5:
                print(f"    ... 还有 {len(data['missing']) - 5} 个文件")

    print("\n" + "-" * 60)
    overall_percentage = (found_all / total_all * 100) if total_all > 0 else 0
    overall_status = "完整" if found_all == total_all else "不完整"
    print(f"总计: {found_all}/{total_all} ({overall_percentage:.1f}%) - {overall_status}")
    print("=" * 60 + "\n")

    return found_all == total_all

if __name__ == '__main__':
    results = check_files()
    is_complete = print_report(results)
    sys.exit(0 if is_complete else 1)

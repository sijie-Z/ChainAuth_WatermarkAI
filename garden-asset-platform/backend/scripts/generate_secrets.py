"""生成生产环境随机密钥

用法：
    python scripts/generate_secrets.py

把输出写入部署环境的 SECRET_KEY / JWT_SECRET_KEY。
生产配置会拒绝示例占位文本与长度不足 32 位的密钥。
"""
import secrets


def main():
    print(f'SECRET_KEY={secrets.token_hex(32)}')
    print(f'JWT_SECRET_KEY={secrets.token_hex(32)}')


if __name__ == '__main__':
    main()

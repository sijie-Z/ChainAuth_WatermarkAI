"""
默认水印生成
创建用于测试的默认水印图片
"""
import os
from PIL import Image, ImageDraw, ImageFont


def create_default_watermark(output_path, text="SZGARDEN", size=(128, 128)):
    """创建默认水印图片"""
    # 创建透明背景
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # 使用默认字体
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()

    # 计算文本位置
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    # 绘制半透明文字
    draw.text((x, y), text, fill=(128, 128, 128, 128), font=font)

    # 保存
    img.save(output_path, 'PNG')
    print(f"水印图片已创建: {output_path}")


def create_watermark_with_id(output_path, watermark_id, garden_name="苏州园林"):
    """创建带ID的水印图片"""
    size = (256, 64)
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 10)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 绘制园林名称
    draw.text((10, 8), garden_name, fill=(0, 100, 200, 200), font=font_large)

    # 绘制水印ID
    draw.text((10, 32), watermark_id, fill=(100, 100, 100, 180), font=font_small)

    img.save(output_path, 'PNG')
    return output_path


def init_watermark_folder(base_dir):
    """初始化水印文件夹"""
    watermark_dir = os.path.join(base_dir, 'data', 'watermark')
    os.makedirs(watermark_dir, exist_ok=True)

    default_path = os.path.join(watermark_dir, 'default.png')
    if not os.path.exists(default_path):
        create_default_watermark(default_path)

    return watermark_dir


if __name__ == '__main__':
    # 测试生成
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    init_watermark_folder(base)

    # 生成带ID的水印示例
    sample_path = os.path.join(base, 'data', 'watermark', 'sample_ZZY-IMG-20260426123456-A1B2.png')
    create_watermark_with_id(sample_path, 'ZY-IMG-20260426123456-A1B2')
"""
水印算法测试脚本
验证DCT和矢量坐标扰动算法
"""
import os
import sys
import numpy as np
from PIL import Image

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_watermark():
    """创建测试水印图像"""
    # 创建一个简单的二值水印
    watermark = np.zeros((64, 64), dtype=np.uint8)

    # 添加一些图案
    watermark[10:20, 10:50] = 255  # 上方横线
    watermark[20:30, 20:30] = 255  # 左方块
    watermark[20:30, 40:50] = 255  # 右方块
    watermark[30:40, 15:25] = 255  # 中左方块
    watermark[30:40, 35:45] = 255  # 中右方块
    watermark[40:50, 10:50] = 255  # 下方横线

    # 添加标识文字像素
    watermark[15, 30] = 255
    watermark[25, 25] = 255
    watermark[25, 45] = 255

    return Image.fromarray(watermark)


def create_test_image():
    """创建测试图像"""
    # 创建一个256x256的测试图像
    img = np.random.randint(100, 200, (256, 256), dtype=np.uint8)

    # 添加一些图案使其更像真实图像
    img[50:100, 50:100] = 150
    img[100:150, 100:150] = 180
    img[150:200, 150:200] = 120

    return Image.fromarray(img)


def test_raster_watermark():
    """测试栅格水印嵌入和提取"""
    print("=" * 60)
    print("栅格水印算法测试")
    print("=" * 60)

    # 创建测试目录
    test_dir = os.path.join(os.path.dirname(__file__), 'test_output')
    os.makedirs(test_dir, exist_ok=True)

    # 创建测试图像和水印
    test_image = create_test_image()
    watermark = create_test_watermark()

    image_path = os.path.join(test_dir, 'test_image.png')
    watermark_path = os.path.join(test_dir, 'test_watermark.png')

    test_image.save(image_path)
    watermark.save(watermark_path)

    print(f"测试图像: {image_path}")
    print(f"水印图像: {watermark_path}")

    # 测试嵌入
    from algorithm.raster.embed import embed_raster_watermark

    print("\n[DCT域水印嵌入]")
    result = embed_raster_watermark(
        image_path=image_path,
        watermark_path=watermark_path,
        output_folder=test_dir,
        method='dct',
        garden_code='ZZY'
    )

    print(f"水印ID: {result['watermark_id']}")
    print(f"PSNR: {result['psnr']:.2f} dB")
    print(f"输出文件: {result['watermarked_path']}")

    # 测试提取
    from algorithm.raster.extract import extract_raster_watermark

    print("\n[水印提取]")
    extract_result = extract_raster_watermark(
        watermarked_path=result['watermarked_path'],
        original_watermark_path=watermark_path,
        output_folder=test_dir
    )

    print(f"提取成功: {extract_result.get('success', 'N/A')}")
    print(f"NC值: {extract_result.get('nc_value', 0):.4f}")

    # 检查NC值判断提取质量
    nc = extract_result.get('nc_value', 0)
    if nc > 0.7:
        print("✓ 水印提取质量良好")
    elif nc > 0.5:
        print("⚠ 水印提取质量中等")
    else:
        print("✗ 水印提取质量较差")

    return result


def main():
    """主测试函数"""
    print("\n苏州园林数字资产平台 - 水印算法验证")
    print("=" * 60)

    try:
        # 测试栅格水印
        test_raster_watermark()

        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
"""
AI服务演示脚本
演示GLM-4和特征提取功能
"""
import json


def demo_glm4_chat():
    """GLM-4智能问答演示"""
    print("\n" + "=" * 60)
    print("GLM-4-Flash 智能问答演示")
    print("=" * 60)

    from zhipuai import ZhipuAI

    # 初始化客户端
    # client = ZhipuAI(api_key="your_api_key")

    print("\n场景1: 园林知识问答")
    print("-" * 40)

    questions = [
        "拙政园有哪些主要景点?",
        "苏州园林的建筑特色是什么?",
        "如何区分苏州四大名园?"
    ]

    for q in questions:
        print(f"\n问: {q}")
        # 实际调用
        # response = client.chat.completions.create(
        #     model="glm-4-flash",
        #     messages=[{"role": "user", "content": q}]
        # )
        # print(f"答: {response.choices[0].message.content}")

        # 模拟回复
        answers = {
            "拙政园有哪些主要景点?": "拙政园主要景点包括远香堂、荷风四面亭、见山楼、香洲等。远香堂是园内主体建筑，四面环水...",
            "苏州园林的建筑特色是什么?": "苏州园林建筑特色包括:1.移步换景的空间布局 2.粉墙黛瓦的色彩搭配 3.借景造景的艺术手法...",
            "如何区分苏州四大名园?": "拙政园以水景见长，留园以建筑布局著称，狮子林以假山闻名，沧浪亭以山林景色取胜..."
        }
        print(f"答: {answers.get(q, '...')}")

    print("\n场景2: 资产描述生成")
    print("-" * 40)

    print("\n输入: 拙政园远香堂照片")
    print("输出: 远香堂是拙政园的主体建筑，面阔三间，四面临水，是一座典型的江南园林厅堂建筑...")

    print("\n场景3: 溯源报告解读")
    print("-" * 40)

    print("\n输入: NC值=0.95的溯源结果")
    print("输出: 根据NC值分析，该图片与原始资产的相似度为95%，水印信息完整...")


def demo_clip_feature():
    """CLIP特征提取演示"""
    print("\n" + "=" * 60)
    print("CLIP特征提取演示")
    print("=" * 60)

    print("\n1. 图像特征提取")
    print("-" * 40)

    # from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer('clip-ViT-B-32')

    # image_features = model.encode(["./data/sample/garden.jpg"])

    print("输入图像: ./data/sample/garden.jpg")
    print("输出特征向量维度: 512")
    print("特征向量示例: [0.123, -0.456, 0.789, ...]")

    print("\n2. 文本特征提取")
    print("-" * 40)

    texts = ["苏州园林", "古典建筑", "远香堂"]
    print(f"输入文本: {texts}")
    print("输出特征向量维度: 512")

    print("\n3. 图文相似度计算")
    print("-" * 40)

    print("图像: 拙政园远香堂")
    print("文本相似度:")
    print("  '苏州园林': 0.89")
    print("  '古典建筑': 0.76")
    print("  '现代建筑': 0.23")


def demo_vector_search():
    """向量检索演示"""
    print("\n" + "=" * 60)
    print("Milvus向量检索演示")
    print("=" * 60)

    print("\n1. 连接Milvus")
    print("-" * 40)

    # from pymilvus import connections, Collection
    # connections.connect(host='localhost', port=19530)

    print("✓ 已连接 localhost:19530")
    print("集合: garden_assets")
    print("向量维度: 512")

    print("\n2. 插入向量")
    print("-" * 40)

    print("插入资产: ZY-ZZY-IMG-20260426120000-A1B2")
    print("向量: [0.1, 0.2, ..., 0.9]")
    print("✓ 插入成功")

    print("\n3. 相似度搜索")
    print("-" * 40)

    print("查询向量: [0.12, 0.23, ..., 0.91]")
    print("Top 5 结果:")
    print("  1. ZY-ZZY-IMG-20260426120000-A1B2 (相似度: 0.95)")
    print("  2. ZY-ZZY-IMG-20260426113000-C3D4 (相似度: 0.87)")
    print("  3. ZY-LY-IMG-20260426110000-E5F6 (相似度: 0.82)")


def demo_infringement_detection():
    """侵权检测演示"""
    print("\n" + "=" * 60)
    print("侵权检测演示")
    print("=" * 60)

    print("\n场景: 用户上传可疑图片进行溯源")
    print("-" * 40)

    print("\n1. 提取图片水印...")
    print("   水印ID: ZY-ZZY-IMG-20260426120000-A1B2")

    print("\n2. 数据库匹配...")
    print("   匹配资产: 拙政园远香堂全景图")
    print("   原作者: admin")

    print("\n3. 区块链验证...")
    print("   存证状态: ✓ 已存证")
    print("   交易哈希: 0x1234...5678")

    print("\n4. 生成报告...")
    print("   结论: 该图片为系统已登记资产")
    print("   建议: 联系原作者获取授权")


def demo():
    """完整演示"""
    print("=" * 60)
    print("AI智能服务演示")
    print("苏州园林数字资产安全分发与溯源系统")
    print("=" * 60)

    demo_glm4_chat()
    demo_clip_feature()
    demo_vector_search()
    demo_infringement_detection()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == '__main__':
    demo()
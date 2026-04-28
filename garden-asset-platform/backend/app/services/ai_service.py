"""
AI服务模块
图像特征提取、智能分析等功能
"""
import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from PIL import Image

from flask import current_app
from app.extensions import db
from app.models.asset import Asset, AssetFeature


logger = logging.getLogger(__name__)


class AIService:
    """AI服务类"""

    def __init__(self):
        self._clip_model = None
        self._clip_processor = None
        self._device = None
        self._milvus_client = None
        self._glm_client = None
        self.enabled = False

    def init_app(self, app):
        """初始化AI服务"""
        self.enabled = app.config.get('AI_ENABLED', True)

        if self.enabled:
            self._init_clip()
            self._init_milvus()
            self._init_glm(app)

    def _init_clip(self):
        """初始化CLIP模型"""
        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"使用设备: {self._device}")

            self._clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self._clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

            if self._device == "cuda":
                self._clip_model = self._clip_model.to(self._device)

            logger.info("CLIP模型加载成功")

        except ImportError as e:
            logger.warning(f"AI库未安装，部分功能不可用: {e}")
            self.enabled = False
        except Exception as e:
            logger.error(f"CLIP模型加载失败: {e}")
            self.enabled = False

    def _init_milvus(self):
        """初始化Milvus向量数据库"""
        try:
            from pymilvus import MilvusClient

            # 使用Lite版本（嵌入式）
            db_path = current_app.config.get('MILVUS_DB_PATH', './data/milvus.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            self._milvus_client = MilvusClient(db_path)

            # 确保collection存在
            collection_name = "garden_assets"
            if not self._milvus_client.has_collection(collection_name):
                self._milvus_client.create_collection(
                    collection_name=collection_name,
                    dimension=512  # CLIP向量维度
                )

            logger.info("Milvus初始化成功")

        except ImportError:
            logger.warning("pymilvus未安装，向量检索功能不可用")
        except Exception as e:
            logger.error(f"Milvus初始化失败: {e}")

    def _init_glm(self, app):
        """初始化GLM客户端"""
        try:
            api_key = app.config.get('ZHIPU_API_KEY')
            if api_key:
                from zhipuai import ZhipuAI
                self._glm_client = ZhipuAI(api_key=api_key)
                logger.info("GLM客户端初始化成功")
            else:
                logger.warning("未配置ZHIPU_API_KEY，智能对话功能不可用")
        except ImportError:
            logger.warning("zhipuai未安装，智能对话功能不可用")
        except Exception as e:
            logger.error(f"GLM初始化失败: {e}")

    def extract_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        提取图像特征向量

        Args:
            image_path: 图像路径

        Returns:
            特征向量 (512维)
        """
        if not self.enabled or not self._clip_model:
            return None

        try:
            import torch

            # 读取图像
            image = Image.open(image_path).convert('RGB')

            # 预处理
            inputs = self._clip_processor(images=image, return_tensors="pt")

            if self._device == "cuda":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # 提取特征
            with torch.no_grad():
                features = self._clip_model.get_image_features(**inputs)

            # 归一化
            features = features / features.norm(dim=-1, keepdim=True)

            return features.cpu().numpy().flatten()

        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            return None

    def classify_scene(self, image_path: str) -> Dict[str, Any]:
        """
        场景分类

        Args:
            image_path: 图像路径

        Returns:
            分类结果
        """
        if not self.enabled or not self._clip_model:
            return {'success': False, 'message': 'AI服务未启用'}

        try:
            import torch

            # 园林场景类别
            scene_labels = [
                "亭台楼阁", "假山池沼", "花草树木", "水景",
                "园林建筑", "庭院", "走廊", "桥梁", "门楼", "其他"
            ]

            image = Image.open(image_path).convert('RGB')
            inputs = self._clip_processor(
                text=scene_labels,
                images=image,
                return_tensors="pt",
                padding=True
            )

            if self._device == "cuda":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._clip_model(**inputs)

            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

            # 获取Top-3结果
            top_indices = probs.argsort()[-3:][::-1]
            results = []

            for idx in top_indices:
                results.append({
                    'label': scene_labels[idx],
                    'confidence': float(probs[idx])
                })

            return {
                'success': True,
                'scene': results[0]['label'],
                'confidence': results[0]['confidence'],
                'top_results': results
            }

        except Exception as e:
            logger.error(f"场景分类失败: {e}")
            return {'success': False, 'message': str(e)}

    def store_vector(self, asset_id: str, vector: np.ndarray, metadata: dict = None):
        """
        存储向量到Milvus

        Args:
            asset_id: 资产ID
            vector: 特征向量
            metadata: 元数据
        """
        if not self._milvus_client:
            return False

        try:
            self._milvus_client.insert(
                collection_name="garden_assets",
                data=[{
                    "id": asset_id,
                    "vector": vector.tolist(),
                    "metadata": metadata or {}
                }]
            )
            logger.info(f"向量存储成功: {asset_id}")
            return True

        except Exception as e:
            logger.error(f"向量存储失败: {e}")
            return False

    def search_similar(self, image_path: str, top_k: int = 10) -> List[Dict]:
        """
        搜索相似图像

        Args:
            image_path: 查询图像路径
            top_k: 返回数量

        Returns:
            相似结果列表
        """
        if not self._milvus_client:
            return []

        # 提取查询图像特征
        query_vector = self.extract_features(image_path)
        if query_vector is None:
            return []

        try:
            results = self._milvus_client.search(
                collection_name="garden_assets",
                data=[query_vector.tolist()],
                limit=top_k,
                output_fields=["metadata"]
            )

            return results[0] if results else []

        except Exception as e:
            logger.error(f"相似搜索失败: {e}")
            return []

    def check_infringement(self, image_path: str, threshold: float = 0.85) -> Dict[str, Any]:
        """
        侵权检测

        Args:
            image_path: 待检测图像路径
            threshold: 相似度阈值

        Returns:
            检测结果
        """
        similar_results = self.search_similar(image_path, top_k=5)

        infringements = []
        for result in similar_results:
            if result.get('distance', 0) >= threshold:
                infringements.append({
                    'asset_id': result.get('id'),
                    'similarity': result.get('distance'),
                    'metadata': result.get('entity', {}).get('metadata', {})
                })

        return {
            'has_infringement': len(infringements) > 0,
            'matches': infringements,
            'risk_level': 'high' if infringements else 'low'
        }

    def analyze_with_glm(self, prompt: str, context: dict = None) -> str:
        """
        使用GLM进行智能分析

        Args:
            prompt: 提示词
            context: 上下文

        Returns:
            分析结果
        """
        if not self._glm_client:
            return "AI服务未启用"

        try:
            response = self._glm_client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"GLM分析失败: {e}")
            return f"分析失败: {str(e)}"

    def process_asset(self, asset: Asset) -> Dict[str, Any]:
        """
        处理资产：提取特征、分类、存储向量

        Args:
            asset: 资产对象

        Returns:
            处理结果
        """
        if not self.enabled:
            return {'success': False, 'message': 'AI服务未启用'}

        if not asset.storage_path or not os.path.exists(asset.storage_path):
            return {'success': False, 'message': '文件不存在'}

        if asset.asset_type != 'image':
            return {'success': False, 'message': '仅支持图像类型'}

        results = {}

        # 1. 提取特征向量
        vector = self.extract_features(asset.storage_path)
        if vector is not None:
            # 存储到Milvus
            self.store_vector(
                asset_id=asset.id,
                vector=vector,
                metadata={
                    'asset_code': asset.asset_code,
                    'title': asset.title,
                    'garden_id': asset.garden_id
                }
            )
            results['vector_extracted'] = True
            asset.feature_status = 'done'

        # 2. 场景分类
        scene_result = self.classify_scene(asset.storage_path)
        if scene_result.get('success'):
            # 保存场景特征
            feature = AssetFeature(
                asset_id=asset.id,
                feature_type='scene',
                feature_value=scene_result['scene'],
                confidence=scene_result['confidence'],
                source='ai'
            )
            db.session.add(feature)
            results['scene'] = scene_result['scene']

        db.session.commit()

        return {
            'success': True,
            'results': results
        }


# 全局AI服务实例
ai_service = AIService()
"""
园林数据模型
"""
from datetime import datetime
from app.extensions import db


class Garden(db.Model):
    """园林信息表"""
    __tablename__ = 'gardens'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # 园林编码，如'ZY'
    name = db.Column(db.String(100), nullable=False)  # 园林名称
    name_en = db.Column(db.String(100), nullable=True)  # 英文名称

    # 基本信息
    description = db.Column(db.Text, nullable=True)  # 简介
    history = db.Column(db.Text, nullable=True)  # 历史
    location = db.Column(db.String(200), nullable=True)  # 地址
    longitude = db.Column(db.Numeric(10, 7), nullable=True)  # 经度
    latitude = db.Column(db.Numeric(10, 7), nullable=True)  # 纬度
    area_size = db.Column(db.Numeric(10, 2), nullable=True)  # 面积(平方米)
    build_year = db.Column(db.Integer, nullable=True)  # 建造年代

    # 文保信息
    heritage_level = db.Column(db.String(50), nullable=True)  # 文保级别
    heritage_year = db.Column(db.Integer, nullable=True)  # 列入文保年份

    # 媒体资源
    cover_image = db.Column(db.String(500), nullable=True)  # 封面图URL
    intro_video = db.Column(db.String(500), nullable=True)  # 介绍视频URL

    # 统计信息
    asset_count = db.Column(db.Integer, default=0)  # 资产数量
    view_count = db.Column(db.Integer, default=0)  # 浏览次数

    # 状态
    status = db.Column(db.String(20), default='active')  # active/archived

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联资产
    assets = db.relationship('Asset', backref='garden', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'name_en': self.name_en,
            'description': self.description,
            'location': self.location,
            'longitude': float(self.longitude) if self.longitude else None,
            'latitude': float(self.latitude) if self.latitude else None,
            'area_size': float(self.area_size) if self.area_size else None,
            'build_year': self.build_year,
            'heritage_level': self.heritage_level,
            'cover_image': self.cover_image,
            # 静态 asset_count 字段可能过期，返回实时统计的已发布资产数
            'asset_count': self.assets.filter_by(status='published').count(),
            'status': self.status
        }

    def __repr__(self):
        return f'<Garden {self.name}>'
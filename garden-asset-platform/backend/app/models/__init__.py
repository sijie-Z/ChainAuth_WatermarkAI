# backend/app/models/__init__.py
from app.models.user import User, UserToken
from app.models.garden import Garden
from app.models.asset import Asset, AssetTag, AssetFeature
from app.models.license import License, LicenseApplication, LicenseContract
from app.models.blockchain import BlockchainTransaction, Certificate
from app.models.log import OperationLog
from app.models.extra import (
    Favorite, DownloadRecord, AssetShare, NotificationRead,
    Collection, CollectionAsset, SystemConfig
)

__all__ = [
    'User', 'UserToken',
    'Garden',
    'Asset', 'AssetTag', 'AssetFeature',
    'License', 'LicenseApplication', 'LicenseContract',
    'BlockchainTransaction', 'Certificate',
    'OperationLog',
    'Favorite', 'DownloadRecord', 'AssetShare', 'NotificationRead',
    'Collection', 'CollectionAsset', 'SystemConfig'
]

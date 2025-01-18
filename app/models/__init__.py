from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .asset import Asset, AssetType
from .dividend import DividendRecord

import os
import sys
from datetime import datetime

# 将项目根目录添加到 python 路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from app.core.config import settings
from app.db.sqlite import sqlite_db
from app.core.logger import setup_logging
import logging

def init_configs():
    """
    将当前 settings (从 .env 加载) 中的配置项写入 SQLite 数据库
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("开始初始化系统配置到 SQLite 数据库...")
    
    # 获取 settings 中的所有配置项
    # 我们排除一些敏感或不需要在数据库中动态修改的内部字段
    exclude_keys = {'env_file', 'env_file_encoding', 'case_sensitive'}
    
    # 获取 Settings 类中定义的字段
    model_fields = settings.__class__.model_fields
    
    count = 0
    for key, field_info in model_fields.items():
        if key in exclude_keys:
            continue
            
        value = getattr(settings, key)
        
        # 优先从 Pydantic Field 的 description 中获取描述
        description = field_info.description or f"系统配置项: {key}"
        
        # 检查数据库中是否已存在该配置
        existing = sqlite_db.get_config(key)

        if not existing:
            # 写入数据库
            sqlite_db.set_config(key, value, description)
            logger.info(f"已导入配置: {key} = {value}")
            count += 1
        else:
            # 即使存在，我们也更新一下描述，确保描述是最新的
            sqlite_db.set_config(key, existing["value"], description)
            logger.info(f"更新配置描述: {key}")
            count += 1
            
    logger.info(f"初始化完成，共导入 {count} 条配置。")

if __name__ == "__main__":
    init_configs()

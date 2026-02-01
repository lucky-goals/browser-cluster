"""
技能包管理服务模块

提供技能包的增删改查逻辑
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.db.mongo import mongo
from app.models.skill_bundle import SkillBundleModel, SkillBundleCreate, SkillBundleUpdate

logger = logging.getLogger(__name__)

class SkillBundleService:
    """技能包管理服务"""

    async def list_bundles(self) -> List[Dict[str, Any]]:
        """获取技能包列表"""
        bundles = mongo.skill_bundles.find().sort("created_at", -1)
        return list(bundles)

    async def get_bundle(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """获取单个技能包详情"""
        try:
            return mongo.skill_bundles.find_one({"_id": ObjectId(bundle_id)})
        except:
            return None

    async def create_bundle(self, data: SkillBundleCreate) -> str:
        """创建新技能包"""
        bundle_dict = data.model_dump()
        bundle_dict["created_at"] = datetime.now()
        bundle_dict["updated_at"] = datetime.now()
        
        result = mongo.skill_bundles.insert_one(bundle_dict)
        return str(result.inserted_id)

    async def update_bundle(self, bundle_id: str, data: SkillBundleUpdate) -> bool:
        """更新技能包"""
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            return False
            
        update_data["updated_at"] = datetime.now()
        
        try:
            result = mongo.skill_bundles.update_one(
                {"_id": ObjectId(bundle_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except:
            return False

    async def delete_bundle(self, bundle_id: str) -> bool:
        """删除技能包"""
        try:
            result = mongo.skill_bundles.delete_one({"_id": ObjectId(bundle_id)})
            return result.deleted_count > 0
        except:
            return False

# 全局技能包服务实例
skill_bundle_service = SkillBundleService()

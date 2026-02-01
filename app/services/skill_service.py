"""
技能管理服务模块

提供技能的增删改查以及动态执行逻辑
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.db.mongo import mongo
from app.models.skill import SkillModel, SkillCreate, SkillUpdate, SkillType

logger = logging.getLogger(__name__)

class SkillService:
    """技能管理服务"""

    async def list_skills(self, is_enabled: Optional[bool] = None) -> List[Dict[str, Any]]:
        """获取技能列表"""
        query = {}
        if is_enabled is not None:
            query["is_enabled"] = is_enabled
        
        skills = mongo.skills.find(query).sort("created_at", -1)
        return list(skills)

    async def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取单个技能详情"""
        try:
            return mongo.skills.find_one({"_id": ObjectId(skill_id)})
        except:
            return mongo.skills.find_one({"name": skill_id})

    async def create_skill(self, data: SkillCreate) -> str:
        """创建新技能"""
        skill_dict = data.model_dump()
        skill_dict["created_at"] = datetime.now()
        skill_dict["updated_at"] = datetime.now()
        
        result = mongo.skills.insert_one(skill_dict)
        return str(result.inserted_id)

    async def update_skill(self, skill_id: str, data: SkillUpdate) -> bool:
        """更新技能"""
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            return False
            
        update_data["updated_at"] = datetime.now()
        
        result = mongo.skills.update_one(
            {"_id": ObjectId(skill_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_skill(self, skill_id: str) -> bool:
        """删除技能"""
        result = mongo.skills.delete_one({"_id": ObjectId(skill_id)})
        return result.deleted_count > 0

    async def get_skill_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取启用状态的技能"""
        return mongo.skills.find_one({"name": name, "is_enabled": True})

# 全局技能服务实例
skill_service = SkillService()

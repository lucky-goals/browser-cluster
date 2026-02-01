"""
初始化默认技能脚本

向数据库中注入常用的内置技能
"""

import os
import sys
import asyncio
from datetime import datetime

# 添加项目根目录到 python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mongo import mongo
from app.models.skill import SkillType

DEFAULT_SKILLS = [
    {
        "name": "extract_coordinates",
        "display_name": "提取地图坐标",
        "type": SkillType.EXTRACTION,
        "description": "从页面或 iframe 中提取 Google Maps 经纬度坐标",
        "js_code": """
            const results = [];
            const coordRegex = /(ll|query|@)=([-+]?\\d+\\.\\d+),([-+]?\\d+\\.\\d+)/;
            const altRegex = /@([-+]?\\d+\\.\\d+),([-+]?\\d+\\.\\d+)/;

            const findInNode = (root) => {
                const googleMapsRegex = /google\\.[a-z.]+\\/maps/;
                const links = Array.from(root.querySelectorAll('a')).filter(a => googleMapsRegex.test(a.href));
                
                for (const link of links) {
                    const href = link.href;
                    let match = href.match(coordRegex);
                    if (match) {
                        results.push({ lat: match[2], lng: match[3], url: href });
                        continue;
                    }
                    match = href.match(altRegex);
                    if (match) {
                        results.push({ lat: match[1], lng: match[2], url: href });
                    }
                }

                if (root === document) {
                    const metaGeo = document.querySelector('meta[name="geo.position"]');
                    if (metaGeo) {
                        const parts = metaGeo.content.split(';');
                        if (parts.length === 2) results.push({ lat: parts[0], lng: parts[1], source: 'meta' });
                    }
                }

                const allElements = root.querySelectorAll('*');
                for (const el of allElements) {
                    if (el.shadowRoot) findInNode(el.shadowRoot);
                }
            };

            findInNode(document);
            return results.length > 0 ? results[0] : null;
        """,
        "is_builtin": True,
        "is_enabled": True
    },
    {
        "name": "get_page_meta",
        "display_name": "获取页面元数据",
        "type": SkillType.EXTRACTION,
        "description": "提取页面标题、描述和关键词",
        "js_code": """
            return {
                title: document.title,
                description: document.querySelector('meta[name="description"]')?.content || '',
                keywords: document.querySelector('meta[name="keywords"]')?.content || '',
                canonical: document.querySelector('link[rel="canonical"]')?.href || window.location.href
            };
        """,
        "is_builtin": True,
        "is_enabled": True
    }
]

async def init_skills():
    mongo.connect()
    
    for skill_data in DEFAULT_SKILLS:
        existing = mongo.skills.find_one({"name": skill_data["name"]})
        if not existing:
            skill_data["created_at"] = datetime.now()
            skill_data["updated_at"] = datetime.now()
            mongo.skills.insert_one(skill_data)
            print(f"Added skill: {skill_data['name']}")
        else:
            print(f"Skill {skill_data['name']} already exists, skipping.")
            
    mongo.close()

if __name__ == "__main__":
    asyncio.run(init_skills())

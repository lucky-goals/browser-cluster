from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.models.proxy import Proxy, ProxyCreate, ProxyUpdate, ProxyFilter, ProxyStats, ProxyConfig, ProxyListResponse
from app.services.proxy_service import proxy_service
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/v1/proxy", tags=["Proxy Pool"])

@router.post("/", response_model=Proxy)
async def create_proxy(proxy: ProxyCreate, current_user=Depends(get_current_user)):
    """添加代理 IP"""
    return await proxy_service.add_proxy(proxy)

@router.get("/", response_model=ProxyListResponse)
async def list_proxies(
    group: Optional[str] = None,
    status: Optional[str] = None,
    protocol: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_user)
):
    """获取代理列表"""
    filter_data = ProxyFilter(group=group, status=status, protocol=protocol)
    return await proxy_service.list_proxies(filter_data, skip=skip, limit=limit)

@router.get("/random", response_model=Proxy)
async def get_random_proxy(group: str = "default"):
    """随机获取一个可用代理"""
    proxy = await proxy_service.get_random_proxy(group)
    if not proxy:
        raise HTTPException(status_code=404, detail="No available proxy found")
    return proxy

@router.get("/stats", response_model=ProxyStats)
async def get_proxy_stats(current_user=Depends(get_current_user)):
    """获取代理池统计信息"""
    stats = await proxy_service.get_stats()
    return ProxyStats(**stats)

@router.get("/config", response_model=ProxyConfig)
async def get_proxy_config(current_user=Depends(get_current_user)):
    """获取代理检测配置"""
    return await proxy_service.get_config()

@router.put("/config")
async def update_proxy_config(config: ProxyConfig, current_user=Depends(get_current_user)):
    """更新代理检测配置"""
    success = await proxy_service.update_config(config)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update proxy configuration")
    return {"message": "Proxy configuration updated successfully"}

@router.get("/export-all", response_model=List[ProxyCreate])
async def export_proxies(current_user=Depends(get_current_user)):
    """导出所有代理"""
    return await proxy_service.bulk_export()

@router.get("/{proxy_id}", response_model=Proxy)
async def get_proxy(proxy_id: str, current_user=Depends(get_current_user)):
    """获取代理详情"""
    proxy = await proxy_service.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return proxy

@router.put("/{proxy_id}", response_model=Proxy)
async def update_proxy(proxy_id: str, update: ProxyUpdate, current_user=Depends(get_current_user)):
    """更新代理信息"""
    proxy = await proxy_service.update_proxy(proxy_id, update)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return proxy

@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: str, current_user=Depends(get_current_user)):
    """删除代理"""
    success = await proxy_service.delete_proxy(proxy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {"message": "Proxy deleted successfully"}

@router.post("/batch-delete")
async def batch_delete_proxies(proxy_ids: List[str], current_user=Depends(get_current_user)):
    """批量删除代理"""
    count = await proxy_service.bulk_delete_proxies(proxy_ids)
    return {"message": f"Successfully deleted {count} proxies"}

@router.post("/import")
async def import_proxies(proxies: List[ProxyCreate], current_user=Depends(get_current_user)):
    """批量导入代理"""
    count = await proxy_service.bulk_import(proxies)
    return {"message": f"Successfully imported {count} proxies"}

@router.post("/check-all")
async def check_all_proxies(current_user=Depends(get_current_user)):
    """检测所有代理"""
    await proxy_service.check_all_proxies()
    return {"message": "Started checking all proxies"}

@router.post("/{proxy_id}/check")
async def check_single_proxy(proxy_id: str, current_user=Depends(get_current_user)):
    """检测单个代理"""
    proxy = await proxy_service.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    is_active = await proxy_service.check_proxy(proxy)
    return {"active": is_active, "status": proxy.status}

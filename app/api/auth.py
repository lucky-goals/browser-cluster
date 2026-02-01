from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.core.auth import verify_password, create_access_token, get_current_user
from app.db.sqlite import sqlite_db
from app.core.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录接口"""
    user = sqlite_db.get_user_by_username(form_data.username)

    print(f"user: {user}")
    print(f"form: {form_data.username};{form_data.password}")
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "language": user.get("language", "zh-CN")
        }
    }

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "language": current_user.get("language", "zh-CN")
    }

@router.put("/me")
async def update_users_me(
    user_in: dict, 
    current_user: dict = Depends(get_current_user)
):
    """更新当前用户信息 (主要用于更新语言)"""
    language = user_in.get("language")
    if not language:
        raise HTTPException(status_code=400, detail="Language is required")
    
    sqlite_db.update_user(
        user_id=current_user["id"],
        language=language
    )
    
    updated_user = sqlite_db.get_user_by_id(current_user["id"])
    return {
        "id": updated_user["id"],
        "username": updated_user["username"],
        "role": updated_user["role"],
        "language": updated_user.get("language", "zh-CN")
    }

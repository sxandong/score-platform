"""系统管理: 数据库备份与恢复"""
import os
import shutil
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.core.security import require_role
from app.core.response import success_response
from app.config import settings
from app.core.database import engine

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/backup")
async def download_backup():
    """下载数据库备份"""
    db_path = os.path.abspath(settings.DB_NAME + ".db" if settings.DATABASE_IS_SQLITE else settings.DB_NAME)
    if not settings.DATABASE_IS_SQLITE:
        # For MySQL, we should use mysqldump but for simplicity return a message
        return success_response(message="MySQL backup requires server-side tools")
    if not os.path.exists(db_path):
        return success_response(message="Database file not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create a copy in memory
    with open(db_path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=backup_{timestamp}.db"},
    )


@router.post("/restore")
async def upload_restore(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """上传备份文件恢复数据库"""
    if not settings.DATABASE_IS_SQLITE:
        return success_response(message="Restore not supported for MySQL via web")

    content = await file.read()
    if len(content) < 1024:
        return success_response(message="Invalid backup file (too small)")

    db_path = os.path.abspath(settings.DB_NAME + ".db")
    backup_path = db_path + ".before_restore"
    try:
        # Keep a safety backup
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        # Write new database
        with open(db_path, "wb") as f:
            f.write(content)
        # Recycle engine
        await engine.dispose()
        return success_response(message="数据库恢复成功，请重启应用")
    except Exception as e:
        # Restore from safety backup
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
        return success_response(message=f"恢复失败: {e}")

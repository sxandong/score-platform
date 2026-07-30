"""系统管理: 数据库备份与恢复"""
import os
import shutil
import asyncio
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.core.security import require_role
from app.core.response import success_response
from app.config import settings
from app.core.database import engine

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/backup")
async def download_backup(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """下载数据库备份"""
    # 从 DATABASE_URL 提取实际文件名, e.g. sqlite+aiosqlite:///admission_data.db
    db_name = settings.DATABASE_URL.split("///")[-1] if "///" in settings.DATABASE_URL else "admission_data.db"
    db_path = os.path.abspath(db_name)
    if not settings.DATABASE_IS_SQLITE:
        # For MySQL, we should use mysqldump but for simplicity return a message
        return success_response(message="MySQL backup requires server-side tools")
    if not os.path.exists(db_path):
        return success_response(message="Database file not found")

    # 在 WAL 模式下，先执行 checkpoint 将 WAL 数据写回主文件
    await db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
    await db.commit()

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
    current_user=Depends(require_role("admin")),
):
    """上传备份文件恢复数据库"""
    import logging
    import sqlite3
    import tempfile
    logger = logging.getLogger(__name__)
    _ = asyncio  # 确保 asyncio 已导入

    if not settings.DATABASE_IS_SQLITE:
        return success_response(message="Restore not supported for MySQL via web")

    content = await file.read()

    # 校验是否为有效的 SQLite 数据库文件（16字节的文件头）
    if len(content) < 100 or content[:16] != b"SQLite format 3\x00":
        return success_response(message="备份文件无效，不是正确的数据库文件")

    db_name = settings.DATABASE_URL.split("///")[-1] if "///" in settings.DATABASE_URL else "admission_data.db"
    db_path = os.path.abspath(db_name)

    # 将上传的内容保存到临时文件
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db')
    try:
        with os.fdopen(tmp_fd, 'wb') as f:
            f.write(content)

        # 使用 SQLite 的 .backup 命令进行恢复
        # 这是 SQLite 官方推荐的方式，可以在数据库仍在使用时进行
        def _do_restore():
            # 打开目标数据库
            dst = sqlite3.connect(db_path)
            try:
                # 打开源数据库（上传的备份）
                src = sqlite3.connect(tmp_path)
                try:
                    # 使用 SQLite 的备份 API
                    with dst:
                        src.backup(dst, pages=0, progress=None)
                finally:
                    src.close()
            finally:
                dst.close()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_restore)

        return success_response(message="数据库恢复成功")
    except Exception as e:
        logger.exception("数据恢复失败: %s", str(e))
        return success_response(message=f"数据恢复失败：{str(e)[:100]}")
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/init")
async def system_init(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """系统初始化 - 清空业务数据并重置为初始状态"""
    import logging
    import sqlite3
    logger = logging.getLogger(__name__)

    try:
        # 先创建一个备份
        db_name = settings.DATABASE_URL.split("///")[-1] if "///" in settings.DATABASE_URL else "admission_data.db"
        db_path = os.path.abspath(db_name)
        backup_dir = os.path.join(os.path.dirname(db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"pre_init_{timestamp}.db")
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)

        # 按顺序清空业务数据表（使用原生 SQLite 连接避免 SQLAlchemy 会话问题）
        tables_to_clear = [
            "score_details",    # 成绩明细
            "scores",           # 成绩
            "score_cutoffs",    # 分数线
            "rank_snapshots",   # 排名快照
            "exam_subjects",    # 考试科目
            "exams",            # 考试
            "audit_logs",       # 审计日志
            "students",         # 学生
            "classes",          # 班级
        ]

        def _clear_tables():
            """在独立线程中清空表"""
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                # 关闭外键检查
                cursor.execute("PRAGMA foreign_keys=OFF")
                
                for table in tables_to_clear:
                    try:
                        cursor.execute(f"DELETE FROM {table}")
                    except Exception:
                        pass
                
                # 重新开启外键检查
                cursor.execute("PRAGMA foreign_keys=ON")
                conn.commit()
            finally:
                conn.close()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _clear_tables)

        return success_response(message="系统初始化成功")
    except Exception as e:
        logger.exception("系统初始化失败: %s", str(e))
        return success_response(message=f"系统初始化失败：{str(e)[:100]}")

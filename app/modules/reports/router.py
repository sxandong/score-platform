"""Reports 模块路由"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import get_current_user, require_role
from app.modules.reports import service

router = APIRouter(prefix="/api/reports", tags=["报表导出"])


@router.get("/score-sheet")
async def export_score_sheet(
    exam_id: int,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    output = await service.export_score_sheet(db, exam_id, class_id)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=成绩单_{exam_id}_{class_id}.xlsx"
        },
    )

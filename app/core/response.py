"""统一 API 响应工具"""
from typing import Any
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "success", meta: dict | None = None) -> JSONResponse:
    body: dict = {"code": 200, "message": message}
    if data is not None:
        body["data"] = data
    if meta:
        body["meta"] = meta
    return JSONResponse(content=body)


def error_response(code: int, message: str, data: Any = None) -> JSONResponse:
    body: dict = {"code": code, "message": message}
    if data:
        body["data"] = data
    return JSONResponse(content=body)


def paginated_response(items: list, total: int, page: int, per_page: int) -> JSONResponse:
    return JSONResponse(content={
        "code": 200,
        "message": "success",
        "data": items,
        "meta": {"page": page, "per_page": per_page, "total": total},
    })

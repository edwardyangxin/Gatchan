from typing import Any, Optional

from fastapi.responses import JSONResponse


def success_response(data: Optional[Any] = None, meta: Optional[dict] = None) -> JSONResponse:
    payload: dict[str, Any] = {"success": True, "data": data, "error": None}
    if meta is not None:
        payload["meta"] = meta
    return JSONResponse(payload)


def error_response(message: str, status_code: int = 400, meta: Optional[dict] = None) -> JSONResponse:
    payload: dict[str, Any] = {"success": False, "data": None, "error": message}
    if meta is not None:
        payload["meta"] = meta
    return JSONResponse(payload, status_code=status_code)

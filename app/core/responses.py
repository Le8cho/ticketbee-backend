from typing import Any
from fastapi.responses import JSONResponse

def success(data: Any, message: str = "OK", status_code: int = 200):
    return JSONResponse(status_code=status_code, content={"ok": True, "message": message, "data": data})

def error(message: str, status_code: int = 400):
    return JSONResponse(status_code=status_code, content={"ok": False, "message": message, "data": None})
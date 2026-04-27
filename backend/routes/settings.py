import json
import logging
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import dotenv_values
from pathlib import Path

from main import templates, require_auth, llm_manager
from utils import success_response, error_response

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

ENV_PATH = Path("/.env")
PROVIDERS_PATH = Path("/setup/llm-providers.json")

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": dotenv_values(ENV_PATH),
        "keys": [key for key in dotenv_values(ENV_PATH)],
        "llm_providers": [{"name": provider} for provider in (json.loads(PROVIDERS_PATH.read_text())).get("main")],
        "emb_providers": [{"name": provider} for provider in (json.loads(PROVIDERS_PATH.read_text())).get("embedding")]
    })

@router.post("/api/config")
async def update_config(request: Request, key: str = Form(...), value: str = Form(...)):
    updated = [f"{key}={value}" if line.startswith(key + "=") else line for line in (ENV_PATH.read_text().splitlines())]
    ENV_PATH.write_text("\n".join(updated) + "\n")

    if key in {"LLM_PROVIDER", "EMBEDDING_PROVIDER"}:
        result = llm_manager.apply_from_env(dotenv_values(ENV_PATH))
        if not result["success"]: return error_response(f'Ошибка генерации: {result.get("error")}', 500)

    if request.headers.get("HX-Request"):
        return success_response("✅ Сохранено и пересобрано", triggers={"show-restart-banner": True})
    return {"success": True}

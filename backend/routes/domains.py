import logging
import httpx
import json
import re
from fastapi import APIRouter, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse

from main import templates, require_auth, get_db_connection, BASE_URL
from utils import success_response, error_response

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

async def update_examples_data(examples_json: str) -> list[str]:
    examples = json.loads(examples_json) if examples_json else []
    if not isinstance(examples, list):
        return []
    processed = []
    for example in examples:
        if isinstance(example, str):
            text = example.strip()
            priority = ""
        elif isinstance(example, dict):
            text = example.get("text", "").strip()
            priority = example.get("priority", "").strip()
        else:
            continue

        if not text:
            continue

        if priority:
            formatted = f"{text} [PRIORITY:{priority}]"
        else:
            formatted = text
        processed.append(formatted)

    return processed

@router.get("/domains", dependencies=[Depends(require_auth)], response_class=HTMLResponse)
async def domains_page(request: Request):
    return templates.TemplateResponse("domains.html", {"request": request})

@router.get("/api/domains/list", dependencies=[Depends(require_auth)], response_class=HTMLResponse)
async def get_domains_list(request: Request):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables "
                           "WHERE table_schema='public' AND table_name LIKE '%_priorities' "
                           "ORDER BY table_name")
            domains = [r[0].replace('_priorities', '') for r in cursor.fetchall() if r[0].replace('_priorities', '').strip()]
    return templates.TemplateResponse("domains_list.html", {"request": request, "domains": domains})

@router.post("/api/domains", dependencies=[Depends(require_auth)])
async def create_domain(
    redmine_identifier: str = Form(...),
    prompt_source: str = Form("ai"),
    examples_source: str = Form("ai"),
    prompt_file: UploadFile = File(None),
    examples_file: UploadFile = File(None),
    ai_prompt_examples: str = Form(""),
    ai_examples_base: str = Form("")
):
    clean_id = re.sub(r'[^a-z0-9_-]', '', redmine_identifier.strip().lower())
    if not clean_id: return HTMLResponse('<span class="text-red-600">Неверный формат.</span>', 400)

    data = {
        "domain_name": clean_id, "redmine_identifier": clean_id,
        "prompt_source": prompt_source, "examples_source": examples_source,
        "ai_prompt_examples": ai_prompt_examples, "ai_examples_base": ai_examples_base
    }
    files = {}
    if prompt_file and prompt_file.filename:
        files["prompt_file"] = (prompt_file.filename, await prompt_file.read(), "text/plain")
    if examples_file and examples_file.filename:
        files["examples_file"] = (examples_file.filename, await examples_file.read(), "application/json")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            await client.post(f"{BASE_URL}/webhook/add-domain", data=data, files=files or None)
        return success_response(f'Сфера "{clean_id}" создана', triggers={"refresh-domain-list": True})
    except Exception as thrown:
        logger.error(f"Ошибка создания сферы: {thrown}")
        return error_response(thrown)

@router.get("/api/domains/{name}/config", dependencies=[Depends(require_auth)])
async def get_domain_config(name: str):
    name = name.strip().lower().replace("/", "").replace("'", "")
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT main_prompt FROM domain_configs "
                           "WHERE LOWER(domain_name)=%s", (name,))
            prompt = cursor.fetchone()[0] if cursor.rowcount else ""
            cursor.execute(f'SELECT "text" FROM {name}_priorities ORDER BY id')
            examples = [str(row[0]).strip() for row in cursor.fetchall() if row[0]]
    return {"success": True, "prompt": prompt, "examples": examples}

@router.delete("/api/domains/{name}", dependencies=[Depends(require_auth)])
async def delete_domain(name: str):
    name = name.strip().lower().replace(" ", "_")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.delete(f"{BASE_URL}/webhook/delete-domain-webhook/{name}")
        return success_response('Сфера удалена', triggers={"refresh-domain-list": True})
    except Exception as thrown:
        logger.error(f"Ошибка удаления сферы: {thrown}")
        return error_response(str(thrown))


@router.put("/api/domains/{name}", dependencies=[Depends(require_auth)])
async def update_domain(
    name: str,
    request: Request,
    update_type: str = Form("prompt"),
    prompt_content: str = Form(""),
    examples_json: str = Form("")
):
    domain_name = name.strip().lower().replace("/", "").replace("'", "")
    data = {
        "domain_name": domain_name,
        "update_type": update_type
    }

    if update_type == "prompt":
        data["prompt_content"] = prompt_content
    elif update_type == "examples":
        data["examples"] = await update_examples_data(examples_json)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{BASE_URL}/webhook/update-domain", json=data)
            resp.raise_for_status()

        return success_response(
            "Сфера обновлена",
            triggers={"refresh-domain-list": True, "close-edit-modal": True}
        )
    except Exception as thrown:
        logger.error(f"Ошибка при обновлении сферы: {thrown}")
        return error_response(f"Ошибка: {thrown}")
import os
import json
import re
import httpx
import logging
import psycopg2
from pathlib import Path
from dotenv import dotenv_values
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from services.llm_manager import LLMWebManager

logger = logging.getLogger("uvicorn.error")
app = FastAPI(title="Priority Desk")

# Конфигурация
BASE_URL = os.getenv("BASE_URL", "http://localhost:5678").rstrip("/")
logger.info(f"✅ BASE_URL инициализирован: {BASE_URL}")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-me"),
    session_cookie="priority_session",
    max_age=3600, same_site="lax", https_only=False
)

templates = Jinja2Templates(directory="/app/templates")
ENV_PATH = Path("/.env")
USERS = {"admin": {"password": "admin123", "role": "admin"}}

PROJECT_ROOT = Path("/app").parent
llm_manager = LLMWebManager(PROJECT_ROOT)


async def require_auth(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return request.session["user"]


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == USERS["admin"]["password"]:
        request.session["user"] = "admin"
        return RedirectResponse("/domains", status_code=303)
    return RedirectResponse("/login?error=1", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

@app.get("/", dependencies=[Depends(require_auth)])
async def root_redirect():
    return RedirectResponse("/domains", status_code=303)


@app.get("/domains", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def domains_page(request: Request):
    return templates.TemplateResponse("domains.html", {"request": request})


@app.get("/logs", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def settings_page(request: Request):
    config = dotenv_values(ENV_PATH)
    visible_keys = [k for k in config.keys() if not k.startswith("_")]

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "config": config,
            "keys": visible_keys,
            "llm_providers": llm_manager.get_llm_providers_list(),
            "emb_providers": llm_manager.get_embedding_providers_list()
        }
    )


# Сферы
@app.get("/api/domains/list", dependencies=[Depends(require_auth)])
async def get_domains_list():
    db_url = os.getenv("DATABASE_URL",
                       f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_DB')}")
    conn = psycopg2.connect(dsn=db_url)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%_priorities' ORDER BY table_name")
        domains = [row[0].replace('_priorities', '') for row in cur.fetchall() if
                   row[0].replace('_priorities', '').strip()]

        if not domains:
            return HTMLResponse(
                '<div class="p-6 text-center text-slate-400 bg-white rounded-lg border border-slate-200">Нет активных сфер</div>')

        html = '<div class="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-100">'
        for d in domains:
            # Экранируем кавычки, чтобы не сломать onclick="openEditModal('...')"
            safe_d = d.replace("'", "\\'").replace('"', '\\"')
            html += f'''
            <div class="p-4 flex justify-between items-center hover:bg-slate-50 transition group">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-sm">{d[:3].upper()}</div>
                    <div>
                        <p class="font-medium text-slate-800">{d}</p>
                        <p class="text-xs text-slate-400">Таблица: {d}_priorities</p>
                    </div>
                </div>
                <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                    <button onclick="openEditModal('{safe_d}')" class="text-slate-400 hover:text-blue-500 hover:bg-blue-50 p-2 rounded transition" title="Редактировать">
                        <i class="ph ph-pencil-simple text-xl"></i>
                    </button>
                    <button hx-delete="/api/domains/{d}"
                            hx-swap="outerHTML"
                            hx-confirm="Удалить сферу '{d}' и все векторные данные?"
                            class="text-slate-400 hover:text-red-500 hover:bg-red-50 p-2 rounded transition" title="Удалить">
                        <i class="ph ph-trash text-xl"></i>
                    </button>
                </div>
            </div>'''
        html += '</div>'
        return HTMLResponse(html)
    finally:
        conn.close()

@app.post("/api/domains", dependencies=[Depends(require_auth)])
async def create_domain(
        domain_name: str = Form(...),
        prompt_source: str = Form("ai"),
        examples_source: str = Form("ai"),
        prompt_file: UploadFile = File(None),
        examples_file: UploadFile = File(None),
        ai_prompt_examples: str = Form(""),
        ai_examples_base: str = Form("")
):
    domain_name = domain_name.strip().lower().replace(" ", "_")

    data = {
        "domain_name": domain_name,
        "prompt_source": prompt_source,
        "examples_source": examples_source,
        "ai_prompt_examples": ai_prompt_examples,
        "ai_examples_base": ai_examples_base
    }

    files = {}
    if prompt_file and prompt_file.filename and prompt_source == "file":
        content = await prompt_file.read()
        files["prompt_file"] = (prompt_file.filename, content, "text/plain")

    if examples_file and examples_file.filename and examples_source == "file":
        content = await examples_file.read()
        files["examples_file"] = (examples_file.filename, content, "application/json")

    try:
        webhook_url = f"{BASE_URL}/webhook/add-domain"
        logger.info(f"Отправка вебхука на: {webhook_url}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(webhook_url, data=data, files=files if files else None)
            response.raise_for_status()

        return HTMLResponse(
            content=f'<span class="text-emerald-600 font-medium">✅ Сфера "{domain_name}" создана</span>',
            headers={"HX-Trigger": '{"refresh-domain-list": true}'}
        )
    except httpx.HTTPError as e:
        logger.error(f"Ошибка вебхука n8n: {e}")
        return HTMLResponse(content=f'<span class="text-red-600">❌ Ошибка вебхука: {str(e)}</span>', status_code=500)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return HTMLResponse(content=f'<span class="text-red-600">❌ Внутренняя ошибка: {str(e)}</span>', status_code=500)


@app.get("/api/domains/{name}/config", dependencies=[Depends(require_auth)])
async def get_domain_config(name: str):
    clean_name = name.strip().lower().replace("/", "").replace("'", "")
    db_url = os.getenv("DATABASE_URL",
                       f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_DB')}")
    conn = psycopg2.connect(dsn=db_url)
    try:
        cur = conn.cursor()

        cur.execute("SELECT main_prompt FROM domain_configs WHERE LOWER(domain_name) = %s", (clean_name,))
        prompt_row = cur.fetchone()
        prompt = prompt_row[0] if prompt_row else ""

        cur.execute(f'SELECT "text" FROM {clean_name}_priorities ORDER BY id')
        rows = cur.fetchall()

        examples = []
        # "Текст - 5", "Текст. Приоритет: 5", "Текст - 5 (...)"
        pattern = re.compile(r'^(.+?)(?:\s*[-–—]\s*|\s*[.,;]?\s*[Пп]риоритет:\s*)(\d+)(?:\s*\(.*\))?$')

        for row in rows:
            if not row[0]: continue
            text = str(row[0]).strip()
            match = pattern.match(text)

            if match:
                examples.append({"text": match.group(1).strip(), "priority": match.group(2)})
            else:
                examples.append({"text": text, "priority": ""})

        return {"success": True, "prompt": prompt, "examples": examples}
    except Exception as e:
        logger.error(f"❌ Ошибка получения конфига: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@app.get("/api/domains/{name}/download", dependencies=[Depends(require_auth)])
async def download_config(name: str, type: str = "prompt"):
    db_url = os.getenv("DATABASE_URL", f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_DB')}")
    conn = psycopg2.connect(dsn=db_url)
    try:
        cur = conn.cursor()
        if type == "prompt":
            cur.execute("SELECT main_prompt FROM domain_configs WHERE domain_name = %s", (name,))
            row = cur.fetchone()
            data = row[0] if row else ""
            return StreamingResponse(iter([data.encode("utf-8")]), media_type="text/plain",
                                     headers={"Content-Disposition": f'attachment; filename="{name}_prompt.txt"'})
        else:
            cur.execute(f'SELECT "text" FROM {name}_priorities ORDER BY id')
            examples = [row[0] for row in cur.fetchall()]
            json_str = json.dumps(examples, ensure_ascii=False, indent=2)
            return StreamingResponse(iter([json_str.encode("utf-8")]), media_type="application/json",
                                     headers={"Content-Disposition": f'attachment; filename="{name}_examples.json"'})
    finally:
        conn.close()

@app.put("/api/domains/{name}", dependencies=[Depends(require_auth)])
async def update_domain(
        name: str,
        update_type: str = Form("prompt"),
        prompt_content: str = Form(""),
        prompt_source: str = Form("manual"),
        prompt_file: UploadFile = File(None),
        examples_json: str = Form(""),
        examples_source: str = Form("manual"),
        examples_file: UploadFile = File(None)
):
    domain_name = name.strip().lower().replace("/", "")

    data = {
        "domain_name": domain_name,
        "update_type": update_type,
        "prompt_source": prompt_source,
        "examples_source": examples_source
    }

    if update_type == "prompt":
        data["prompt_content"] = prompt_content

    elif update_type == "examples":
        try:
            raw_examples = json.loads(examples_json) if examples_json else []
            data["examples"] = []

            for ex in raw_examples:
                if isinstance(ex, dict):
                    text = ex.get('text', '').strip()
                    priority = ex.get('priority', '').strip()
                    if text:
                        if priority:
                            data["examples"].append(f"{text}. Приоритет: {priority}.")
                        else:
                            data["examples"].append(text)
                elif isinstance(ex, str):
                    data["examples"].append(ex.strip())

        except json.JSONDecodeError:
            data["examples"] = []

    try:
        webhook_url = f"{BASE_URL}/webhook/update-domain"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(webhook_url, json=data)
            response.raise_for_status()

        return HTMLResponse(
            content=f'<span class="text-emerald-600 font-medium">✅ Сфера "{domain_name}" обновлена</span>',
            headers={"HX-Trigger": '{"refresh-domain-list": true, "close-edit-modal": true}'}
        )
    except httpx.HTTPError as e:
        return HTMLResponse(content=f'<span class="text-red-600">❌ Ошибка n8n: {str(e)}</span>', status_code=500)
    except Exception as e:
        return HTMLResponse(content=f'<span class="text-red-600">❌ Ошибка: {str(e)}</span>', status_code=500)


@app.delete("/api/domains/{name}", dependencies=[Depends(require_auth)])
async def delete_domain(name: str):
    domain_name = name.strip().lower().replace(" ", "_")

    try:
        webhook_url = f"{BASE_URL}/webhook/delete-domain-webhook/{domain_name}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(webhook_url)
            response.raise_for_status()
        return HTMLResponse('<span class="text-emerald-600">✅ Сфера удалена</span>',
                            headers={"HX-Trigger": '{"refresh-domain-list": true}'})
    except httpx.HTTPError as e:
        return HTMLResponse(f'<span class="text-red-600">❌ Ошибка удаления: {str(e)}</span>', status_code=500)

@app.post("/api/config", dependencies=[Depends(require_auth)])
async def update_config(request: Request, key: str = Form(...), value: str = Form(...)):
    try:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        new_lines = []
        updated = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(key + "=") and not stripped.startswith("#"):
                new_lines.append(f"{key}={value}")
                updated = True
            else:
                new_lines.append(line)
        if not updated: new_lines.append(f"{key}={value}")
        ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        if request.headers.get("HX-Request") == "true":
            return HTMLResponse(content='<span class="text-emerald-600 font-medium">✅ Сохранено</span>',
                                headers={"HX-Trigger": '{"show-restart-banner": true}'})
        return {"success": True}
    except Exception as e:
        if request.headers.get("HX-Request") == "true":
            return HTMLResponse(content=f'❌ {str(e)}', status_code=500)
        raise HTTPException(status_code=500, detail=str(e))
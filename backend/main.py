import os
import logging
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import dotenv_values
from contextlib import contextmanager
import psycopg2
from pathlib import Path
from services.llm_manager import LLMWebManager

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="servicedesk_priority")

BASE_URL = os.getenv("BASE_URL", "http://localhost:5678").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "1234")
PROJECT_ROOT = Path("/app")

# Шаблоны (для HTML страниц)
templates = Jinja2Templates(directory="/app/templates")

# Middleware (Сессии)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="priority_session",
    max_age=3600, same_site="lax", https_only=False
)

llm_manager = LLMWebManager(Path("/"))

def get_db_url() -> str:
    return f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_DB')}"

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(dsn=get_db_url())
        yield conn
    except psycopg2.Error as thrown:
        if conn: conn.rollback()
        logger.error(f"Ошибка базы данных: {thrown}")
        raise
    finally:
        if conn: conn.close()

def get_redmine_db_url() -> str:
    return f"postgresql://{os.getenv('REDMINE_DB_USER')}:{os.getenv('REDMINE_DB_PASSWORD')}@{os.getenv('REDMINE_DB_HOST', 'postgres')}:{os.getenv('REDMINE_DB_PORT', '5432')}/{os.getenv('REDMINE_DB_NAME')}"

@contextmanager
def get_redmine_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(dsn=get_redmine_db_url())
        yield conn
    except psycopg2.Error as thrown:
        if conn: conn.rollback()
        logger.error(f"Ошибка базы данных Redmine: {thrown}")
        raise
    finally:
        if conn: conn.close()

def require_auth(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return request.session["user"]

from routes import auth, domains, settings

app.include_router(auth.router)
app.include_router(domains.router)
app.include_router(settings.router)
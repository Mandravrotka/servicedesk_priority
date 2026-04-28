import logging
import bcrypt
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from main import templates, get_db_connection

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.get("/login")
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM users "
                           "WHERE username = %s", (username,))

            row = cursor.fetchone()
            if row:
                if bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
                    request.session["user"] = username
                    logger.info(f"Успешный вход: {username}")
                    return RedirectResponse("/domains", status_code=303)

            logger.warning(f"Неверный пароль или пользователь: {username}")
            return RedirectResponse("/login?error=1", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
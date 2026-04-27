from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from main import templates

router = APIRouter()
USERS = {"admin": {"password": "admin123", "role": "admin"}}

@router.get("/login")
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == USERS["admin"]["password"]:
        request.session["user"] = "admin"
        return RedirectResponse("/domains", status_code=303)
    return RedirectResponse("/login?error=1", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import database as db
import config
from datetime import datetime
import os

app = FastAPI(title="MobKom Robot Panel")

# Шаблоны
templates_dir = os.path.join(os.path.dirname(__file__), "web", "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

# Простая авторизация
ADMIN_PASSWORD = "mobkom2024"


def check_auth(request: Request):
    auth = request.cookies.get("auth")
    return auth == ADMIN_PASSWORD


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not check_auth(request):
        return templates.TemplateResponse("login.html", {"request": request})
    return RedirectResponse(url="/dashboard")


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("auth", ADMIN_PASSWORD, max_age=86400)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный пароль"})


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("auth")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/")

    users = db.get_all_users()
    phones = db.get_phones()
    logs = db.get_logs(10)

    stats = {
        "total_users": len(users),
        "admin_count": len([u for u in users if u["role"] == "admin"]),
        "mod_count": len([u for u in users if u["role"] == "moderator"]),
        "trader_count": len([u for u in users if u["role"] == "trader"]),
        "phones_total": len(phones),
        "phones_online": len([p for p in phones if p["status"] == "online"]),
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "users": users[:20],
        "logs": logs[:10]
    })


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/")

    users = db.get_all_users()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users
    })


@app.post("/users/{user_id}/role")
async def change_role(request: Request, user_id: int, role: str = Form(...)):
    if not check_auth(request):
        return RedirectResponse(url="/")

    db.set_role(user_id, role)
    db.log(None, "web_role_change", f"{user_id} -> {role}")
    return RedirectResponse(url="/users", status_code=302)


@app.get("/phones", response_class=HTMLResponse)
async def phones_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/")

    phones = db.get_phones()
    return templates.TemplateResponse("phones.html", {
        "request": request,
        "phones": phones
    })


@app.get("/purchases", response_class=HTMLResponse)
async def purchases_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/")

    users = db.get_all_users(role="trader")
    all_purchases = []
    for u in users:
        purchases = db.get_purchases(u["user_id"])
        for p in purchases:
            p["username"] = u.get("username", "")
            all_purchases.append(p)

    return templates.TemplateResponse("purchases.html", {
        "request": request,
        "purchases": all_purchases
    })


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/")

    logs = db.get_logs(100)
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "logs": logs
    })


@app.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/")

    conn = db.get_db()
    rows = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    signals = [dict(r) for r in rows]

    return templates.TemplateResponse("signals.html", {
        "request": request,
        "signals": signals
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

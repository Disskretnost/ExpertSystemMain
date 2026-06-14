from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from auth import verify_token

router = APIRouter()


def is_authenticated(request: Request):
    token = request.cookies.get("token")
    if not token:
        return False
    user_data = verify_token(token)
    return user_data is not None
@router.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()
@router.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    with open("static/login.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    with open("static/register.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/profile.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/plan", response_class=HTMLResponse)
async def get_plan(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/plan.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/fitness-test", response_class=HTMLResponse)
async def get_fitness_test(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/fitness_test.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/nutrition", response_class=HTMLResponse)
async def get_nutrition(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/nutrition.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/nutrition-advice", response_class=HTMLResponse)  # ДОБАВИТЬ ЭТОТ МАРШРУТ
async def get_nutrition_advice(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/nutrition_advice.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/nutrition-advice", response_class=HTMLResponse)
async def get_nutrition_advice(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/nutrition_advice.html", "r", encoding="utf-8") as f:
        return f.read()

@router.get("/exercise-advice", response_class=HTMLResponse)
async def get_exercise_advice(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    with open("static/exercise_advice.html", "r", encoding="utf-8") as f:
        return f.read()
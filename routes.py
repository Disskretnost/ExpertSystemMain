from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from gigachat_client import get_gigachat_response
from database import execute_query, fetch_one, fetch_all
from auth import get_current_user, hash_password, verify_password, create_token, verify_token
from models import UserRegister, UserLogin

router = APIRouter()


# ==================== АВТОРИЗАЦИЯ ====================

@router.post("/register")
async def register(user: UserRegister):
    existing = fetch_one("SELECT id FROM users WHERE username = ? OR email = ?",
                         [user.username, user.email])
    if existing:
        raise HTTPException(400, "Username or email already exists")

    password_hash = hash_password(user.password)
    user_id = execute_query(
        "INSERT INTO users (username, email, password_hash, full_name, age) VALUES (?, ?, ?, ?, ?)",
        [user.username, user.email, password_hash, user.full_name, user.age]
    )

    token = create_token(user_id, user.username)
    return {"access_token": token, "token_type": "bearer", "user_id": user_id}


@router.post("/login")
async def login(login_data: UserLogin):
    user = fetch_one(
        "SELECT id, username, password_hash FROM users WHERE username = ? OR email = ?",
        [login_data.username_or_email, login_data.username_or_email]
    )

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    execute_query("UPDATE users SET last_login = ? WHERE id = ?",
                  [datetime.now(), user["id"]])

    token = create_token(user["id"], user["username"])
    return {"access_token": token, "token_type": "bearer", "user_id": user["id"], "username": user["username"]}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user = fetch_one("SELECT id, username, email, full_name, age, created_at FROM users WHERE id = ?",
                     [current_user["user_id"]])
    if not user:
        raise HTTPException(404, "User not found")
    return dict(user)


@router.get("/check-auth")
async def check_auth(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return {"authenticated": False}
    try:
        token = auth_header.replace("Bearer ", "")
        user_data = verify_token(token)
        if user_data:
            return {"authenticated": True, "user_id": user_data["user_id"], "username": user_data["username"]}
    except:
        pass
    return {"authenticated": False}


# ==================== ФИТНЕС-ПРОФИЛЬ ====================

class ProfileData(BaseModel):
    height: float
    weight: float
    age: int
    gender: str
    bmi: float
    bmiCategory: str
    activity: str
    fitnessSelf: str
    fitnessLevel: str
    goal: str
    goalText: str
    daily_calories: Optional[int] = None
    target_weight: Optional[float] = None
    measurement_date: Optional[str] = None  # НОВОЕ ПОЛЕ


@router.post("/profile/save")
async def save_profile(profile: ProfileData, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    # Используем переданную дату или сегодняшнюю
    measurement_date = profile.measurement_date if profile.measurement_date else date.today().isoformat()

    existing = fetch_one("SELECT id FROM fitness_profiles WHERE user_id = ?", [user_id])

    if existing:
        execute_query("""
                      UPDATE fitness_profiles
                      SET height=?,
                          weight=?,
                          age=?,
                          gender=?,
                          bmi=?,
                          bmi_category=?,
                          activity=?,
                          fitness_self=?,
                          fitness_level=?,
                          goal=?,
                          daily_calories=?,
                          target_weight=?,
                          saved_at=CURRENT_TIMESTAMP
                      WHERE user_id = ?
                      """, [
                          profile.height, profile.weight, profile.age, profile.gender,
                          profile.bmi, profile.bmiCategory, profile.activity, profile.fitnessSelf,
                          profile.fitnessLevel, profile.goal, profile.daily_calories, profile.target_weight, user_id
                      ])
    else:
        execute_query("""
                      INSERT INTO fitness_profiles
                      (user_id, height, weight, age, gender, bmi, bmi_category,
                       activity, fitness_self, fitness_level, goal, daily_calories, target_weight)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                      """, [
                          user_id, profile.height, profile.weight, profile.age, profile.gender,
                          profile.bmi, profile.bmiCategory, profile.activity, profile.fitnessSelf,
                          profile.fitnessLevel, profile.goal, profile.daily_calories, profile.target_weight
                      ])

    # СОХРАНЯЕМ ВЕС В ИСТОРИЮ С УКАЗАННОЙ ДАТОЙ
    existing_history = fetch_one(
        "SELECT id FROM fitness_history WHERE user_id = ? AND date = ?",
        [user_id, measurement_date]
    )

    if existing_history:
        execute_query("""
                      UPDATE fitness_history
                      SET weight = ?
                      WHERE user_id = ? AND date = ?
                      """, [profile.weight, user_id, measurement_date])
    else:
        execute_query("""
                      INSERT INTO fitness_history (user_id, date, weight)
                      VALUES (?, ?, ?)
                      """, [user_id, measurement_date, profile.weight])

    # СОХРАНЯЕМ В ТАБЛИЦУ ВЕСА
    existing_weight = fetch_one("SELECT id FROM weight_history WHERE user_id = ? AND date = ?",
                                [user_id, measurement_date])
    if existing_weight:
        execute_query("""
                      UPDATE weight_history
                      SET weight     = ?,
                          updated_at = CURRENT_TIMESTAMP
                      WHERE user_id = ? AND date = ?
                      """, [profile.weight, user_id, measurement_date])
    else:
        execute_query("""
                      INSERT INTO weight_history (user_id, date, weight)
                      VALUES (?, ?, ?)
                      """, [user_id, measurement_date, profile.weight])

    return {"success": True, "daily_calories": profile.daily_calories}

@router.get("/profile/get")
async def get_profile(current_user: dict = Depends(get_current_user)):
    profile = fetch_one("SELECT * FROM fitness_profiles WHERE user_id = ?", [current_user["user_id"]])
    return dict(profile) if profile else None


# ==================== ФИТНЕС-ТЕСТЫ ====================

class TestsData(BaseModel):
    test_date: str
    pullups: Optional[int] = None
    pushups: Optional[int] = None
    benchpress: Optional[int] = None
    plank: Optional[int] = None
    run: Optional[float] = None
    walking: Optional[int] = None
    total_score: int
    level: str


@router.post("/tests/save")
async def save_tests(tests: TestsData, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    test_date = tests.test_date

    # Получаем текущий вес из профиля
    profile_data = fetch_one("SELECT weight FROM fitness_profiles WHERE user_id = ?", [user_id])
    current_weight = profile_data["weight"] if profile_data else None

    # Сохраняем результат теста
    existing = fetch_one(
        "SELECT id FROM fitness_tests WHERE user_id = ? AND test_date = ?",
        [user_id, test_date]
    )

    if existing:
        execute_query("""
            UPDATE fitness_tests 
            SET pullups=?, pushups=?, benchpress=?, plank=?, run=?, walking=?, total_score=?, level=?
            WHERE user_id=? AND test_date=?
        """, [
            tests.pullups, tests.pushups, tests.benchpress,
            tests.plank, tests.run, tests.walking, tests.total_score, tests.level,
            user_id, test_date
        ])
    else:
        execute_query("""
            INSERT INTO fitness_tests 
            (user_id, test_date, pullups, pushups, benchpress, plank, run, walking, total_score, level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            user_id, test_date, tests.pullups, tests.pushups, tests.benchpress,
            tests.plank, tests.run, tests.walking, tests.total_score, tests.level
        ])

    # ОБНОВЛЯЕМ ИСТОРИЮ С ВЕСОМ И ДАННЫМИ ТЕСТА
    existing_history = fetch_one(
        "SELECT id FROM fitness_history WHERE user_id = ? AND date = ?",
        [user_id, test_date]
    )

    if existing_history:
        execute_query("""
            UPDATE fitness_history 
            SET weight = ?, fitness_score = ?, fitness_level = ?,
                pullups = ?, pushups = ?, benchpress = ?, plank = ?, run = ?, walking = ?
            WHERE user_id = ? AND date = ?
        """, [
            current_weight, tests.total_score, tests.level,
            tests.pullups, tests.pushups, tests.benchpress, tests.plank, tests.run, tests.walking,
            user_id, test_date
        ])
    else:
        execute_query("""
            INSERT INTO fitness_history 
            (user_id, date, weight, fitness_score, fitness_level, pullups, pushups, benchpress, plank, run, walking)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            user_id, test_date, current_weight, tests.total_score, tests.level,
            tests.pullups, tests.pushups, tests.benchpress, tests.plank, tests.run, tests.walking
        ])

    return {"success": True}


@router.get("/tests/get")
async def get_tests(current_user: dict = Depends(get_current_user)):
    tests = fetch_one("""
        SELECT test_date, pullups, pushups, benchpress, plank, run, walking, total_score, level
        FROM fitness_tests 
        WHERE user_id = ? 
        ORDER BY test_date DESC LIMIT 1
    """, [current_user["user_id"]])
    return dict(tests) if tests else None


@router.get("/tests/get_by_date")
async def get_tests_by_date(date: str, current_user: dict = Depends(get_current_user)):
    tests = fetch_one("""
        SELECT test_date, pullups, pushups, benchpress, plank, run, walking, total_score, level
        FROM fitness_tests 
        WHERE user_id = ? AND test_date = ?
    """, [current_user["user_id"], date])
    return dict(tests) if tests else None


# ==================== ИСТОРИЯ ====================

@router.get("/history/get")
async def get_history(current_user: dict = Depends(get_current_user)):
    """Получение истории по дням для графиков (с весом)"""
    history = fetch_all("""
        SELECT date, weight, fitness_score, fitness_level, 
               pullups, pushups, benchpress, plank, run, walking
        FROM fitness_history
        WHERE user_id = ?
        ORDER BY date ASC
    """, [current_user["user_id"]])

    result = []
    for row in history:
        result.append({
            "recorded_at": row["date"],
            "weight": row["weight"],
            "fitness_score": row["fitness_score"],
            "fitness_level": row["fitness_level"],
            "pullups": row["pullups"],
            "pushups": row["pushups"],
            "benchpress": row["benchpress"],
            "plank": row["plank"],
            "run": row["run"],
            "walking": row["walking"]
        })

    return result


# ==================== ДНЕВНИК ПИТАНИЯ ====================

class FoodItem(BaseModel):
    name: str
    grams: int
    calories: int = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0


class MealData(BaseModel):
    date: str
    meal_type: str
    foods: List[FoodItem]


class WeightData(BaseModel):
    weight: float
    date: str


@router.post("/nutrition/add")
async def add_meal(meal_data: MealData, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]

    for food in meal_data.foods:
        execute_query("""
            INSERT INTO nutrition_log (user_id, date, meal_type, food_name, grams, calories, protein, fat, carbs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            user_id, meal_data.date, meal_data.meal_type, food.name, food.grams,
            food.calories, food.protein, food.fat, food.carbs
        ])

    return {"success": True}


@router.get("/nutrition/by_date")
async def get_nutrition_by_date(date: str, current_user: dict = Depends(get_current_user)):
    """Получение питания за конкретную дату"""
    user_id = current_user["user_id"]

    meals = fetch_all("""
        SELECT id, meal_type, food_name, grams, calories, protein, fat, carbs, logged_at
        FROM nutrition_log
        WHERE user_id = ? AND date = ?
        ORDER BY meal_type, logged_at ASC
    """, [user_id, date])

    result = {
        "breakfast": [],
        "lunch": [],
        "snack": [],
        "dinner": [],
        "extra": []
    }

    for meal in meals:
        result[meal["meal_type"]].append({
            "id": meal["id"],
            "name": meal["food_name"],
            "grams": meal["grams"],
            "calories": meal["calories"],
            "protein": meal["protein"],
            "fat": meal["fat"],
            "carbs": meal["carbs"],
            "logged_at": meal["logged_at"]
        })

    return result


@router.get("/nutrition/week")
async def get_week_nutrition(current_user: dict = Depends(get_current_user)):
    """Получение суммарных калорий за неделю по дням"""
    user_id = current_user["user_id"]

    logs = fetch_all("""
        SELECT date, SUM(calories) as total_calories
        FROM nutrition_log
        WHERE user_id = ? AND date >= date('now', '-30 days')
        GROUP BY date
        ORDER BY date ASC
    """, [user_id])

    result = {}
    for log in logs:
        result[log["date"]] = {
            "totals": {
                "calories": log["total_calories"]
            }
        }

    return result


# ==================== ВЕС ====================

@router.post("/weight/save")
async def save_weight(weight_data: WeightData, current_user: dict = Depends(get_current_user)):
    """Сохранение веса за конкретную дату"""
    user_id = current_user["user_id"]
    today = weight_data.date

    # Обновляем вес в профиле
    profile = fetch_one("SELECT id, height FROM fitness_profiles WHERE user_id = ?", [user_id])
    if profile and profile["height"]:
        height_m = profile["height"] / 100
        bmi = round(weight_data.weight / (height_m * height_m), 1)
        execute_query("""
            UPDATE fitness_profiles 
            SET weight = ?, bmi = ?
            WHERE user_id = ?
        """, [weight_data.weight, bmi, user_id])

    # СОХРАНЯЕМ В ТАБЛИЦУ ВЕСА
    existing_weight = fetch_one("SELECT id FROM weight_history WHERE user_id = ? AND date = ?",
                                [user_id, today])
    if existing_weight:
        execute_query("""
            UPDATE weight_history SET weight = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND date = ?
        """, [weight_data.weight, user_id, today])
    else:
        execute_query("""
            INSERT INTO weight_history (user_id, date, weight)
            VALUES (?, ?, ?)
        """, [user_id, today, weight_data.weight])

    # СОХРАНЯЕМ ВЕС В ИСТОРИЮ fitness_history
    existing_history = fetch_one(
        "SELECT id FROM fitness_history WHERE user_id = ? AND date = ?",
        [user_id, today]
    )

    if existing_history:
        execute_query("""
            UPDATE fitness_history SET weight = ? WHERE user_id = ? AND date = ?
        """, [weight_data.weight, user_id, today])
    else:
        execute_query("""
            INSERT INTO fitness_history (user_id, date, weight) VALUES (?, ?, ?)
        """, [user_id, today, weight_data.weight])

    return {"success": True}


@router.get("/weight/history")
async def get_weight_history(current_user: dict = Depends(get_current_user)):
    """Получение истории веса"""
    history = fetch_all("""
        SELECT date, weight
        FROM weight_history
        WHERE user_id = ?
        ORDER BY date ASC
    """, [current_user["user_id"]])

    return [{"date": row["date"], "weight": row["weight"]} for row in history]


@router.get("/weight/by_date")
async def get_weight_by_date(date: str, current_user: dict = Depends(get_current_user)):
    """Получение веса за конкретную дату"""
    weight = fetch_one("""
        SELECT date, weight
        FROM weight_history
        WHERE user_id = ? AND date = ?
    """, [current_user["user_id"], date])

    return dict(weight) if weight else None

@router.get("/ai/nutrition-advice")
async def get_nutrition_advice(current_user: dict = Depends(get_current_user)):
    """Получение персонализированных рекомендаций по питанию от GigaChat"""
    from gigachat_client import get_gigachat_response

    user_id = current_user["user_id"]

    # 1. Получаем профиль пользователя
    profile = fetch_one("SELECT * FROM fitness_profiles WHERE user_id = ?", [user_id])
    if not profile:
        return {"recommendations": "Заполните профиль (рост, вес, цель), чтобы получить рекомендации."}

    # 2. Получаем питание за последние 14 дней
    nutrition_logs = fetch_all("""
                               SELECT date, meal_type, food_name, grams, calories, protein, fat, carbs
                               FROM nutrition_log
                               WHERE user_id = ? AND date >= date ('now', '-14 days')
                               ORDER BY date DESC, meal_type
                               """, [user_id])

    # Формируем историю питания
    nutrition_history = ""
    current_date = None
    daily_totals = {}

    for log in nutrition_logs[:30]:
        if current_date != log["date"]:
            current_date = log["date"]
            nutrition_history += f"\n📅 {current_date}:\n"
            daily_totals[current_date] = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0}
        nutrition_history += f"  - {log['meal_type']}: {log['food_name']} ({log['grams']}г) = {log['calories']} ккал, белки: {log['protein'] or 0}г, жиры: {log['fat'] or 0}г, углеводы: {log['carbs'] or 0}г\n"
        daily_totals[current_date]["calories"] += log['calories'] or 0
        daily_totals[current_date]["protein"] += log['protein'] or 0
        daily_totals[current_date]["fat"] += log['fat'] or 0
        daily_totals[current_date]["carbs"] += log['carbs'] or 0

    # Считаем средние
    if daily_totals:
        avg_calories = round(sum(d["calories"] for d in daily_totals.values()) / len(daily_totals))
        avg_protein = round(sum(d["protein"] for d in daily_totals.values()) / len(daily_totals))
        avg_fat = round(sum(d["fat"] for d in daily_totals.values()) / len(daily_totals))
        avg_carbs = round(sum(d["carbs"] for d in daily_totals.values()) / len(daily_totals))
    else:
        avg_calories = 0
        avg_protein = 0
        avg_fat = 0
        avg_carbs = 0

    goal_text = {"lose": "похудеть", "gain": "набрать массу", "maintain": "поддерживать форму"}.get(profile["goal"],
                                                                                                    "поддерживать форму")
    target_calories = profile['daily_calories'] or 2400

    # Нормы БЖУ в зависимости от цели
    weight = profile['weight']
    if profile['goal'] == 'lose':
        protein_norm = round(weight * 2.0)
        fat_norm = round(weight * 0.7)
        carbs_norm = round(weight * 3.5)
    elif profile['goal'] == 'gain':
        protein_norm = round(weight * 1.8)
        fat_norm = round(weight * 0.9)
        carbs_norm = round(weight * 4.5)
    else:
        protein_norm = round(weight * 1.6)
        fat_norm = round(weight * 0.8)
        carbs_norm = round(weight * 4.0)

    prompt = f"""Ты — персональный диетолог.

================================================================================
ИНФОРМАЦИЯ О ПАЦИЕНТЕ:
================================================================================
- Рост: {profile['height']} см
- Вес: {profile['weight']} кг
- Цель: {goal_text}
- Целевая калорийность: {target_calories} ккал/день
- Норма белка: {protein_norm} г/день
- Норма жиров: {fat_norm} г/день
- Норма углеводов: {carbs_norm} г/день

================================================================================
ИСТОРИЯ ПИТАНИЯ (последние 14 дней):
================================================================================
{nutrition_history if nutrition_history else "Нет данных о питании"}

================================================================================
ТВОЯ ЗАДАЧА:
================================================================================
1. Проанализируй текущее питание пациента
2. Составь сбалансированное меню на день с учётом цели {goal_text} и калорийности {target_calories} ккал

**ПРАВИЛА СОСТАВЛЕНИЯ МЕНЮ:**
- В каждом приёме: 2-4 продукта
- Используй разнообразные полезные продукты
- ТЫ САМ рассчитываешь калории, белки, жиры, углеводы для каждого продукта
- В столбцах пиши значения для УКАЗАННОЙ порции (не на 100г)

**ВАЖНОЕ ТРЕБОВАНИЕ ПО ФОРМАТУ АНАЛИЗА:**
- Секция "Анализ" должна быть оформлена в виде СПИСКА (с дефисом).
- Используй формат, показанный в примере ниже.

**ПРИМЕР ПРАВИЛЬНОГО ФОРМАТА АНАЛИЗА:**

## 📊 Анализ текущего питания
- **Среднее потребление:** 2800 ккал/день, 112 г белка, 60 г жиров, 36 г углеводов
- **Цель:** 2416 ккал/день, 130 г белка, 65 г жиров, 324 г углеводов
- **Вывод:** Требуется скорректировать рацион, увеличив углеводы.

**ВАЖНОЕ ТРЕБОВАНИЕ ПО ФОРМАТУ ИТОГОВ:**
- ПОСЛЕ КАЖДОЙ ТАБЛИЦЫ напиши итог в ОТДЕЛЬНОЙ СТРОКЕ
- Итог должен быть в формате: **Итого:** X ккал | X г белка | X г жиров | X г углеводов
- Используй ВЕРТИКАЛЬНУЮ ЧЕРТУ (|) для разделения показателей

**ПРИМЕР ПРАВИЛЬНОГО ФОРМАТА ТАБЛИЦЫ:**
| Продукт | Порция | Ккал | Белки | Жиры | Углеводы |
|---------|--------|------|-------|------|----------|
| Овсянка | 80 г | 280 | 10 | 6 | 50 |
| Творог | 150 г | 180 | 27 | 9 | 9 |
**Итого:** 460 ккал | 37 г белка | 15 г жиров | 59 г углеводов

**ОТВЕТЬ В ТОЧНОСТИ ПО ЭТОМУ ФОРМАТУ:**

## 📊 Анализ текущего питания
- **Среднее потребление:** {avg_calories} ккал/день, {avg_protein} г белка, {avg_fat} г жиров, {avg_carbs} г углеводов
- **Цель:** {target_calories} ккал/день, {protein_norm} г белка, {fat_norm} г жиров, {carbs_norm} г углеводов
- **Вывод:** (напиши, чего не хватает или что в избытке, 1-2 предложения)

## 🍽️ РЕКОМЕНДУЕМОЕ МЕНЮ

### 🍳 Завтрак
| Продукт | Порция | Ккал | Белки | Жиры | Углеводы |
|---------|--------|------|-------|------|----------|
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
**Итого:** X ккал | X г белка | X г жиров | X г углеводов

### 🍱 Обед
| Продукт | Порция | Ккал | Белки | Жиры | Углеводы |
|---------|--------|------|-------|------|----------|
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
**Итого:** X ккал | X г белка | X г жиров | X г углеводов

### 🍎 Полдник
| Продукт | Порция | Ккал | Белки | Жиры | Углеводы |
|---------|--------|------|-------|------|----------|
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
**Итого:** X ккал | X г белка | X г жиров | X г углеводов

### 🍽️ Ужин
| Продукт | Порция | Ккал | Белки | Жиры | Углеводы |
|---------|--------|------|-------|------|----------|
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
**Итого:** X ккал | X г белка | X г жиров | X г углеводов

### 🍪 Перекус перед сном
| Продукт | Порция | Ккал | Белки | Жиры | Углеводы |
|---------|--------|------|-------|------|----------|
| [продукт] | [г] | [калории] | [белки] | [жиры] | [углеводы] |
**Итого:** X ккал | X г белка | X г жиров | X г углеводов

## 💡 Рекомендации
- Первая рекомендация
- Вторая рекомендация
- Третья рекомендация

**ВАЖНО:**
- Секция анализа должна быть списком с дефисами.
- Итоги пиши ТОЛЬКО с вертикальной чертой (|), без запятых
"""

    try:
        recommendations = get_gigachat_response(prompt)
        return {"recommendations": recommendations}
    except Exception as e:
        return {"recommendations": f"Ошибка: {str(e)}"}


@router.get("/ai/exercise-advice")
async def get_exercise_advice(current_user: dict = Depends(get_current_user)):
    """Получение персонализированных рекомендаций по упражнениям от GigaChat на основе последних 4 тренировок"""
    from gigachat_client import get_gigachat_response

    user_id = current_user["user_id"]

    # 1. Получаем профиль пользователя
    profile = fetch_one("SELECT * FROM fitness_profiles WHERE user_id = ?", [user_id])
    if not profile:
        return {"recommendations": "Заполните профиль (рост, вес, цель), чтобы получить рекомендации."}

    # 2. Получаем последние 4 тренировки (результаты тестов)
    recent_tests = fetch_all("""
                             SELECT test_date,
                                    pullups,
                                    pushups,
                                    benchpress,
                                    plank,
                                    run,
                                    walking,
                                    total_score,
                                    level
                             FROM fitness_tests
                             WHERE user_id = ?
                             ORDER BY test_date DESC LIMIT 4
                             """, [user_id])

    if not recent_tests:
        return {
            "recommendations": "Пройдите фитнес-тестирование хотя бы один раз, чтобы получить персональные рекомендации."}

    # 3. Получаем историю веса за последний месяц
    weight_history = fetch_all("""
                               SELECT date, weight
                               FROM weight_history
                               WHERE user_id = ? AND date >= date ('now', '-30 days')
                               ORDER BY date ASC
                               """, [user_id])

    # Формируем строку с историей тренировок
    training_history = ""
    for i, test in enumerate(recent_tests, 1):
        training_history += f"""
Тренировка #{i} (дата: {test['test_date']}):
- Подтягивания: {test['pullups'] if test['pullups'] is not None else 'нет данных'} раз
- Отжимания: {test['pushups'] if test['pushups'] is not None else 'нет данных'} раз
- Жим штанги: {test['benchpress'] if test['benchpress'] is not None else 'нет данных'} кг
- Планка: {test['plank'] if test['plank'] is not None else 'нет данных'} секунд
- Бег 1км: {test['run'] if test['run'] is not None else 'нет данных'} минут
- Ходьба: {test['walking'] if test['walking'] is not None else 'нет данных'} шагов в день
- Общая оценка: {test['total_score']} баллов
"""

    # Формируем историю веса
    weight_history_str = ""
    if weight_history:
        for w in weight_history:
            weight_history_str += f"- {w['date']}: {w['weight']} кг\n"
    else:
        weight_history_str = "Нет данных о динамике веса"

    goal_text = {
        "lose": "похудеть (снижение веса)",
        "gain": "набрать мышечную массу",
        "maintain": "поддерживать текущую форму"
    }.get(profile["goal"], "поддерживать форму")

    activity_text = {
        "none": "нет тренировок",
        "1-2": "1-2 раза в неделю",
        "3-4": "3-4 раза в неделю",
        "5+": "5+ раз в неделю"
    }.get(profile["activity"], "не указано")

    gender_text = "Мужской" if profile["gender"] == "male" else "Женский"

    prompt = f"""Ты — профессиональный фитнес-тренер с опытом более 10 лет.

================================================================================
ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
================================================================================
- Рост: {profile['height']} см
- Вес: {profile['weight']} кг
- Возраст: {profile['age']} лет
- Пол: {gender_text}
- Цель: {goal_text}
- Частота тренировок: {activity_text}

================================================================================
ИСТОРИЯ ВЕСА (последние 30 дней):
================================================================================
{weight_history_str}

================================================================================
РЕЗУЛЬТАТЫ ПОСЛЕДНИХ 4 ФИТНЕС-ТЕСТОВ (от новых к старым):
================================================================================
{training_history}

================================================================================
СПИСОК УПРАЖНЕНИЙ, ПО КОТОРЫМ НУЖНО ДАТЬ РЕКОМЕНДАЦИИ:
================================================================================
1. Подтягивания
2. Отжимания
3. Жим штанги
4. Планка
5. Бег (1 км)
6. Ходьба (шаги в день)

================================================================================
ТВОЯ ЗАДАЧА:
================================================================================
На основе предоставленных данных, дай рекомендации ТОЛЬКО по этим 6 упражнениям.

Для КАЖДОГО упражнения, где есть данные, напиши:
1. Текущий результат и динамику (улучшение/ухудшение за 4 тренировки)
2. Конкретные техники для улучшения:
   - Варианты хватов (для подтягиваний, жима)
   - Интервалы отдыха между подходами
   - Правильное дыхание
   - Количество подходов и повторений
   - Вариации упражнения (для прогрессии)
   - Частота выполнения в неделю

Если по упражнению нет данных — напиши "нет данных".

================================================================================
ФОРМАТ ОТВЕТА (строго соблюдай эту структуру):
================================================================================

## 📊 Общий анализ динамики

(Краткий анализ: что улучшилось, что ухудшилось, общий прогресс)

## 🎯 Рекомендации по каждому упражнению

### 1. Подтягивания

**Текущий результат:** X раз (динамика: +Y / -Z за 4 тренировки)

**Как улучшить:**
- **Хваты:** (какие использовать: прямой, обратный, нейтральный, широкий, узкий)
- **Интервалы:** отдых X секунд между подходами
- **Дыхание:** (как правильно дышать)
- **Подходы/повторения:** X подходов по Y раз
- **Вариации:** (с весом, резиной, негативные, частичные)
- **Частота:** X раз в неделю

### 2. Отжимания

**Текущий результат:** X раз (динамика: +Y / -Z)

**Как улучшить:**
- **Постановка рук:** (широкая, узкая, алмаз)
- **Интервалы:** отдых X секунд
- **Дыхание:** (на вдохе/выдохе)
- **Подходы/повторения:** X x Y
- **Вариации:** (с весом, на коленях, с хлопком)
- **Частота:** X раз в неделю

### 3. Жим штанги

**Текущий результат:** X кг (динамика: +Y / -Z)

**Как улучшить:**
- **Хват:** (ширина, закрытый/открытый)
- **Интервалы:** отдых X секунд
- **Дыхание:** (фаза опускания/подъёма)
- **Подходы/повторения:** X x Y
- **Вариации:** (жим с паузой, наклонный, гантели)
- **Частота:** X раз в неделю

### 4. Планка

**Текущий результат:** X секунд (динамика: +Y / -Z)

**Как улучшить:**
- **Техника:** (положение таза, лопатки, шея)
- **Дыхание:** (ровное, без задержек)
- **Вариации:** (боковая, с подъёмом ноги/руки, с весом)
- **Прогрессия:** добавлять по X секунд в неделю
- **Частота:** X раз в неделю

### 5. Бег (1 км)

**Текущий результат:** X мин (динамика: +Y / -Z)

**Как улучшить:**
- **Интервалы:** (чередование X сек бег / Y сек ходьба)
- **Дыхание:** (ритм вдох-выдох на X шагов)
- **Техника:** (постановка стопы, частота шагов)
- **Вариации:** (фартлек, интервальный бег, темповый)
- **Частота:** X раз в неделю

### 6. Ходьба

**Текущий результат:** X шагов/день (динамика: +Y / -Z)

**Как улучшить:**
- **Интенсивность:** (скорость, интервальная ходьба)
- **Техника:** (осанка, работа рук)
- **Прогрессия:** увеличивать на X шагов в неделю
- **Дыхание:** (ритмичное)
- **Частота:** ежедневно

## 💡 Общие рекомендации с учётом цели "{goal_text}"

(2-3 совета по питанию, восстановлению, режиму)

**ВАЖНО:** 
- Не придумывай упражнения, которых нет в списке
- Если динамики нет (всего 1 тест), напиши "недостаточно данных для анализа динамики"
- Будь максимально конкретным: цифры, секунды, проценты
"""

    try:
        recommendations = get_gigachat_response(prompt)
        return {"recommendations": recommendations}
    except Exception as e:
        return {"recommendations": f"Ошибка получения рекомендаций: {str(e)}"}
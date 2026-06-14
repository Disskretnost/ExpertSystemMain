from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ==================== МОДЕЛИ ДЛЯ АВТОРИЗАЦИИ ====================

class UserRegister(BaseModel):
    """Модель для регистрации пользователя"""
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    age: Optional[int] = None


class UserLogin(BaseModel):
    """Модель для входа пользователя"""
    username_or_email: str
    password: str


class UserResponse(BaseModel):
    """Модель ответа с данными пользователя"""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """Модель ответа с токеном"""
    access_token: str
    token_type: str
    user_id: int
    username: Optional[str] = None


class ErrorResponse(BaseModel):
    """Модель ошибки"""
    detail: str


# ==================== МОДЕЛИ ДЛЯ ПРОФИЛЯ ====================

class ProfileData(BaseModel):
    """Модель данных профиля пользователя"""
    height: float  # рост в см
    weight: float  # текущий вес в кг
    target_weight: Optional[float] = None  # желаемый вес в кг
    age: int  # возраст в годах
    gender: str  # male / female
    bmi: float  # индекс массы тела
    bmiCategory: str  # категория ИМТ
    activity: str  # none / 1-2 / 3-4 / 5+
    fitnessSelf: str  # самооценка физической подготовки
    fitnessLevel: str  # уровень подготовки (Начинающий/Средний/Продвинутый)
    goal: str  # lose / gain / maintain
    goalText: str  # текстовое описание цели


class ProfileResponse(BaseModel):
    """Модель ответа с профилем пользователя"""
    id: int
    user_id: int
    height: float
    weight: float
    target_weight: Optional[float] = None
    daily_calories: Optional[int] = None
    age: int
    gender: str
    bmi: float
    bmi_category: str
    activity: str
    fitness_self: str
    fitness_level: str
    goal: str
    saved_at: datetime


# ==================== МОДЕЛИ ДЛЯ ФИТНЕС-ТЕСТОВ ====================

class TestsData(BaseModel):
    """Модель результатов фитнес-тестирования"""
    pullups: Optional[int] = None  # количество подтягиваний
    pushups: Optional[int] = None  # количество отжиманий
    bench_press: Optional[int] = None  # количество жимов штанги
    plank: Optional[int] = None  # время планки в секундах
    walking: Optional[float] = None  # время ходьбы 1 км в минутах
    total_score: int  # общая сумма баллов
    level: str  # уровень подготовки


class TestsResponse(BaseModel):
    """Модель ответа с результатами тестов"""
    id: int
    user_id: int
    pullups: Optional[int] = None
    pushups: Optional[int] = None
    bench_press: Optional[int] = None
    plank: Optional[int] = None
    walking: Optional[float] = None
    total_score: int
    level: str
    test_date: datetime


# ==================== МОДЕЛИ ДЛЯ ИСТОРИИ ====================

class HistoryItem(BaseModel):
    """Модель элемента истории тренировок"""
    recorded_at: datetime
    bmi: Optional[float] = None
    fitness_score: Optional[int] = None
    fitness_level: Optional[str] = None
    pullups: Optional[int] = None
    pushups: Optional[int] = None
    bench_press: Optional[int] = None
    plank: Optional[int] = None
    walking: Optional[float] = None


class HistoryResponse(BaseModel):
    """Модель ответа с историей"""
    history: list[HistoryItem]


# ==================== МОДЕЛИ ДЛЯ ДНЕВНИКА ПИТАНИЯ ====================

class FoodItem(BaseModel):
    """Модель продукта питания"""
    name: str  # название продукта
    grams: int  # вес в граммах
    calories: int = 0  # калории
    protein: float = 0  # белки в граммах
    fat: float = 0  # жиры в граммах
    carbs: float = 0  # углеводы в граммах


class MealData(BaseModel):
    """Модель приёма пищи"""
    meal_type: str  # breakfast, lunch, snack, dinner, extra
    foods: list[FoodItem]  # список продуктов
    date: str  # дата в формате YYYY-MM-DD


class FullDayData(BaseModel):
    """Модель полного дня питания"""
    meals: list[MealData]  # список приёмов пищи


class NutritionTotals(BaseModel):
    """Модель суммарных показателей питания за день"""
    calories: int = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0


class DayNutritionResponse(BaseModel):
    """Модель ответа с питанием за день"""
    breakfast: list[FoodItem] = []
    lunch: list[FoodItem] = []
    snack: list[FoodItem] = []
    dinner: list[FoodItem] = []
    extra: list[FoodItem] = []
    totals: NutritionTotals = NutritionTotals()


class WeekNutritionResponse(BaseModel):
    """Модель ответа с питанием за неделю"""
    data: dict[str, DayNutritionResponse]  # ключ - дата, значение - питание за день


# ==================== МОДЕЛИ ДЛЯ ПЛАНА ТРЕНИРОВОК ====================

class WorkoutExercise(BaseModel):
    """Модель упражнения в плане тренировки"""
    name: str  # название упражнения
    sets: int  # количество подходов
    reps: int  # количество повторений
    rest_seconds: int = 60  # отдых в секундах
    notes: Optional[str] = None  # примечания


class WorkoutDay(BaseModel):
    """Модель дня тренировки"""
    day_name: str  # название дня (Понедельник, Вторник и т.д.)
    day_number: int  # номер дня (1-7)
    focus: str  # фокус тренировки (Грудь/Спина/Ноги и т.д.)
    exercises: list[WorkoutExercise]  # список упражнений
    duration_minutes: int = 45  # продолжительность в минутах


class WorkoutPlanResponse(BaseModel):
    """Модель ответа с планом тренировок"""
    user_id: int
    goal: str  # цель пользователя
    fitness_level: str  # уровень подготовки
    plan: list[WorkoutDay]  # план на неделю
    generated_at: datetime


# ==================== ВСПОМОГАТЕЛЬНЫЕ МОДЕЛИ ====================

class DailyCaloriesResponse(BaseModel):
    """Модель ответа с нормой калорий"""
    daily_calories: int  # суточная норма калорий
    remaining_calories: int  # оставшиеся калории на сегодня
    consumed_calories: int  # потреблённые калории за сегодня
    goal: str  # цель пользователя


class BMICalculation(BaseModel):
    """Модель расчёта ИМТ"""
    bmi: float
    category: str  # категория ИМТ
    healthy_weight_range: str  # диапазон здорового веса


class CaloricNeeds(BaseModel):
    """Модель расчёта потребности в калориях"""
    bmr: int  # базовый метаболизм
    tdee: int  # общий расход энергии
    recommended_intake: int  # рекомендуемое потребление
    goal_adjustment: int  # корректировка под цель
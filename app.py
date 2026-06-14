from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
from routes import router as api_router
from pages import router as pages_router

app = FastAPI(title="Parkinson's Diagnostic System")

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(pages_router, tags=["Pages"])

@app.on_event("startup")
def startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
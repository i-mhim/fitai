from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.assessments.router import router as assessments_router
from app.feasibility.router import router as feasibility_router
from app.goals.router import router as goals_router

app = FastAPI(title="Adaptive Fitness API", version="0.4.0")
app.include_router(auth_router)
app.include_router(goals_router)
app.include_router(assessments_router)
app.include_router(feasibility_router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore  # type: ignore

from app.common.firestore_client import get_db_dep
from app.auth.routes import router as auth_router
from app.employees.routes import router as employees_router
from app.calls.routes import router as calls_router
from app.payments.routes import router as payments_router
from app.dashboard.routes import router as dashboard_router
from app.manager.router import router as manager_router

app = FastAPI(
    title="Staff Performance Tracker API",
    version="0.4.0",
    description="API for managing staff performance, calls, demos, payments and incentives",
)

# --- CORS CONFIG ---
origins = [
    "*",  # you can later restrict to your domains: cloudshell, firebase, etc.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Staff Performance Tracker API",
        "version": "0.4.0",
    }


@app.get("/health")
def health(db: firestore.Client = Depends(get_db_dep)):
    if db is None:
        return {"status": "error", "firestore": "not_initialized"}
    return {"status": "healthy", "firestore": "connected"}


# Register routes
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(employees_router, prefix="/employees", tags=["Employees"])
app.include_router(calls_router, prefix="/calls", tags=["Calls & Demos"])
app.include_router(payments_router, prefix="/payments", tags=["Payments"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard & Incentives"])
app.include_router(manager_router, prefix="/manager", tags=["Manager"])


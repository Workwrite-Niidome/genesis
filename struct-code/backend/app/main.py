import os
print("=== STARTUP ENV CHECK ===")
print(f"DATABASE_URL at startup: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
print("=========================")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from sqlalchemy import text, inspect

from .services.struct_calculator_refactored import StructCalculatorRefactored
from .routers import struct_code_v2
from .routers import struct_code_dynamic
from .config.database import engine, Base
from .models.diagnosis_result import DiagnosisResult

app = FastAPI(
    title="STRUCT CODE API",
    description="STRUCT CODE診断システム - 動的構造計算対応版",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V2 APIルーターを登録（従来の静的API）
print(f"=== Registering V2 Router (Static) ===")
print(f"Router has {len(struct_code_v2.router.routes)} routes:")
for route in struct_code_v2.router.routes:
    methods = list(route.methods) if hasattr(route, 'methods') else []
    print(f"  {methods} {route.path}")
app.include_router(struct_code_v2.router)
print("=== V2 Router registered ===")

# Dynamic APIルーターを登録（新しい動的API）
print(f"=== Registering Dynamic Router ===")
print(f"Router has {len(struct_code_dynamic.router.routes)} routes:")
for route in struct_code_dynamic.router.routes:
    methods = list(route.methods) if hasattr(route, 'methods') else []
    print(f"  {methods} {route.path}")
app.include_router(struct_code_dynamic.router)
print("=== Dynamic Router registered ===")

calculator = StructCalculatorRefactored()

def run_migrations():
    """既存テーブルに新しいカラムを追加するマイグレーション"""
    inspector = inspect(engine)

    if 'diagnosis_results' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('diagnosis_results')]

        with engine.connect() as conn:
            # diagnosis_id カラムを追加
            if 'diagnosis_id' not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE diagnosis_results ADD COLUMN diagnosis_id VARCHAR(12)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_diagnosis_results_diagnosis_id ON diagnosis_results(diagnosis_id)"
                ))
                conn.commit()
                print("MIGRATION: Added diagnosis_id column")

            # response_json カラムを追加
            if 'response_json' not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE diagnosis_results ADD COLUMN response_json JSON"
                ))
                conn.commit()
                print("MIGRATION: Added response_json column")

@app.on_event("startup")
async def startup_event():
    # DBテーブルを作成
    Base.metadata.create_all(bind=engine)
    print("SUCCESS: Database tables created/verified")

    # マイグレーション実行
    try:
        run_migrations()
        print("SUCCESS: Migrations completed")
    except Exception as e:
        print(f"WARNING: Migration error (may already be applied): {e}")

    await calculator.initialize()
    print("SUCCESS: STRUCT CODE API v2.0 started (with dynamic calculation)")

@app.get("/")
async def root():
    return {
        "message": "STRUCT CODE API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "static": "/api/v2/diagnosis",
            "dynamic": "/api/v2/dynamic/diagnosis",
            "compare": "/api/v2/dynamic/compare"
        }
    }

@app.get("/api/questions")
async def get_questions():
    return calculator.get_questions()

@app.get("/api/types")
async def get_all_types():
    return calculator.get_all_types()

@app.get("/api/types/{type_code}")
async def get_type_detail(type_code: str):
    detail = calculator.get_type_detail(type_code)
    if not detail:
        raise HTTPException(status_code=404, detail="Type not found")
    return detail

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": ["static_diagnosis", "dynamic_diagnosis", "time_comparison"]
    }

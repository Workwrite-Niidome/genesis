# -*- coding: utf-8 -*-
"""
STRUCT CODE v2.0 Dynamic API Router
動的構造計算を使用した新API

Features:
- 診断日時による動的な構造計算
- ネイタル構造と現在構造の分離
- 時期テーマの提供
- 将来予測の提供
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import json
import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import hashlib

from app.services.dynamic_struct_calculator import (
    DynamicStructCalculator,
    DynamicDiagnosisResult,
    convert_to_api_response
)
from app.models.schemas import AnswerData as AnswerDataModel
from app.config.database import get_db
from app.services.diagnosis_storage import save_diagnosis_result, get_diagnosis_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/dynamic", tags=["STRUCT CODE v2 Dynamic"])

# 計算機のインスタンス（シングルトン）
dynamic_calculator = None

# 診断結果キャッシュ
diagnosis_cache: Dict[str, Dict] = {}
cache_expiry: Dict[str, datetime] = {}


async def get_dynamic_calculator() -> DynamicStructCalculator:
    """動的計算機インスタンスを取得（遅延初期化）"""
    global dynamic_calculator
    if dynamic_calculator is None:
        dynamic_calculator = DynamicStructCalculator()
        await dynamic_calculator.static_calculator.initialize()
    return dynamic_calculator


def generate_diagnosis_id(birth_date: str, location: str, timestamp: str) -> str:
    """診断IDを生成"""
    data = f"{birth_date}_{location}_{timestamp}"
    return hashlib.md5(data.encode()).hexdigest()[:12]


def clean_expired_cache():
    """期限切れのキャッシュを削除"""
    now = datetime.utcnow()
    expired_ids = [
        did for did, expiry in cache_expiry.items()
        if expiry < now
    ]
    for did in expired_ids:
        diagnosis_cache.pop(did, None)
        cache_expiry.pop(did, None)


# === Pydanticモデル ===

class Answer(BaseModel):
    """回答データ"""
    question_id: str = Field(..., example="Q.01")
    choice: str = Field(..., example="A")


class DynamicDiagnosisRequest(BaseModel):
    """動的診断リクエスト"""
    birth_date: str = Field(..., example="1990-01-15", description="生年月日 YYYY-MM-DD")
    birth_location: str = Field(..., example="Tokyo", description="出生地")
    answers: List[Answer] = Field(..., description="25問の回答")
    birth_time: Optional[str] = Field(None, example="14:30", description="出生時刻（任意）HH:MM")
    diagnosis_date: Optional[str] = Field(None, example="2024-01-15T10:30:00", description="診断日時（省略時は現在）")


class AxisScore(BaseModel):
    """軸スコア"""
    起動軸: int
    判断軸: int
    選択軸: int
    共鳴軸: int
    自覚軸: int


class StructureData(BaseModel):
    """構造データ"""
    type: str
    type_name: str
    sds: List[float]
    sds_display: AxisScore
    description: str


class TemporalData(BaseModel):
    """時期データ"""
    current_theme: str
    theme_description: str
    active_transits: List[Dict[str, Any]]
    future_outlook: List[Dict[str, Any]]


class DynamicDiagnosisResponse(BaseModel):
    """動的診断レスポンス"""
    diagnosis_id: str
    struct_code: str
    diagnosis_timestamp: str

    # ネイタル構造（生涯の本質）
    natal: StructureData

    # 現在構造（時期を反映）
    current: StructureData

    # TOP3タイプ
    top3_types: List[str]

    # DesignGap
    design_gap: Dict[str, float]

    # 時期データ
    temporal: TemporalData

    # 後方互換性のための従来データ
    legacy: Optional[Dict[str, Any]] = None


@router.post("/diagnosis", response_model=None)
async def create_dynamic_diagnosis(request: DynamicDiagnosisRequest, db: Session = Depends(get_db)):
    """
    動的診断を実行

    - 生年月日、出生地、25問の回答から診断を実行
    - 診断日時（省略時は現在）に基づいた動的な構造を計算
    - ネイタル構造（生涯の本質）と現在構造（時期を反映）を分離して出力
    - 時期テーマと将来予測を提供
    """
    try:
        # キャッシュクリーンアップ
        clean_expired_cache()

        # 計算機を取得
        calc = await get_dynamic_calculator()

        # Answerを AnswerDataModelに変換
        answers = [
            AnswerDataModel(question_id=ans.question_id, choice=ans.choice)
            for ans in request.answers
        ]

        # 診断日時をパース
        diagnosis_date = None
        if request.diagnosis_date:
            try:
                # ISO形式の日時文字列をパース
                diagnosis_date = datetime.fromisoformat(request.diagnosis_date.replace('Z', '+00:00'))
                # タイムゾーン情報を削除（naive datetimeに変換）
                if diagnosis_date.tzinfo is not None:
                    diagnosis_date = diagnosis_date.replace(tzinfo=None)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="診断日時の形式が不正です。ISO形式（例: 2024-01-15T10:30:00）で指定してください。"
                )

        # 動的診断実行
        result = await calc.calculate_dynamic_struct_code(
            birth_date=request.birth_date,
            birth_time=request.birth_time,
            birth_location=request.birth_location,
            answers=answers,
            diagnosis_date=diagnosis_date
        )

        # 診断IDを生成
        diagnosis_id = generate_diagnosis_id(
            birth_date=request.birth_date,
            location=request.birth_location,
            timestamp=datetime.utcnow().isoformat()
        )

        # API応答形式に変換
        response_data = convert_to_api_response(result)
        response_data['diagnosis_id'] = diagnosis_id

        # キャッシュに保存（24時間）
        diagnosis_cache[diagnosis_id] = response_data
        cache_expiry[diagnosis_id] = datetime.utcnow() + timedelta(hours=24)

        # DB保存（非ブロッキング）
        try:
            natal_data = response_data.get('natal', {})
            current_data = response_data.get('current', {})
            design_gap_data = response_data.get('design_gap', {})
            temporal_data = response_data.get('temporal', {})

            # ネイタル軸スコアを取得（sds_displayから）
            natal_sds_display = natal_data.get('sds_display', {})
            natal_axis_scores = {
                "activation": natal_sds_display.get('起動軸', 500),
                "judgment": natal_sds_display.get('判断軸', 500),
                "choice": natal_sds_display.get('選択軸', 500),
                "resonance": natal_sds_display.get('共鳴軸', 500),
                "awareness": natal_sds_display.get('自覚軸', 500),
            }

            natal_result = {
                "struct_type": result.natal_type,
                "struct_code": "",  # struct_codeはカレントベースなので使わない
                "axis_scores": natal_axis_scores,
                "similarity_score": 0.0,
                "type_detail": {
                    "label": natal_data.get('type_name', '')
                },
                "vectors": {},
                "top_candidates": response_data.get('top3_types', [])
            }

            # カレント軸スコアを取得（sds_displayから）
            current_sds_display = current_data.get('sds_display', {})
            current_axis_scores = {
                "activation": current_sds_display.get('起動軸', 500),
                "judgment": current_sds_display.get('判断軸', 500),
                "choice": current_sds_display.get('選択軸', 500),
                "resonance": current_sds_display.get('共鳴軸', 500),
                "awareness": current_sds_display.get('自覚軸', 500),
            }

            current_result = {
                "struct_type": result.current_type,
                "struct_code": response_data.get('struct_code', ''),
                "axis_scores": current_axis_scores,
                "type_detail": {
                    "label": current_data.get('type_name', '')
                }
            }

            # DesignGapを適切な形式に変換
            design_gap = {
                "activation": design_gap_data.get('起動軸', 0),
                "judgment": design_gap_data.get('判断軸', 0),
                "choice": design_gap_data.get('選択軸', 0),
                "resonance": design_gap_data.get('共鳴軸', 0),
                "awareness": design_gap_data.get('自覚軸', 0),
            }

            save_diagnosis_result(
                db=db,
                diagnosis_type="current",
                birth_date=request.birth_date,
                birth_location=request.birth_location,
                birth_time=request.birth_time,
                natal_result=natal_result,
                current_result=current_result,
                design_gap=design_gap,
                period_theme=temporal_data.get('current_theme', ''),
                answers=answers,
                diagnosis_id=diagnosis_id,
                response_data=response_data
            )
        except Exception as e:
            logger.error(f"Failed to save dynamic diagnosis result (non-blocking): {e}")

        # 明示的にUTF-8でJSONレスポンスを返す
        return JSONResponse(
            content=response_data,
            media_type="application/json; charset=utf-8"
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"入力エラー: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"診断エラー: {str(e)}")


@router.get("/diagnosis/{diagnosis_id}")
async def get_dynamic_diagnosis_result(diagnosis_id: str, db: Session = Depends(get_db)):
    """
    動的診断結果を取得

    - 診断IDから過去の診断結果を取得
    - キャッシュになければDBから取得
    """
    try:
        # キャッシュクリーンアップ
        clean_expired_cache()

        # 1. まずキャッシュから取得
        if diagnosis_id in diagnosis_cache:
            return JSONResponse(
                content=diagnosis_cache[diagnosis_id],
                media_type="application/json; charset=utf-8"
            )

        # 2. キャッシュになければDBから取得
        db_result = get_diagnosis_by_id(db, diagnosis_id)
        if db_result:
            # キャッシュにも保存（次回アクセス高速化）
            diagnosis_cache[diagnosis_id] = db_result
            cache_expiry[diagnosis_id] = datetime.utcnow() + timedelta(hours=24)

            return JSONResponse(
                content=db_result,
                media_type="application/json; charset=utf-8"
            )

        # 3. どちらにもなければ404
        raise HTTPException(status_code=404, detail="診断結果が見つかりません")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"診断結果取得エラー: {str(e)}")


@router.post("/compare")
async def compare_time_periods(request: DynamicDiagnosisRequest):
    """
    異なる時期での構造を比較

    - 半年前、現在、半年後の構造を比較
    - 時期による変化を可視化
    """
    try:
        calc = await get_dynamic_calculator()

        # Answerを変換
        answers = [
            AnswerDataModel(question_id=ans.question_id, choice=ans.choice)
            for ans in request.answers
        ]

        # 3つの時点で診断
        now = datetime.now()
        periods = [
            ("半年前", now - timedelta(days=180)),
            ("現在", now),
            ("半年後", now + timedelta(days=180)),
        ]

        comparisons = []
        for label, date in periods:
            result = await calc.calculate_dynamic_struct_code(
                birth_date=request.birth_date,
                birth_time=request.birth_time,
                birth_location=request.birth_location,
                answers=answers,
                diagnosis_date=date
            )

            comparisons.append({
                "period": label,
                "date": date.isoformat(),
                "current_type": result.current_type,
                "current_sds": result.current_sds,
                "theme": result.current_theme,
            })

        return {
            "natal_type": comparisons[1]["current_type"] if comparisons else None,
            "comparisons": comparisons,
            "analysis": _generate_comparison_analysis(comparisons)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"比較エラー: {str(e)}")


def _generate_comparison_analysis(comparisons: List[Dict]) -> str:
    """比較分析を生成"""
    if len(comparisons) < 3:
        return "比較データが不足しています。"

    past = comparisons[0]
    present = comparisons[1]
    future = comparisons[2]

    axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
    changes = []

    for i, axis in enumerate(axis_names):
        past_val = past['current_sds'][i]
        present_val = present['current_sds'][i]
        future_val = future['current_sds'][i]

        trend = "→"
        if future_val > present_val + 0.05:
            trend = "↑"
        elif future_val < present_val - 0.05:
            trend = "↓"

        if abs(future_val - past_val) > 0.1:
            changes.append(f"{axis}は{trend}傾向")

    if changes:
        return "今後の変化傾向: " + ", ".join(changes)
    else:
        return "全体的に安定した時期です。"


@router.get("/health")
async def health_check():
    """
    ヘルスチェック

    - 動的計算APIの稼働状況を確認
    """
    try:
        calc = await get_dynamic_calculator()
        return {
            "status": "healthy",
            "version": "2.0-dynamic",
            "calculator_initialized": calc is not None,
            "cached_diagnoses": len(diagnosis_cache),
            "timestamp": datetime.utcnow().isoformat(),
            "features": [
                "natal_structure",
                "current_structure",
                "transit_modulation",
                "progressed_modulation",
                "temporal_theme",
                "future_projection"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "version": "2.0-dynamic",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

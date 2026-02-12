# -*- coding: utf-8 -*-
"""
STRUCT CODE v2 API Router
新しい正確な占星術エンジンを使用したAPI
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import hashlib
import time
import logging

from app.services.struct_calculator_refactored import StructCalculatorRefactored
from app.models.schemas import AnswerData as AnswerDataModel
from app.config.database import get_db
from app.services.diagnosis_storage import save_diagnosis_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["STRUCT CODE v2"])

# 計算機のインスタンス（シングルトン）
calculator = None

# 診断結果キャッシュ（24時間保持）
diagnosis_cache: Dict[str, Dict] = {}
cache_expiry: Dict[str, datetime] = {}


async def get_calculator() -> StructCalculatorRefactored:
    """計算機インスタンスを取得（遅延初期化）"""
    global calculator
    if calculator is None:
        calculator = StructCalculatorRefactored()
        await calculator.initialize()
    return calculator


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


class DiagnosisRequest(BaseModel):
    """診断リクエスト"""
    birth_date: str = Field(..., example="1990-01-15", description="生年月日 YYYY-MM-DD")
    birth_location: str = Field(..., example="Tokyo, Japan", description="出生地")
    answers: List[Answer] = Field(..., description="25問の回答")
    birth_time: Optional[str] = Field(None, example="14:30", description="出生時刻（任意）HH:MM")


class DiagnosisResponse(BaseModel):
    """診断レスポンス"""
    diagnosis_id: str
    struct_type: str
    struct_code: str
    type_info: Dict
    confidence: float
    axes: Dict[str, float]
    birth_time_estimated: Dict
    horoscope: Dict
    metadata: Dict




@router.post("/diagnosis")
async def create_diagnosis(request: DiagnosisRequest, db: Session = Depends(get_db)):
    """
    診断を実行

    - 生年月日、出生地、25問の回答から診断を実行
    - STRUCT TYPEとSTRUCT CODEを生成
    """
    try:
        # キャッシュクリーンアップ
        clean_expired_cache()

        # 計算機を取得
        calc = await get_calculator()

        # Answerを AnswerDataModelに変換
        answers = [AnswerDataModel(question_id=ans.question_id, choice=ans.choice) for ans in request.answers]

        # 診断実行
        result = await calc.calculate_struct_code(
            birth_date=request.birth_date,
            birth_location=request.birth_location,
            answers=answers
        )

        # 診断IDを生成
        diagnosis_id = generate_diagnosis_id(
            birth_date=request.birth_date,
            location=request.birth_location,
            timestamp=datetime.utcnow().isoformat()
        )

        # 軸データを抽出
        axes = {}
        if hasattr(result, 'vectors') and isinstance(result.vectors, dict):
            # axesが直接含まれている場合
            if 'axes' in result.vectors:
                axes = result.vectors['axes']
            else:
                for key in ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']:
                    if key in result.vectors:
                        axes[key] = result.vectors[key]

        # struct_typesからarchetype、mission、axis_signatureを取得
        struct_type_info = calc.struct_types.get(result.struct_type, {})

        # horoscopeデータを構築
        horoscope_data = {
            "vectors": result.vectors
        }
        # planetary_positionsからASCとMCを取得
        if hasattr(result, 'vectors') and isinstance(result.vectors, dict):
            planetary_positions = result.vectors.get('planetary_positions', {})
            aspects = result.vectors.get('aspects', [])

            # ASC (Ascendant) - 正しく計算されたアセンダント値を使用
            ascendant = result.vectors.get('ascendant', planetary_positions.get('sun', 0))
            horoscope_data['asc'] = ascendant
            # MC (Medium Coeli) - ASCから90度先
            horoscope_data['mc'] = (ascendant + 90) % 360
            # House positions
            horoscope_data['house_positions'] = result.vectors.get('house_positions', {})
            # アスペクト数
            horoscope_data['aspects_count'] = len(aspects) if isinstance(aspects, list) else 0

        # 出生時間推定データを構築
        birth_time_data = {
            "symbolic_time": result.symbolic_time,
            "symbolic_meaning": result.symbolic_meaning,
            "time": result.symbolic_time,  # フロントエンド用
            "is_estimated": True,
            "confidence": result.similarity_score
        }

        # type_candidatesを取得（vectors内から）
        type_candidates = []
        if hasattr(result, 'vectors') and isinstance(result.vectors, dict):
            type_candidates = result.vectors.get('type_candidates', [])

        # レスポンス構築
        response_data = {
            "diagnosis_id": diagnosis_id,
            "struct_type": result.struct_type,
            "struct_code": result.struct_code,
            "type_info": {
                "code": result.type_detail.code,
                "name": result.type_detail.label,
                "summary": result.type_detail.summary,
                "decision_style": result.type_detail.decision_style,
                "choice_pattern": result.type_detail.choice_pattern,
                "risk_note": result.type_detail.risk_note,
                "relation_hint": result.type_detail.relation_hint,
                "growth_tip": result.type_detail.growth_tip,
                "archetype": struct_type_info.get('archetype', '-'),
                "mission": struct_type_info.get('mission', '-'),
                "axis_signature": struct_type_info.get('axis_signature', {})
            },
            "confidence": result.similarity_score,
            "axes": axes,
            "type_candidates": type_candidates,
            "birth_time_estimated": birth_time_data,
            "horoscope": horoscope_data,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "top_candidates": result.top_candidates
            }
        }

        # キャッシュに保存（24時間）
        diagnosis_cache[diagnosis_id] = response_data
        cache_expiry[diagnosis_id] = datetime.utcnow() + timedelta(hours=24)

        # DB保存（非ブロッキング）
        try:
            natal_result = {
                "struct_type": result.struct_type,
                "struct_code": result.struct_code,
                "similarity_score": result.similarity_score,
                "type_detail": {
                    "label": result.type_detail.label
                },
                "vectors": result.vectors,
                "top_candidates": result.top_candidates
            }
            save_diagnosis_result(
                db=db,
                diagnosis_type="natal",
                birth_date=request.birth_date,
                birth_location=request.birth_location,
                birth_time=request.birth_time,
                natal_result=natal_result,
                answers=answers
            )
        except Exception as e:
            logger.error(f"Failed to save diagnosis result (non-blocking): {e}")

        return response_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"入力エラー: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"診断エラー: {str(e)}")


@router.get("/diagnosis/{diagnosis_id}")
async def get_diagnosis_result(diagnosis_id: str):
    """
    診断結果を取得

    - 診断IDから過去の診断結果を取得
    """
    try:
        # キャッシュクリーンアップ
        clean_expired_cache()

        # キャッシュから取得
        if diagnosis_id not in diagnosis_cache:
            raise HTTPException(status_code=404, detail="診断結果が見つかりません")

        return diagnosis_cache[diagnosis_id]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"診断結果取得エラー: {str(e)}")

@router.get("/types")
async def get_all_types():
    """
    全タイプ一覧を取得

    - 24種類の全タイプの基本情報を取得
    """
    try:
        calc = await get_calculator()
        types = calc.get_all_types()
        return types

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"タイプ一覧取得エラー: {str(e)}")


@router.get("/types/{type_code}")
async def get_type_details(type_code: str):
    """
    特定タイプの詳細情報を取得
    
    - タイプコード（例: ACCP）から詳細情報を取得
    """
    try:
        calc = await get_calculator()
        type_detail = calc.get_type_detail(type_code)
        
        if not type_detail:
            raise HTTPException(
                status_code=404,
                detail=f"タイプ '{type_code}' が見つかりません。"
            )
        
        # TypeDetailオブジェクトを辞書に変換
        return {
            "code": type_detail.code,
            "name": type_detail.label,
            "summary": type_detail.summary,
            "decision_style": type_detail.decision_style,
            "choice_pattern": type_detail.choice_pattern,
            "risk_note": type_detail.risk_note,
            "relation_hint": type_detail.relation_hint,
            "growth_tip": type_detail.growth_tip
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"タイプ取得エラー: {str(e)}")


@router.get("/health")
async def health_check():
    """
    ヘルスチェック
    
    - APIの稼働状況を確認
    - 計算機の初期化状態を確認
    """
    try:
        calc = await get_calculator()
        return {
            "status": "healthy",
            "calculator_initialized": calc is not None,
            "cached_diagnoses": len(diagnosis_cache),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }



"""
Diagnosis Storage Service
DB保存とGoogleスプレッドシート連携を担当
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import numpy as np

logger = logging.getLogger(__name__)


def convert_numpy_types(value):
    """NumPy型をPython標準型に変換"""
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    return value

# Google Sheets設定
SPREADSHEET_ID = "1Nujz-DYImoSx7c774MFl4kcdS9oqbD4_b6QFaM-eFKI"

# 認証ファイルのデフォルトパス
DEFAULT_CREDENTIALS_PATH = r"C:\Users\kazuk\Downloads\struct-code-596f902d2c6f.json"


class GoogleSheetsClient:
    """Google Sheets APIクライアント"""

    def __init__(self):
        self.client = None
        self.sheet = None
        self._initialized = False

    def _init_client(self):
        """遅延初期化"""
        if self._initialized:
            return self.client is not None

        self._initialized = True

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            # 1. 環境変数からJSONパスを取得
            creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", DEFAULT_CREDENTIALS_PATH)

            # 2. 環境変数から直接JSON文字列を取得（従来互換）
            creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

            logger.info(f"Checking credentials: creds_json={'SET' if creds_json else 'NOT SET'}, creds_path={creds_path}")

            if creds_json:
                # JSON文字列から認証
                creds_dict = json.loads(creds_json)
                credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                logger.info("Using credentials from GOOGLE_SHEETS_CREDENTIALS env var")
            elif creds_path and os.path.exists(creds_path):
                # ファイルパスから認証
                credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
                logger.info(f"Using credentials from file: {creds_path}")
            else:
                logger.warning("No Google Sheets credentials found. Sheets sync disabled.")
                logger.warning(f"Set GOOGLE_SHEETS_CREDENTIALS_PATH or place JSON at: {DEFAULT_CREDENTIALS_PATH}")
                return False

            self.client = gspread.authorize(credentials)
            self.sheet = self.client.open_by_key(SPREADSHEET_ID).sheet1
            logger.info("Google Sheets client initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            return False

    def append_row(self, data: Dict[str, Any]) -> bool:
        """スプレッドシートに行を追加"""
        if not self._init_client():
            return False

        try:
            # ヘッダーが存在するか確認、なければ作成
            existing = self.sheet.row_values(1)
            if not existing:
                headers = [
                    "タイムスタンプ",
                    "診断タイプ",
                    "生年月日",
                    "出生地",
                    "出生時刻",
                    "ネイタルタイプ",
                    "ネイタルラベル",
                    "ネイタルコード",
                    "類似度",
                    "起動軸",
                    "判断軸",
                    "選択軸",
                    "共鳴軸",
                    "自覚軸",
                    "カレントタイプ",
                    "カレントラベル",
                    "カレントコード",
                    "C起動軸",
                    "C判断軸",
                    "C選択軸",
                    "C共鳴軸",
                    "C自覚軸",
                    "Gap起動",
                    "Gap判断",
                    "Gap選択",
                    "Gap共鳴",
                    "Gap自覚",
                    "時期テーマ",
                    "セッションID"
                ]
                self.sheet.append_row(headers)

            # データ行を作成
            row = [
                data.get("created_at", datetime.now().isoformat()),
                data.get("diagnosis_type", ""),
                data.get("birth_date", ""),
                data.get("birth_location", ""),
                data.get("birth_time", ""),
                data.get("natal_type_code", ""),
                data.get("natal_type_label", ""),
                data.get("natal_struct_code", ""),
                data.get("natal_similarity_score", ""),
                data.get("natal_activation", ""),
                data.get("natal_judgment", ""),
                data.get("natal_choice", ""),
                data.get("natal_resonance", ""),
                data.get("natal_awareness", ""),
                data.get("current_type_code", ""),
                data.get("current_type_label", ""),
                data.get("current_struct_code", ""),
                data.get("current_activation", ""),
                data.get("current_judgment", ""),
                data.get("current_choice", ""),
                data.get("current_resonance", ""),
                data.get("current_awareness", ""),
                data.get("design_gap_activation", ""),
                data.get("design_gap_judgment", ""),
                data.get("design_gap_choice", ""),
                data.get("design_gap_resonance", ""),
                data.get("design_gap_awareness", ""),
                data.get("period_theme", ""),
                data.get("session_id", "")
            ]

            self.sheet.append_row(row)
            logger.info(f"Successfully appended row to Google Sheets: {data.get('natal_type_code')}")
            return True

        except Exception as e:
            logger.error(f"Failed to append row to Google Sheets: {e}")
            return False


# シングルトンインスタンス
_sheets_client = GoogleSheetsClient()


def save_diagnosis_result(
    db: Session,
    diagnosis_type: str,
    birth_date: str,
    birth_location: str,
    birth_time: Optional[str],
    natal_result: Dict[str, Any],
    current_result: Optional[Dict[str, Any]] = None,
    design_gap: Optional[Dict[str, float]] = None,
    period_theme: Optional[str] = None,
    answers: Optional[list] = None,
    diagnosis_id: Optional[str] = None,
    response_data: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """
    診断結果をDBに保存し、Googleスプレッドシートに同期

    Args:
        db: SQLAlchemyセッション
        diagnosis_type: "natal" or "current"
        birth_date: 生年月日 (YYYY-MM-DD)
        birth_location: 出生地
        birth_time: 出生時刻 (HH:MM) - カレント診断時のみ
        natal_result: ネイタル診断結果
        current_result: カレント診断結果（カレント診断時のみ）
        design_gap: DesignGap（カレント診断時のみ）
        period_theme: 時期テーマ（カレント診断時のみ）
        answers: 質問回答
        diagnosis_id: 診断ID（URL用）
        response_data: APIレスポンスデータ（永続化用）

    Returns:
        保存されたレコードのID、エラー時はNone
    """
    from app.models.diagnosis_result import DiagnosisResult

    try:
        # 5軸スコアを抽出
        natal_scores = natal_result.get("axis_scores", {})
        if not natal_scores and "vectors" in natal_result:
            # vectorsから抽出
            vectors = natal_result["vectors"]
            if isinstance(vectors, dict) and "final_vector" in vectors:
                final = vectors["final_vector"]
                natal_scores = {
                    "activation": int(final[0] * 1000) if len(final) > 0 else 500,
                    "judgment": int(final[1] * 1000) if len(final) > 1 else 500,
                    "choice": int(final[2] * 1000) if len(final) > 2 else 500,
                    "resonance": int(final[3] * 1000) if len(final) > 3 else 500,
                    "awareness": int(final[4] * 1000) if len(final) > 4 else 500,
                }

        # struct_codeからスコアを抽出（フォールバック）
        if not natal_scores:
            struct_code = natal_result.get("struct_code", "")
            parts = struct_code.split("-")
            if len(parts) >= 6:
                natal_scores = {
                    "activation": int(parts[1]),
                    "judgment": int(parts[2]),
                    "choice": int(parts[3]),
                    "resonance": int(parts[4]),
                    "awareness": int(parts[5]),
                }

        # DBレコード作成
        record = DiagnosisResult(
            diagnosis_id=diagnosis_id,
            diagnosis_type=diagnosis_type,
            birth_date=birth_date,
            birth_location=birth_location,
            birth_time=birth_time,
            natal_type_code=natal_result.get("struct_type", ""),
            natal_type_label=natal_result.get("type_detail", {}).get("label", ""),
            natal_struct_code=natal_result.get("struct_code", ""),
            natal_similarity_score=natal_result.get("similarity_score", 0.0),
            natal_activation=natal_scores.get("activation", 500),
            natal_judgment=natal_scores.get("judgment", 500),
            natal_choice=natal_scores.get("choice", 500),
            natal_resonance=natal_scores.get("resonance", 500),
            natal_awareness=natal_scores.get("awareness", 500),
            vectors_json=natal_result.get("vectors"),
            answers_json=[{"question_id": a.question_id, "choice": a.choice} for a in answers] if answers else None,
            top_candidates_json=natal_result.get("top_candidates"),
            response_json=response_data,
        )

        # カレント診断の場合、追加データを設定
        if diagnosis_type == "current" and current_result:
            current_scores = current_result.get("axis_scores", {})
            if not current_scores:
                current_struct = current_result.get("struct_code", "")
                parts = current_struct.split("-")
                if len(parts) >= 6:
                    current_scores = {
                        "activation": int(parts[1]),
                        "judgment": int(parts[2]),
                        "choice": int(parts[3]),
                        "resonance": int(parts[4]),
                        "awareness": int(parts[5]),
                    }

            record.current_type_code = current_result.get("struct_type", "")
            record.current_type_label = current_result.get("type_detail", {}).get("label", "")
            record.current_struct_code = current_result.get("struct_code", "")
            record.current_activation = current_scores.get("activation")
            record.current_judgment = current_scores.get("judgment")
            record.current_choice = current_scores.get("choice")
            record.current_resonance = current_scores.get("resonance")
            record.current_awareness = current_scores.get("awareness")

            if design_gap:
                record.design_gap_activation = convert_numpy_types(design_gap.get("activation"))
                record.design_gap_judgment = convert_numpy_types(design_gap.get("judgment"))
                record.design_gap_choice = convert_numpy_types(design_gap.get("choice"))
                record.design_gap_resonance = convert_numpy_types(design_gap.get("resonance"))
                record.design_gap_awareness = convert_numpy_types(design_gap.get("awareness"))

            record.period_theme = period_theme

        # DB保存
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"Saved diagnosis result to DB: id={record.id}, type={diagnosis_type}")

        # Googleスプレッドシートに同期（非同期的に、エラーでも続行）
        try:
            sheets_data = {
                "created_at": record.created_at.isoformat() if record.created_at else datetime.now().isoformat(),
                "diagnosis_type": diagnosis_type,
                "birth_date": birth_date,
                "birth_location": birth_location,
                "birth_time": birth_time or "",
                "natal_type_code": record.natal_type_code,
                "natal_type_label": record.natal_type_label,
                "natal_struct_code": record.natal_struct_code,
                "natal_similarity_score": record.natal_similarity_score,
                "natal_activation": record.natal_activation,
                "natal_judgment": record.natal_judgment,
                "natal_choice": record.natal_choice,
                "natal_resonance": record.natal_resonance,
                "natal_awareness": record.natal_awareness,
                "current_type_code": record.current_type_code or "",
                "current_type_label": record.current_type_label or "",
                "current_struct_code": record.current_struct_code or "",
                "current_activation": record.current_activation or "",
                "current_judgment": record.current_judgment or "",
                "current_choice": record.current_choice or "",
                "current_resonance": record.current_resonance or "",
                "current_awareness": record.current_awareness or "",
                "design_gap_activation": record.design_gap_activation or "",
                "design_gap_judgment": record.design_gap_judgment or "",
                "design_gap_choice": record.design_gap_choice or "",
                "design_gap_resonance": record.design_gap_resonance or "",
                "design_gap_awareness": record.design_gap_awareness or "",
                "period_theme": record.period_theme or "",
                "session_id": record.session_id,
            }
            _sheets_client.append_row(sheets_data)
        except Exception as e:
            logger.error(f"Failed to sync to Google Sheets (non-blocking): {e}")

        return record.id

    except Exception as e:
        logger.error(f"Failed to save diagnosis result: {e}")
        db.rollback()
        return None


def get_diagnosis_by_id(db: Session, diagnosis_id: str) -> Optional[Dict[str, Any]]:
    """
    診断IDから診断結果を取得

    Args:
        db: SQLAlchemyセッション
        diagnosis_id: 診断ID

    Returns:
        診断結果のAPIレスポンス形式、見つからない場合はNone
    """
    from app.models.diagnosis_result import DiagnosisResult

    try:
        record = db.query(DiagnosisResult).filter(
            DiagnosisResult.diagnosis_id == diagnosis_id
        ).first()

        if not record:
            return None

        # response_jsonが保存されていればそれを返す
        if record.response_json:
            return record.response_json

        # なければ基本情報から再構築（後方互換性）
        return {
            'diagnosis_id': record.diagnosis_id,
            'struct_code': record.natal_struct_code,
            'birth_date': record.birth_date,
            'birth_location': record.birth_location,
            'natal': {
                'type': record.natal_type_code,
                'type_name': record.natal_type_label,
            },
            'current': {
                'type': record.current_type_code,
                'type_name': record.current_type_label,
            } if record.current_type_code else None,
            'top3_types': record.top_candidates_json or [],
        }

    except Exception as e:
        logger.error(f"Failed to get diagnosis by id: {e}")
        return None

"""
DiagnosisResult model for storing diagnosis results
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.config.database import Base
import uuid


class DiagnosisResult(Base):
    """診断結果を保存するテーブル"""
    __tablename__ = "diagnosis_results"

    id = Column(Integer, primary_key=True, index=True)

    # 診断ID（URL用、永続的）
    diagnosis_id = Column(String(12), unique=True, index=True, nullable=True)

    # ユニークID（将来のユーザー紐付け用）
    session_id = Column(String(36), default=lambda: str(uuid.uuid4()), index=True)

    # 入力データ
    birth_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    birth_location = Column(String(255), nullable=False)
    birth_time = Column(String(5), nullable=True)  # HH:MM（カレント診断用）

    # 診断タイプ
    diagnosis_type = Column(String(20), nullable=False)  # "natal" or "current"

    # ネイタル診断結果
    natal_type_code = Column(String(10), nullable=False)  # e.g., "JDPU"
    natal_type_label = Column(String(50), nullable=False)  # e.g., "マーキュリー"
    natal_struct_code = Column(String(50), nullable=False)  # e.g., "JDPU-423-589-352-201-349"
    natal_similarity_score = Column(Float, nullable=False)

    # 5軸スコア（ネイタル）
    natal_activation = Column(Integer, nullable=False)  # 起動軸
    natal_judgment = Column(Integer, nullable=False)    # 判断軸
    natal_choice = Column(Integer, nullable=False)      # 選択軸
    natal_resonance = Column(Integer, nullable=False)   # 共鳴軸
    natal_awareness = Column(Integer, nullable=False)   # 自覚軸

    # カレント診断結果（カレント診断の場合のみ）
    current_type_code = Column(String(10), nullable=True)
    current_type_label = Column(String(50), nullable=True)
    current_struct_code = Column(String(50), nullable=True)

    # 5軸スコア（カレント）
    current_activation = Column(Integer, nullable=True)
    current_judgment = Column(Integer, nullable=True)
    current_choice = Column(Integer, nullable=True)
    current_resonance = Column(Integer, nullable=True)
    current_awareness = Column(Integer, nullable=True)

    # DesignGap（カレント診断の場合のみ）
    design_gap_activation = Column(Float, nullable=True)
    design_gap_judgment = Column(Float, nullable=True)
    design_gap_choice = Column(Float, nullable=True)
    design_gap_resonance = Column(Float, nullable=True)
    design_gap_awareness = Column(Float, nullable=True)

    # 時期テーマ（カレント診断の場合のみ）
    period_theme = Column(Text, nullable=True)

    # ベクトルデータ（JSON形式で保存）
    vectors_json = Column(JSON, nullable=True)

    # 質問回答（JSON形式で保存）
    answers_json = Column(JSON, nullable=True)

    # Top候補（JSON形式で保存）
    top_candidates_json = Column(JSON, nullable=True)

    # 完全なAPIレスポンス（永続化用）
    response_json = Column(JSON, nullable=True)

    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 将来のユーザー紐付け用
    user_id = Column(String(36), nullable=True, index=True)

    def __repr__(self):
        return f"<DiagnosisResult(id={self.id}, type={self.diagnosis_type}, natal={self.natal_type_code}, created={self.created_at})>"

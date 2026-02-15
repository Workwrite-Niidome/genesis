# -*- coding: utf-8 -*-
"""
STRUCT CODE v2.0 - Dynamic Calculator
動的構造計算エンジン：時間軸を持つ構造計算

Features:
- ネイタル構造（生涯の本質）の計算
- 現在構造（時期を反映）の計算
- トランジット/プログレスによる変調
- 時期テーマの生成
- 将来予測
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

from .struct_calculator_refactored import get_struct_calculator
from .astrological_engine import get_astrological_engine, Chart
from .temporal_modulator import get_temporal_modulator, TemporalModulation
from ..models.schemas import AnswerData, DiagnosisResponse
from ..utils.logging_config import logger

# 軸名定数（エンコーディング問題回避）
AXIS_NAMES = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
AXIS_KIDOU = '起動軸'
AXIS_HANDAN = '判断軸'
AXIS_SENTAKU = '選択軸'
AXIS_KYOUMEI = '共鳴軸'
AXIS_JIKAKU = '自覚軸'


@dataclass
class DynamicDiagnosisResult:
    """動的診断結果"""
    # 基本情報
    struct_code: str
    diagnosis_timestamp: str

    # 出生情報（AIプロンプト用）
    birth_date: str
    birth_location: str

    # ネイタル構造（生涯の本質）
    natal_type: str
    natal_type_name: str
    natal_sds: List[float]
    natal_description: str

    # 現在構造（時期を反映）
    current_type: str
    current_type_name: str
    current_sds: List[float]
    current_description: str

    # TOP3タイプ（オブジェクト形式: type, name, archetype, score）
    top3_types: List[Dict[str, Any]]

    # DesignGap（本来と現在の差分）
    design_gap: Dict[str, float]

    # 時期テーマ
    current_theme: str
    theme_description: str
    active_transits: List[Dict]

    # 将来予測
    future_outlook: List[Dict]

    # 従来の結果（後方互換）
    legacy_response: Dict[str, Any]


class DynamicStructCalculator:
    """
    動的STRUCT CODE計算エンジン

    v1.0との違い:
    - 同じ入力でも診断日時により結果が変化
    - ネイタル構造と現在構造を分離して出力
    - 時期テーマと将来予測を追加
    """

    def __init__(self):
        self.static_calculator = get_struct_calculator()
        self.astro_engine = get_astrological_engine()
        self.temporal_modulator = get_temporal_modulator()
        logger.info("DynamicStructCalculator initialized")

    async def calculate_dynamic_struct_code(
        self,
        birth_date: str,
        birth_time: Optional[str],
        birth_location: str,
        answers: List[AnswerData],
        diagnosis_date: datetime = None
    ) -> DynamicDiagnosisResult:
        """
        動的STRUCT CODE診断の実行

        Args:
            birth_date: 生年月日 (YYYY-MM-DD)
            birth_time: 出生時刻 (HH:MM) - オプション
            birth_location: 出生地
            answers: 質問回答リスト
            diagnosis_date: 診断日時（デフォルト: 現在）

        Returns:
            DynamicDiagnosisResult: 動的診断結果
        """
        if diagnosis_date is None:
            diagnosis_date = datetime.now()

        logger.info(f"Starting dynamic diagnosis for {birth_date}, diagnosis_date={diagnosis_date}")

        try:
            # Phase 1: 静的計算（従来のv1.0ロジック）でネイタル構造を取得
            legacy_response = await self.static_calculator.calculate_struct_code(
                birth_date, birth_location, answers
            )

            # ネイタルSDS（従来の結果をネイタルとして扱う）
            # vectors['axes']から軸スコアを取得
            axes_data = legacy_response.vectors.get('axes', {})
            natal_sds = [
                axes_data.get(AXIS_KIDOU, 0.5),
                axes_data.get(AXIS_HANDAN, 0.5),
                axes_data.get(AXIS_SENTAKU, 0.5),
                axes_data.get(AXIS_KYOUMEI, 0.5),
                axes_data.get(AXIS_JIKAKU, 0.5),
            ]
            natal_type = legacy_response.struct_type

            # Phase 2: ネイタルチャートを計算
            natal_chart = self.astro_engine.calculate_natal_chart(
                birth_date, birth_time, birth_location
            )

            # Phase 3: チャートポテンシャル融合 + 時間的変調を計算
            # calculate_full_diagnosisを使用することで:
            # 1. 設問回答 + チャートポテンシャルの融合（enhanced_natal_sds）
            # 2. トランジット/プログレス変調
            # が正しく適用される
            temporal_mod = self.temporal_modulator.calculate_full_diagnosis(
                natal_sds, natal_chart, birth_date, diagnosis_date
            )

            # 融合後のネイタルSDSで更新
            natal_sds = temporal_mod.natal_sds

            # Phase 4: 現在の構造からタイプを再決定
            current_sds_dict = {
                '起動軸': temporal_mod.current_sds[0],
                '判断軸': temporal_mod.current_sds[1],
                '選択軸': temporal_mod.current_sds[2],
                '共鳴軸': temporal_mod.current_sds[3],
                '自覚軸': temporal_mod.current_sds[4],
            }
            current_type, _ = self.static_calculator._determine_struct_type(
                current_sds_dict, {}  # 簡易版：アストロデータなしで判定
            )

            # Phase 5: 将来予測
            future_outlook = self.temporal_modulator.project_future(
                natal_chart, natal_sds, months_ahead=6
            )

            # Phase 6: タイプ名を取得
            natal_type_name = self._get_type_name(natal_type)
            current_type_name = self._get_type_name(current_type)

            # Phase 7: 説明文を生成
            natal_description = self._generate_natal_description(natal_type, natal_sds)
            current_description = self._generate_current_description(
                current_type, temporal_mod.current_sds, temporal_mod.current_theme
            )

            # Phase 8: STRUCT CODE文字列生成
            struct_code = self._generate_struct_code_string(
                natal_type, natal_sds, current_type, temporal_mod.current_sds
            )

            # Phase 9: TOP3タイプ取得（オブジェクト形式で返す）
            if hasattr(self.static_calculator, '_last_type_candidates') and self.static_calculator._last_type_candidates:
                top3_types = self.static_calculator._last_type_candidates[:3]
            else:
                # フォールバック: natal_typeをオブジェクト形式で返す
                top3_types = [{
                    'type': natal_type,
                    'name': natal_type_name,
                    'archetype': '',
                    'score': 1.0
                }]

            # 結果を構築
            result = DynamicDiagnosisResult(
                struct_code=struct_code,
                diagnosis_timestamp=diagnosis_date.isoformat(),

                birth_date=birth_date,
                birth_location=birth_location,

                natal_type=natal_type,
                natal_type_name=natal_type_name,
                natal_sds=natal_sds,
                natal_description=natal_description,

                current_type=current_type,
                current_type_name=current_type_name,
                current_sds=temporal_mod.current_sds,
                current_description=current_description,

                top3_types=top3_types,

                design_gap=temporal_mod.design_gap,

                current_theme=temporal_mod.current_theme,
                theme_description=temporal_mod.theme_description,
                active_transits=temporal_mod.active_transits,

                future_outlook=future_outlook,

                legacy_response=self._convert_legacy_response(legacy_response)
            )

            logger.info(f"Dynamic diagnosis complete: natal={natal_type}, current={current_type}")
            return result

        except Exception as e:
            logger.error(f"Error in dynamic calculation: {e}")
            raise

    def _get_type_name(self, type_code: str) -> str:
        """タイプコードから名前を取得"""
        type_info = self.static_calculator.struct_types.get(type_code, {})
        return type_info.get('name', type_code)

    def _generate_natal_description(self, type_code: str, sds: List[float]) -> str:
        """ネイタル構造の説明文を生成"""
        type_info = self.static_calculator.struct_types.get(type_code, {})
        archetype = type_info.get('archetype', '')
        mission = type_info.get('mission', '')

        # 最も高い軸を特定
        max_idx = np.argmax(sds)
        dominant_axis = AXIS_NAMES[max_idx]

        return (
            f"生涯を通じた本質的な構造です。{archetype}の原型を持ち、"
            f"{dominant_axis}が最も発達しています。{mission}"
        )

    def _generate_current_description(
        self,
        type_code: str,
        sds: List[float],
        theme: str
    ) -> str:
        """現在構造の説明文を生成"""
        return (
            f"現在の時期的影響を反映した構造状態です。"
            f"「{theme}」の時期にあり、この影響が構造に現れています。"
        )

    def _generate_struct_code_string(
        self,
        natal_type: str,
        natal_sds: List[float],
        current_type: str,
        current_sds: List[float]
    ) -> str:
        """STRUCT CODE文字列を生成（カレント診断用）"""
        # カレントベースのコード（カレント診断なのでカレントが主）
        current_scores = '-'.join([f"{int(s * 1000):03d}" for s in current_sds])

        if natal_type == current_type:
            return f"{current_type}-{current_scores}"
        else:
            # カレントタイプが主、ネイタルタイプがカッコ内
            return f"{current_type}({natal_type})-{current_scores}"

    def _convert_legacy_response(self, response: DiagnosisResponse) -> Dict[str, Any]:
        """従来のレスポンスを辞書に変換"""
        # axes から axis_scores を構築
        axes_data = response.vectors.get('axes', {})
        axis_scores = {
            AXIS_KIDOU: int(axes_data.get(AXIS_KIDOU, 0.5) * 1000),
            AXIS_HANDAN: int(axes_data.get(AXIS_HANDAN, 0.5) * 1000),
            AXIS_SENTAKU: int(axes_data.get(AXIS_SENTAKU, 0.5) * 1000),
            AXIS_KYOUMEI: int(axes_data.get(AXIS_KYOUMEI, 0.5) * 1000),
            AXIS_JIKAKU: int(axes_data.get(AXIS_JIKAKU, 0.5) * 1000),
        }

        # type_candidates から top3_types を構築
        type_candidates = response.vectors.get('type_candidates', [])
        top3_types = [c.get('type') for c in type_candidates[:3]] if type_candidates else []

        return {
            'struct_type': response.struct_type,
            'struct_code': response.struct_code,
            'type_detail': {
                'code': response.type_detail.code,
                'label': response.type_detail.label,
                'summary': response.type_detail.summary,
                'decision_style': response.type_detail.decision_style,
                'choice_pattern': response.type_detail.choice_pattern,
                'risk_note': response.type_detail.risk_note,
                'relation_hint': response.type_detail.relation_hint,
                'growth_tip': response.type_detail.growth_tip,
            } if response.type_detail else None,
            'axis_scores': axis_scores,
            'confidence': response.similarity_score,
            'top3_types': top3_types,
            'type_candidates': type_candidates,
        }


# ユーティリティ関数
def convert_to_api_response(result: DynamicDiagnosisResult) -> Dict[str, Any]:
    """DynamicDiagnosisResultをAPI応答形式に変換"""
    return {
        'struct_code': result.struct_code,
        'diagnosis_timestamp': result.diagnosis_timestamp,

        # 出生情報（AIプロンプト用）
        'birth_date': result.birth_date,
        'birth_location': result.birth_location,

        'natal': {
            'type': result.natal_type,
            'type_name': result.natal_type_name,
            'sds': result.natal_sds,
            'sds_display': {
                AXIS_KIDOU: int(result.natal_sds[0] * 1000),
                AXIS_HANDAN: int(result.natal_sds[1] * 1000),
                AXIS_SENTAKU: int(result.natal_sds[2] * 1000),
                AXIS_KYOUMEI: int(result.natal_sds[3] * 1000),
                AXIS_JIKAKU: int(result.natal_sds[4] * 1000),
            },
            'description': result.natal_description,
        },

        'current': {
            'type': result.current_type,
            'type_name': result.current_type_name,
            'sds': result.current_sds,
            'sds_display': {
                AXIS_KIDOU: int(result.current_sds[0] * 1000),
                AXIS_HANDAN: int(result.current_sds[1] * 1000),
                AXIS_SENTAKU: int(result.current_sds[2] * 1000),
                AXIS_KYOUMEI: int(result.current_sds[3] * 1000),
                AXIS_JIKAKU: int(result.current_sds[4] * 1000),
            },
            'description': result.current_description,
        },

        'top3_types': result.top3_types,

        'design_gap': result.design_gap,

        'temporal': {
            'current_theme': result.current_theme,
            'theme_description': result.theme_description,
            'active_transits': result.active_transits[:3],  # 上位3つ
            'future_outlook': result.future_outlook,
        },

        # 後方互換性のため従来の形式も含める
        'legacy': result.legacy_response,
    }


# シングルトンインスタンス
_dynamic_calculator_instance = None

def get_dynamic_calculator() -> DynamicStructCalculator:
    """DynamicStructCalculatorのシングルトンインスタンスを取得"""
    global _dynamic_calculator_instance
    if _dynamic_calculator_instance is None:
        _dynamic_calculator_instance = DynamicStructCalculator()
    return _dynamic_calculator_instance

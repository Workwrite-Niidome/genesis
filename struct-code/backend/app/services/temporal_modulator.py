"""
STRUCT CODE v2.0 - Temporal Modulator
時間的変調エンジン：トランジット/プログレスによる軸への影響を計算

Features:
- トランジットによる軸の一時的変調
- プログレスによる内的成長の反映
- 時期テーマの生成
- 将来予測（6ヶ月〜1年）
- ネイタルポテンシャル計算（サイン＋アスペクト）
- 顕在化率による成長・経験の反映
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np

from .astrological_engine import (
    AstrologicalEngine, Chart, Aspect, PlanetPosition,
    get_astrological_engine
)
from ..utils.logging_config import logger

# 動的タイプ分類器（v3.0統一計算用）- 循環インポート回避のため遅延インポート
_dynamic_classifier = None

def _get_dynamic_classifier():
    """DynamicTypeClassifierの遅延取得（循環インポート回避）"""
    global _dynamic_classifier
    if _dynamic_classifier is None:
        from .dynamic_type_classifier import get_dynamic_classifier
        _dynamic_classifier = get_dynamic_classifier()
    return _dynamic_classifier


# ============================================================
# STRUCT CODE v2.0 独自アルゴリズム
# 「構造共鳴理論」- 西洋占星術を超える精密な構造変調
# ============================================================

# ============================================================
# STRUCT CODE v2.0 深層アルゴリズム
# サイン別・アスペクト別のポテンシャル計算
# ============================================================

# サイン別軸修正値（-100〜+100の範囲、1000段階中の修正値）
# v3.1更新: 自覚軸のプラスバイアスを軽減（平均+29→+5）
# 占星術的根拠:
# - Scorpio/Capricorn: 内省的だが極端な値を緩和
# - Aries/Libra: 外向的・他者志向で自己内省が弱い
# - Sagittarius: 楽観的で深い内省より行動優先
SIGN_AXIS_MODIFIERS = {
    'Aries': {'起動軸': +80, '判断軸': -20, '選択軸': +30, '共鳴軸': -40, '自覚軸': -20},
    'Taurus': {'起動軸': -30, '判断軸': +20, '選択軸': -40, '共鳴軸': +20, '自覚軸': +10},
    'Gemini': {'起動軸': +40, '判断軸': +60, '選択軸': 0, '共鳴軸': +20, '自覚軸': -30},
    'Cancer': {'起動軸': -20, '判断軸': -40, '選択軸': +20, '共鳴軸': +80, '自覚軸': +10},
    'Leo': {'起動軸': +100, '判断軸': 0, '選択軸': +50, '共鳴軸': -30, '自覚軸': +20},
    'Virgo': {'起動軸': 0, '判断軸': +80, '選択軸': -30, '共鳴軸': -20, '自覚軸': +30},
    'Libra': {'起動軸': -10, '判断軸': +40, '選択軸': +60, '共鳴軸': +40, '自覚軸': -20},
    'Scorpio': {'起動軸': +20, '判断軸': +40, '選択軸': +30, '共鳴軸': -20, '自覚軸': +60},
    'Sagittarius': {'起動軸': +60, '判断軸': -20, '選択軸': +80, '共鳴軸': +20, '自覚軸': -30},
    'Capricorn': {'起動軸': +30, '判断軸': +60, '選択軸': -50, '共鳴軸': -40, '自覚軸': +40},
    'Aquarius': {'起動軸': +40, '判断軸': +70, '選択軸': +40, '共鳴軸': -10, '自覚軸': +10},
    'Pisces': {'起動軸': -40, '判断軸': -60, '選択軸': +50, '共鳴軸': +100, '自覚軸': +5},  # Neptune支配で自己境界が曖昧
}

# 天体の重み（ポテンシャル計算時）
PLANET_WEIGHT = {
    'sun': 1.0, 'moon': 0.9, 'mercury': 0.6, 'venus': 0.6, 'mars': 0.7,
    'jupiter': 0.5, 'saturn': 0.6, 'uranus': 0.3, 'neptune': 0.3, 'pluto': 0.4,
    'asc': 0.8, 'mc': 0.5,
}

# アスペクトパターン別の軸修正
# v3.1更新: 自覚軸のプラスバイアス軽減
# - 極端に高い値を緩和（+120→+80, +90→+60等）
# - マイナスパターンを追加（Neptune関連の混乱、Jupiter関連の内省不足）
ASPECT_PATTERNS = {
    ('sun', 'moon', 'conjunction'): {'共鳴軸': +40, '自覚軸': +20},
    ('sun', 'moon', 'opposition'): {'共鳴軸': -20, '自覚軸': +35},
    ('sun', 'mercury', 'conjunction'): {'判断軸': +50, '起動軸': +20},
    ('sun', 'venus', 'conjunction'): {'選択軸': +40, '共鳴軸': +30},
    ('sun', 'mars', 'conjunction'): {'起動軸': +70, '自覚軸': -20},
    ('sun', 'mars', 'square'): {'起動軸': +40, '自覚軸': +20},
    ('sun', 'jupiter', 'conjunction'): {'起動軸': +50, '選択軸': +40},
    ('sun', 'jupiter', 'trine'): {'起動軸': +30, '選択軸': +25},
    ('sun', 'saturn', 'conjunction'): {'自覚軸': +50, '起動軸': -30},
    ('sun', 'saturn', 'square'): {'自覚軸': +40, '起動軸': +20},
    ('sun', 'pluto', 'conjunction'): {'自覚軸': +80, '判断軸': +40},
    ('sun', 'pluto', 'square'): {'自覚軸': +50, '起動軸': +30},
    ('moon', 'venus', 'conjunction'): {'共鳴軸': +50, '選択軸': +30},
    ('moon', 'saturn', 'conjunction'): {'自覚軸': +35, '共鳴軸': -40},
    ('moon', 'neptune', 'conjunction'): {'共鳴軸': +70, '判断軸': -30, '自覚軸': -15},  # 共感力は高いが自己境界が曖昧
    ('moon', 'pluto', 'conjunction'): {'自覚軸': +40, '共鳴軸': +30},
    ('mercury', 'saturn', 'conjunction'): {'判断軸': +60, '自覚軸': +25},
    ('mercury', 'pluto', 'conjunction'): {'判断軸': +90, '自覚軸': +45},
    ('venus', 'neptune', 'conjunction'): {'共鳴軸': +60, '選択軸': +40},
    ('mars', 'saturn', 'conjunction'): {'自覚軸': +45, '起動軸': -20},
    ('mars', 'saturn', 'square'): {'自覚軸': +50, '起動軸': +30},
    ('mars', 'pluto', 'conjunction'): {'起動軸': +70, '自覚軸': +40},
    ('saturn', 'uranus', 'square'): {'判断軸': +40, '自覚軸': +35},
    ('saturn', 'pluto', 'conjunction'): {'自覚軸': +60, '判断軸': +40},
    # v3.1追加: 自覚軸マイナスパターン（Neptune関連: 混乱・自己欺瞞）
    ('moon', 'neptune', 'square'): {'自覚軸': -40, '判断軸': -20},
    ('sun', 'neptune', 'square'): {'自覚軸': -30, '起動軸': -20},
    ('mercury', 'neptune', 'square'): {'自覚軸': -30, '判断軸': -30},
    ('venus', 'neptune', 'square'): {'自覚軸': -20, '選択軸': -15},
    # v3.1追加: Jupiter関連（過度の楽観、内省不足）
    ('jupiter', 'neptune', 'conjunction'): {'自覚軸': -20, '選択軸': +30},
    ('moon', 'jupiter', 'opposition'): {'自覚軸': -20, '共鳴軸': +20},
    ('sun', 'jupiter', 'square'): {'自覚軸': -15, '起動軸': +30},  # 過度の自信、内省不足
}

# 天体の性質定義
PLANET_NATURE = {
    'sun': {'type': 'benefic', 'speed': 'personal', 'weight': 1.0},
    'moon': {'type': 'luminary', 'speed': 'personal', 'weight': 0.8},
    'mercury': {'type': 'neutral', 'speed': 'personal', 'weight': 0.7},
    'venus': {'type': 'benefic', 'speed': 'personal', 'weight': 0.8},
    'mars': {'type': 'malefic', 'speed': 'personal', 'weight': 0.9},
    'jupiter': {'type': 'benefic', 'speed': 'social', 'weight': 1.0},
    'saturn': {'type': 'malefic', 'speed': 'social', 'weight': 1.0},
    'uranus': {'type': 'transpersonal', 'speed': 'generational', 'weight': 0.6},
    'neptune': {'type': 'transpersonal', 'speed': 'generational', 'weight': 0.5},
    'pluto': {'type': 'transpersonal', 'speed': 'generational', 'weight': 0.5},
}

PLANET_RULED_AXES = {
    'sun': {'primary': '起動軸', 'secondary': '自覚軸'},
    'moon': {'primary': '共鳴軸', 'secondary': '判断軸'},
    'mercury': {'primary': '判断軸', 'secondary': '起動軸'},
    'venus': {'primary': '選択軸', 'secondary': '共鳴軸'},
    'mars': {'primary': '起動軸', 'secondary': '判断軸'},
    'jupiter': {'primary': '選択軸', 'secondary': '起動軸'},
    'saturn': {'primary': '自覚軸', 'secondary': '判断軸'},
    'uranus': {'primary': '判断軸', 'secondary': '選択軸'},
    'neptune': {'primary': '共鳴軸', 'secondary': '選択軸'},
    'pluto': {'primary': '自覚軸', 'secondary': '共鳴軸'},
}

# v3.1更新: 自覚軸への影響を調整
# - saturn: +0.5 → +0.4 (依然として高いが緩和)
# - pluto: +0.5 → +0.35 (深層変容だが極端さを緩和)
# - neptune: +0.2 → -0.1 (Neptuneは自覚を曖昧にする側面あり)
PLANET_AXIS_INFLUENCE = {
    'sun': {'起動軸': 0.4, '自覚軸': 0.25, '選択軸': 0.2, '共鳴軸': -0.2},
    'moon': {'共鳴軸': 0.5, '自覚軸': 0.15, '判断軸': -0.3, '起動軸': -0.1},
    'mercury': {'判断軸': 0.5, '起動軸': 0.2, '共鳴軸': -0.2, '選択軸': -0.1},
    'venus': {'選択軸': 0.4, '共鳴軸': 0.3, '起動軸': -0.2, '判断軸': -0.1},
    'mars': {'起動軸': 0.6, '判断軸': -0.2, '共鳴軸': -0.2, '自覚軸': -0.15},
    'jupiter': {'選択軸': 0.4, '起動軸': 0.3, '共鳴軸': 0.2, '自覚軸': -0.3, '判断軸': -0.1},
    'saturn': {'自覚軸': 0.4, '判断軸': 0.4, '起動軸': -0.4, '共鳴軸': -0.2, '選択軸': -0.1},
    'uranus': {'判断軸': 0.3, '起動軸': 0.3, '選択軸': 0.2, '自覚軸': -0.2, '共鳴軸': -0.2},
    'neptune': {'共鳴軸': 0.5, '選択軸': 0.3, '自覚軸': -0.1, '判断軸': -0.4, '起動軸': -0.3},
    'pluto': {'自覚軸': 0.35, '選択軸': 0.2, '起動軸': -0.2, '共鳴軸': -0.2, '判断軸': -0.1},
}

ASPECT_MODIFIERS = {
    'conjunction': {'base': 1.0, 'nature': 'fusion'},
    'opposition': {'base': 0.8, 'nature': 'tension'},
    'square': {'base': 0.7, 'nature': 'challenge'},
    'trine': {'base': 0.6, 'nature': 'harmony'},
    'sextile': {'base': 0.4, 'nature': 'opportunity'},
}

TRANSIT_DURATION = {
    'moon': 2, 'sun': 7, 'mercury': 14, 'venus': 21, 'mars': 30,
    'jupiter': 90, 'saturn': 180, 'uranus': 365, 'neptune': 730, 'pluto': 1095,
}

TRANSIT_THEMES = {
    ('saturn', 'sun', 'conjunction'): {
        'theme': '自己の再定義と責任の時期',
        'description': '土星があなたの太陽に重なっています。自分が本当に何者なのかを問い直す時期です。',
        'axis_modulation': {'起動軸': -0.12, '自覚軸': +0.10},
    },
    ('jupiter', 'sun', 'conjunction'): {
        'theme': '拡大と成長の好機',
        'description': '木星があなたの太陽に重なっています。新しいことを始めるのに最適な時期です。',
        'axis_modulation': {'起動軸': +0.12, '選択軸': +0.08},
    },
    ('pluto', 'sun', 'conjunction'): {
        'theme': '根本的な変容の時期',
        'description': '冥王星があなたの太陽に重なっています。人生で最も深い変容の一つを経験する時期です。',
        'axis_modulation': {'自覚軸': +0.15, '起動軸': -0.08},
    },
}


@dataclass
class TemporalModulation:
    natal_sds: List[float]
    current_sds: List[float]
    modulation_factors: Dict[str, float]
    active_transits: List[Dict]
    current_theme: str
    theme_description: str
    design_gap: Dict[str, float]


@dataclass
class NatalPotential:
    sign_based: Dict[str, float]
    aspect_based: Dict[str, float]
    total: Dict[str, float]
    manifestation_rate: float


class TemporalModulator:
    def __init__(self, engine: AstrologicalEngine = None):
        self.engine = engine or get_astrological_engine()
        logger.info("TemporalModulator initialized")

    def calculate_sign_based_potential(self, natal_chart: Chart) -> Dict[str, float]:
        axis_potential = {'起動軸': 500.0, '判断軸': 500.0, '選択軸': 500.0, '共鳴軸': 500.0, '自覚軸': 500.0}
        total_weight = 0.0
        # natal_chart.planetsは Dict[str, PlanetPosition] なので .items() でイテレート
        for planet_name, planet_pos in natal_chart.planets.items():
            planet_key = planet_name.lower()
            sign = planet_pos.sign
            weight = PLANET_WEIGHT.get(planet_key, 0.3)
            total_weight += weight
            sign_mods = SIGN_AXIS_MODIFIERS.get(sign, {})
            for axis, mod_value in sign_mods.items():
                axis_potential[axis] += mod_value * weight
        if total_weight > 0:
            for axis in axis_potential:
                axis_potential[axis] = 500 + (axis_potential[axis] - 500) / total_weight
        return axis_potential

    def calculate_aspect_based_potential(self, natal_chart: Chart) -> Dict[str, float]:
        axis_potential = {'起動軸': 0.0, '判断軸': 0.0, '選択軸': 0.0, '共鳴軸': 0.0, '自覚軸': 0.0}
        for aspect in natal_chart.aspects:
            planet1, planet2 = aspect.planet1.lower(), aspect.planet2.lower()
            aspect_type = aspect.aspect_type
            pattern_key = (planet1, planet2, aspect_type)
            reverse_key = (planet2, planet1, aspect_type)
            pattern_mods = ASPECT_PATTERNS.get(pattern_key) or ASPECT_PATTERNS.get(reverse_key)
            if pattern_mods:
                strength = aspect.strength if hasattr(aspect, 'strength') else 1.0
                for axis, mod_value in pattern_mods.items():
                    axis_potential[axis] += mod_value * strength
        return axis_potential

    def calculate_manifestation_rate(self, birth_date: str, diagnosis_date: datetime = None) -> float:
        if diagnosis_date is None:
            diagnosis_date = datetime.now()
        birth_year = int(birth_date.split('-')[0])
        birth_month = int(birth_date.split('-')[1])
        birth_day = int(birth_date.split('-')[2])
        birth_dt = datetime(birth_year, birth_month, birth_day)
        age = (diagnosis_date - birth_dt).days / 365.25
        if age < 18:
            rate = 0.40 + (age / 18) * 0.15
        elif age < 30:
            rate = 0.55 + ((age - 18) / 12) * 0.20
        elif age < 45:
            rate = 0.75 + ((age - 30) / 15) * 0.15
        elif age < 60:
            rate = 0.90 + ((age - 45) / 15) * 0.08
        else:
            rate = 0.98 + min((age - 60) / 40, 0.02)
        return min(1.0, max(0.4, rate))

    def calculate_natal_potential(self, natal_chart: Chart, birth_date: str, diagnosis_date: datetime = None) -> NatalPotential:
        sign_potential = self.calculate_sign_based_potential(natal_chart)
        aspect_potential = self.calculate_aspect_based_potential(natal_chart)
        manifestation_rate = self.calculate_manifestation_rate(birth_date, diagnosis_date)
        total_potential = {}
        for axis in sign_potential:
            # sign_potential(500ベース) + aspect_potential(0ベース加算値)
            base = sign_potential[axis] + aspect_potential[axis]
            total_potential[axis] = max(0, min(1000, base))
        return NatalPotential(sign_based=sign_potential, aspect_based=aspect_potential, total=total_potential, manifestation_rate=manifestation_rate)

    def calculate_enhanced_natal_sds(self, questionnaire_sds: List[float], natal_chart: Chart, birth_date: str, diagnosis_date: datetime = None) -> List[float]:
        """
        設問回答とチャートポテンシャルを融合してネイタルSDSを計算

        【STRUCT CODE v3.0 統一アルゴリズム】
        - チャートポテンシャル（70%）: dynamic_type_classifier._calculate_axes_from_chart()を使用
          （Essential Dignity, Accidental Dignity, Node, Chiron, Part of Fortune, Moon Phase, Fixed Stars）
        - 設問回答（30%）: 現在の自己認識（後天的な変化・経験）

        v3.0更新: V2 APIとDynamic APIで同じ占星術計算ロジックを使用
        """
        axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
        enhanced_sds = []

        # v3.0統一: dynamic_type_classifierの精密計算を使用
        try:
            classifier = _get_dynamic_classifier()
            chart_axes = classifier._calculate_axes_from_chart(natal_chart)
        except Exception as e:
            logger.warning(f"Failed to use unified calculation, falling back to legacy: {e}")
            # フォールバック: 旧ロジック（calculate_natal_potential）
            potential = self.calculate_natal_potential(natal_chart, birth_date, diagnosis_date)
            chart_axes = {axis: potential.total[axis] / 1000.0 for axis in axis_names}

        # 重み付け定義: 占星術70% + 設問30%
        CHART_WEIGHT = 0.70
        QUESTIONNAIRE_WEIGHT = 0.30

        for i, axis in enumerate(axis_names):
            q_value = questionnaire_sds[i]
            chart_value = chart_axes.get(axis, 0.5)

            # 融合: 占星術ベース(70%) + 設問補正(30%)
            final_value = chart_value * CHART_WEIGHT + q_value * QUESTIONNAIRE_WEIGHT

            enhanced_sds.append(max(0.0, min(1.0, final_value)))
        return enhanced_sds

    def calculate_transit_modulation(self, natal_chart: Chart, transit_date: datetime = None, natal_sds: List[float] = None) -> Dict[str, float]:
        if transit_date is None:
            transit_date = datetime.now()
        transit_chart = self.engine.calculate_transit_chart(transit_date)
        aspects = self.engine.calculate_transit_to_natal_aspects(transit_chart, natal_chart)
        modulation = {'起動軸': 0.0, '判断軸': 0.0, '選択軸': 0.0, '共鳴軸': 0.0, '自覚軸': 0.0}
        axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
        for aspect in aspects:
            transit_planet = aspect.planet1.replace('(tr/pr)', '').strip()
            natal_planet = aspect.planet2.replace('(n)', '').strip()
            transit_nature = PLANET_NATURE.get(transit_planet, {'type': 'neutral', 'weight': 0.5})
            natal_ruled = PLANET_RULED_AXES.get(natal_planet, {'primary': '起動軸', 'secondary': '判断軸'})
            primary_axis, secondary_axis = natal_ruled['primary'], natal_ruled['secondary']
            aspect_modifier = ASPECT_MODIFIERS.get(aspect.aspect_type, {'base': 0.5, 'nature': 'neutral'})
            direction = 1.0
            if transit_nature['type'] == 'benefic':
                if aspect_modifier['nature'] in ['harmony', 'opportunity']:
                    direction = 0.9
                elif aspect_modifier['nature'] == 'fusion':
                    direction = 0.7
                else:
                    direction = -0.2
            elif transit_nature['type'] == 'malefic':
                if aspect_modifier['nature'] in ['harmony', 'opportunity']:
                    direction = -0.3
                elif aspect_modifier['nature'] == 'fusion':
                    direction = -0.7
                else:
                    direction = -0.9
            elif transit_nature['type'] == 'transpersonal':
                if aspect_modifier['nature'] in ['tension', 'challenge']:
                    direction = -0.6
                elif aspect_modifier['nature'] == 'fusion':
                    direction = -0.3
                else:
                    direction = 0.5
            else:
                if aspect_modifier['nature'] in ['tension', 'challenge']:
                    direction = -0.4
                elif aspect_modifier['nature'] == 'fusion':
                    direction = 0.5
                else:
                    direction = 0.6
            base_strength = aspect.strength * aspect_modifier['base'] * transit_nature['weight']
            if natal_sds is not None:
                primary_idx = axis_names.index(primary_axis)
                secondary_idx = axis_names.index(secondary_axis)
                primary_resonance = 0.5 + natal_sds[primary_idx]
                secondary_resonance = 0.5 + natal_sds[secondary_idx] * 0.5
            else:
                primary_resonance, secondary_resonance = 1.0, 0.75
            # 影響係数を強化：天体の影響をより顕著に
            modulation[primary_axis] += base_strength * direction * primary_resonance * 0.25
            modulation[secondary_axis] += base_strength * direction * secondary_resonance * 0.12
        # 制限を撤廃：天体の影響をそのまま反映
        return modulation

    def calculate_progressed_modulation(self, natal_chart: Chart, target_date: datetime = None, natal_sds: List[float] = None) -> Dict[str, float]:
        if target_date is None:
            target_date = datetime.now()
        progressed_chart = self.engine.calculate_progressed_chart(natal_chart, target_date)
        modulation = {'起動軸': 0.0, '判断軸': 0.0, '選択軸': 0.0, '共鳴軸': 0.0, '自覚軸': 0.0}
        axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
        for aspect in progressed_chart.aspects:
            progressed_planet = aspect.planet1.replace('(tr/pr)', '').strip()
            natal_planet = aspect.planet2.replace('(n)', '').strip()
            natal_ruled = PLANET_RULED_AXES.get(natal_planet, {'primary': '起動軸', 'secondary': '判断軸'})
            aspect_modifier = ASPECT_MODIFIERS.get(aspect.aspect_type, {'base': 0.5, 'nature': 'neutral'})
            direction = -0.3 if aspect_modifier['nature'] in ['tension', 'challenge'] else 0.6
            base_strength = aspect.strength * aspect_modifier['base'] * 0.4
            if natal_sds is not None:
                primary_idx = axis_names.index(natal_ruled['primary'])
                resonance = 0.5 + natal_sds[primary_idx] * 0.5
            else:
                resonance = 0.75
            # プログレスの影響係数を強化
            modulation[natal_ruled['primary']] += base_strength * direction * resonance * 0.20
        # 制限を撤廃：プログレスの影響をそのまま反映
        return modulation

    def get_active_transits(self, natal_chart: Chart, target_date: datetime = None) -> List[Dict[str, Any]]:
        if target_date is None:
            target_date = datetime.now()
        major_transits = self.engine.get_current_major_transits(natal_chart, target_date)
        active = []
        for transit in major_transits:
            if transit['strength'] > 0.3:
                key = (transit['transit_planet'], transit['natal_planet'], transit['aspect'])
                theme_data = TRANSIT_THEMES.get(key, {})
                active.append({**transit, 'theme': theme_data.get('theme', '時期的な影響'), 'description': theme_data.get('description', ''), 'axis_modulation': theme_data.get('axis_modulation', {})})
        return active

    def generate_current_theme(self, active_transits: List[Dict]) -> Tuple[str, str]:
        if not active_transits:
            return "安定した時期", "特に強いトランジットの影響はありません。"
        primary = active_transits[0]
        theme = primary.get('theme', '変化の時期')
        description = primary.get('description', '')
        if len(active_transits) > 1:
            secondary_themes = [t['theme'] for t in active_transits[1:3] if t.get('theme')]
            if secondary_themes:
                description += f"\n\n同時に、{', '.join(secondary_themes)}のテーマも影響しています。"
        return theme, description

    def calculate_temporal_modulation(self, natal_sds: List[float], natal_chart: Chart, diagnosis_date: datetime = None) -> TemporalModulation:
        if diagnosis_date is None:
            diagnosis_date = datetime.now()
        transit_mod = self.calculate_transit_modulation(natal_chart, diagnosis_date, natal_sds)
        progressed_mod = self.calculate_progressed_modulation(natal_chart, diagnosis_date, natal_sds)
        axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
        # 総合変調：制限なしで天体の影響を正確に反映
        total_modulation = {}
        for axis in axis_names:
            total_modulation[axis] = transit_mod.get(axis, 0) + progressed_mod.get(axis, 0)
        current_sds = []
        for i, axis in enumerate(axis_names):
            current_value = max(0.0, min(1.0, natal_sds[i] + total_modulation[axis]))
            current_sds.append(current_value)
        active_transits = self.get_active_transits(natal_chart, diagnosis_date)
        theme, theme_description = self.generate_current_theme(active_transits)
        design_gap = {axis: current_sds[i] - natal_sds[i] for i, axis in enumerate(axis_names)}
        return TemporalModulation(natal_sds=natal_sds, current_sds=current_sds, modulation_factors=total_modulation, active_transits=active_transits, current_theme=theme, theme_description=theme_description, design_gap=design_gap)

    def calculate_full_diagnosis(self, questionnaire_sds: List[float], natal_chart: Chart, birth_date: str, diagnosis_date: datetime = None) -> TemporalModulation:
        if diagnosis_date is None:
            diagnosis_date = datetime.now()
        enhanced_natal_sds = self.calculate_enhanced_natal_sds(questionnaire_sds, natal_chart, birth_date, diagnosis_date)
        return self.calculate_temporal_modulation(enhanced_natal_sds, natal_chart, diagnosis_date)

    def project_future(self, natal_chart: Chart, natal_sds: List[float], months_ahead: int = 6) -> List[Dict[str, Any]]:
        projections = []
        current_date = datetime.now()
        for month in range(1, months_ahead + 1):
            future_date = current_date + timedelta(days=30 * month)
            active_transits = self.get_active_transits(natal_chart, future_date)
            theme, description = self.generate_current_theme(active_transits)
            transit_mod = self.calculate_transit_modulation(natal_chart, future_date)
            projections.append({'period': future_date.strftime('%Y年%m月'), 'theme': theme, 'description': description[:100] + '...' if len(description) > 100 else description, 'dominant_axis_change': max(transit_mod.items(), key=lambda x: abs(x[1]))[0] if transit_mod else None})
        return projections


_modulator_instance = None

def get_temporal_modulator() -> TemporalModulator:
    global _modulator_instance
    if _modulator_instance is None:
        _modulator_instance = TemporalModulator()
    return _modulator_instance

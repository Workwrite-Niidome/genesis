# -*- coding: utf-8 -*-
"""
STRUCT CODE v4.0 - 動的タイプ分類システム

占星術的な時間軸を完全に考慮した、動的なタイプ分類を行う。

【設計思想】
人は生まれた瞬間の天体配置（ネイタル）だけで固定されるのではなく、
その後の星の巡り（トランジット・プログレス）を経て変容していく。
カレント診断は「今、その人がどのような状態にあるか」を、
この時間軸の過程を踏まえて判定する。

【完全実装する占星術要素】
1. ネイタルチャート - 出生時の基本構造
2. プログレスチャート - 内的成長の軌跡（1日=1年）
3. トランジットチャート - 外的環境からの刺激
4. サターンリターン - 約29.5年周期の成熟サイクル
5. ジュピターリターン - 約12年周期の拡張サイクル
6. ノード軸（ドラゴンヘッド/テイル） - 魂の成長方向
7. プログレス月のサイクル - 約27.3年で一周する感情サイクル
8. トランジット×ネイタルのアスペクト - 現在の活性化ポイント
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from .astrological_engine import (
    AstrologicalEngine, get_astrological_engine,
    Chart, PlanetPosition, Aspect, ASPECTS, ALL_ASPECTS, ZODIAC_SIGNS, HouseCusps
)
from ..utils.logging_config import logger


# ============================================================
# 定数定義
# ============================================================

# 惑星の公転周期（年）
PLANETARY_PERIODS = {
    'moon': 27.3 / 365.25,  # 約27.3日
    'sun': 1.0,
    'mercury': 0.24,
    'venus': 0.62,
    'mars': 1.88,
    'jupiter': 11.86,
    'saturn': 29.46,
    'uranus': 84.01,
    'neptune': 164.8,
    'pluto': 248.1,
}

# 惑星と軸の対応関係（影響度付き）
PLANET_AXIS_INFLUENCE = {
    # 起動軸に影響する惑星
    '起動軸': {
        'sun': 0.35, 'mars': 0.30, 'jupiter': 0.15,
        'uranus': 0.10, 'pluto': 0.10
    },
    # 判断軸に影響する惑星
    '判断軸': {
        'mercury': 0.30, 'saturn': 0.30, 'uranus': 0.15,
        'pluto': 0.15, 'sun': 0.10
    },
    # 選択軸に影響する惑星
    '選択軸': {
        'venus': 0.30, 'mars': 0.20, 'jupiter': 0.20,
        'neptune': 0.15, 'moon': 0.15
    },
    # 共鳴軸に影響する惑星
    '共鳴軸': {
        'moon': 0.25, 'venus': 0.25, 'neptune': 0.25,
        'jupiter': 0.15, 'sun': 0.10
    },
    # 自覚軸に影響する惑星
    '自覚軸': {
        'saturn': 0.30, 'pluto': 0.25, 'moon': 0.20,
        'sun': 0.15, 'neptune': 0.10
    },
}

# アスペクトの影響係数（メジャー + マイナー）
ASPECT_INFLUENCE = {
    # メジャーアスペクト
    'conjunction': {'modifier': 1.0, 'nature': 'intensify', 'angle': 0, 'orb': 8},    # 強化
    'opposition': {'modifier': 0.8, 'nature': 'tension', 'angle': 180, 'orb': 8},     # 緊張・気づき
    'trine': {'modifier': 0.6, 'nature': 'flow', 'angle': 120, 'orb': 8},             # 調和・流れ
    'square': {'modifier': 0.7, 'nature': 'challenge', 'angle': 90, 'orb': 7},        # 挑戦・成長
    'sextile': {'modifier': 0.4, 'nature': 'opportunity', 'angle': 60, 'orb': 5},     # 機会
    # マイナーアスペクト（より繊細な影響）
    'quincunx': {'modifier': 0.5, 'nature': 'adjustment', 'angle': 150, 'orb': 3},    # 調整・不協和
    'semisextile': {'modifier': 0.25, 'nature': 'growth', 'angle': 30, 'orb': 2},     # 成長の種
    'semisquare': {'modifier': 0.35, 'nature': 'friction', 'angle': 45, 'orb': 2},    # 摩擦
    'sesquiquadrate': {'modifier': 0.35, 'nature': 'friction', 'angle': 135, 'orb': 2}, # 摩擦
    'quintile': {'modifier': 0.3, 'nature': 'talent', 'angle': 72, 'orb': 2},         # 才能・創造性
    'biquintile': {'modifier': 0.3, 'nature': 'talent', 'angle': 144, 'orb': 2},      # 才能の発現
}

# Combustion（太陽燃焼）の定義
COMBUSTION_ORB = 8.5      # 8.5度以内で燃焼（弱体化）
CAZIMI_ORB = 0.283        # 17分（0.283度）以内でカジミ（超強化）
UNDER_BEAMS_ORB = 17.0    # 17度以内でアンダービームズ（軽度弱体化）

# 惑星クラスター検出の閾値
CLUSTER_ORB = 30.0        # 30度以内で同一クラスター判定

# グランドパターン定義
GRAND_PATTERNS = {
    'grand_trine': {'aspects': ['trine', 'trine', 'trine'], 'planets': 3, 'boost': 0.15},
    'grand_cross': {'aspects': ['square', 'square', 'square', 'square'], 'planets': 4, 'boost': 0.10},
    't_square': {'aspects': ['square', 'square', 'opposition'], 'planets': 3, 'boost': 0.08},
    'yod': {'aspects': ['quincunx', 'quincunx', 'sextile'], 'planets': 3, 'boost': 0.12},
    'kite': {'aspects': ['trine', 'trine', 'sextile', 'opposition'], 'planets': 4, 'boost': 0.10},
    'stellium': {'min_planets': 4, 'max_orb': 10, 'boost': 0.12},  # 4惑星以上が10度以内
}

# ============================================================
# 惑星の品位（Dignity）システム - 西洋占星術の基本原理
# ============================================================
# 惑星がどのサインにあるかで「強さ」が変わる
# - Domicile（本拠地）: 惑星が最も力を発揮するサイン (+5)
# - Exaltation（高揚）: 惑星が高められるサイン (+4)
# - Triplicity（三区分支配）: エレメントの支配 (+3) ※昼夜で異なる
# - Terms/Bounds（デーカン区分）: 度数による区分 (+2)
# - Face/Decan（顔）: 10度区分の支配 (+1)
# - Peregrine（放浪）: どの品位も持たない (-5)
# - Detriment（障害）: 本拠地の反対、力が弱まる (-4)
# - Fall（転落）: 高揚の反対、最も弱い (-5)

# サイン支配星（チャートルーラー計算用）
SIGN_RULERS = {
    'Aries': 'mars', 'Taurus': 'venus', 'Gemini': 'mercury',
    'Cancer': 'moon', 'Leo': 'sun', 'Virgo': 'mercury',
    'Libra': 'venus', 'Scorpio': 'mars', 'Sagittarius': 'jupiter',
    'Capricorn': 'saturn', 'Aquarius': 'saturn', 'Pisces': 'jupiter'
}

# モダン支配星（外惑星を含む）
MODERN_RULERS = {
    'Scorpio': 'pluto', 'Aquarius': 'uranus', 'Pisces': 'neptune'
}

# Triplicity支配星（昼/夜で異なる - 古典的なドロセウス方式）
TRIPLICITY_RULERS = {
    'fire': {'day': 'sun', 'night': 'jupiter', 'participating': 'saturn'},
    'earth': {'day': 'venus', 'night': 'moon', 'participating': 'mars'},
    'air': {'day': 'saturn', 'night': 'mercury', 'participating': 'jupiter'},
    'water': {'day': 'venus', 'night': 'mars', 'participating': 'moon'}
}

# エレメントとサインの対応
ELEMENT_SIGNS = {
    'fire': ['Aries', 'Leo', 'Sagittarius'],
    'earth': ['Taurus', 'Virgo', 'Capricorn'],
    'air': ['Gemini', 'Libra', 'Aquarius'],
    'water': ['Cancer', 'Scorpio', 'Pisces']
}

# Face/Decan支配星（各サインを10度ずつ3分割）
# カルデアン・オーダーに基づく
FACE_RULERS = {
    'Aries': ['mars', 'sun', 'venus'],
    'Taurus': ['mercury', 'moon', 'saturn'],
    'Gemini': ['jupiter', 'mars', 'sun'],
    'Cancer': ['venus', 'mercury', 'moon'],
    'Leo': ['saturn', 'jupiter', 'mars'],
    'Virgo': ['sun', 'venus', 'mercury'],
    'Libra': ['moon', 'saturn', 'jupiter'],
    'Scorpio': ['mars', 'sun', 'venus'],
    'Sagittarius': ['mercury', 'moon', 'saturn'],
    'Capricorn': ['jupiter', 'mars', 'sun'],
    'Aquarius': ['venus', 'mercury', 'moon'],
    'Pisces': ['saturn', 'jupiter', 'mars']
}

# Terms/Bounds（エジプト式） - 各サインを5つの区分に分け、支配惑星を割り当てる
# 形式: サイン: [(終了度数, 支配星), ...]
EGYPTIAN_TERMS = {
    'Aries': [(6, 'jupiter'), (12, 'venus'), (20, 'mercury'), (25, 'mars'), (30, 'saturn')],
    'Taurus': [(8, 'venus'), (14, 'mercury'), (22, 'jupiter'), (27, 'saturn'), (30, 'mars')],
    'Gemini': [(6, 'mercury'), (12, 'jupiter'), (17, 'venus'), (24, 'mars'), (30, 'saturn')],
    'Cancer': [(7, 'mars'), (13, 'venus'), (19, 'mercury'), (26, 'jupiter'), (30, 'saturn')],
    'Leo': [(6, 'jupiter'), (11, 'venus'), (18, 'saturn'), (24, 'mercury'), (30, 'mars')],
    'Virgo': [(7, 'mercury'), (17, 'venus'), (21, 'jupiter'), (28, 'mars'), (30, 'saturn')],
    'Libra': [(6, 'saturn'), (14, 'mercury'), (21, 'jupiter'), (28, 'venus'), (30, 'mars')],
    'Scorpio': [(7, 'mars'), (11, 'venus'), (19, 'mercury'), (24, 'jupiter'), (30, 'saturn')],
    'Sagittarius': [(12, 'jupiter'), (17, 'venus'), (21, 'mercury'), (26, 'saturn'), (30, 'mars')],
    'Capricorn': [(7, 'mercury'), (14, 'jupiter'), (22, 'venus'), (26, 'saturn'), (30, 'mars')],
    'Aquarius': [(7, 'mercury'), (13, 'venus'), (20, 'jupiter'), (25, 'mars'), (30, 'saturn')],
    'Pisces': [(12, 'venus'), (16, 'jupiter'), (19, 'mercury'), (28, 'mars'), (30, 'saturn')]
}

# 惑星の平均日速度（度/日）- 速度判定用
PLANET_AVERAGE_SPEED = {
    'sun': 0.9856,      # 約1度/日
    'moon': 13.176,     # 約13度/日
    'mercury': 1.383,   # 変動が大きい
    'venus': 1.2,       # 変動が大きい
    'mars': 0.524,
    'jupiter': 0.083,
    'saturn': 0.033,
    'uranus': 0.012,
    'neptune': 0.006,
    'pluto': 0.004
}

# 惑星速度の閾値（平均速度に対する比率）
SPEED_THRESHOLDS = {
    'fast': 1.2,    # 平均の120%以上 = 速い
    'slow': 0.8,    # 平均の80%以下 = 遅い
    'stationary': 0.1  # 平均の10%以下 = 停滞（逆行前後）
}

# 重要な恒星（黄経位置 - 2000年エポック、歳差で年約50秒移動）
# 恒星データ（吉凶情報付き）
# influence: 'benefic'(吉), 'malefic'(凶), 'neutral'(中立), 'intense'(激しい/両面)
# 伝統的占星術の恒星解釈に基づく
FIXED_STARS = {
    'Regulus': {
        'longitude': 149.83, 'nature': ['mars', 'jupiter'], 'magnitude': 1.4,
        'influence': 'benefic',  # 王の星、成功と栄光
        'effect': 0.10
    },
    'Spica': {
        'longitude': 203.83, 'nature': ['venus', 'mars'], 'magnitude': 1.0,
        'influence': 'benefic',  # 最も吉星の一つ、才能と幸運
        'effect': 0.12
    },
    'Antares': {
        'longitude': 249.79, 'nature': ['mars', 'jupiter'], 'magnitude': 1.1,
        'influence': 'intense',  # 蠍の心臓、激しさと成功/破滅の両面
        'effect': 0.0  # 品位依存で決定
    },
    'Aldebaran': {
        'longitude': 69.95, 'nature': ['mars'], 'magnitude': 0.9,
        'influence': 'benefic',  # 牡牛の目、成功と富（正直さが条件）
        'effect': 0.08
    },
    'Fomalhaut': {
        'longitude': 333.87, 'nature': ['venus', 'mercury'], 'magnitude': 1.2,
        'influence': 'benefic',  # 四大王星の一つ、理想と成功
        'effect': 0.08
    },
    'Algol': {
        'longitude': 56.17, 'nature': ['saturn', 'jupiter'], 'magnitude': 2.1,
        'influence': 'malefic',  # メデューサの首、最も凶の恒星
        'effect': -0.15
    },
    'Sirius': {
        'longitude': 104.07, 'nature': ['jupiter', 'mars'], 'magnitude': -1.46,
        'influence': 'benefic',  # 最も明るい恒星、栄光と成功
        'effect': 0.12
    },
    'Vega': {
        'longitude': 285.45, 'nature': ['venus', 'mercury'], 'magnitude': 0.0,
        'influence': 'benefic',  # 芸術と魅力
        'effect': 0.08
    },
    'Capella': {
        'longitude': 81.83, 'nature': ['mars', 'mercury'], 'magnitude': 0.1,
        'influence': 'benefic',  # 好奇心と探求
        'effect': 0.06
    },
    'Rigel': {
        'longitude': 78.63, 'nature': ['jupiter', 'saturn'], 'magnitude': 0.2,
        'influence': 'benefic',  # 教育と成功
        'effect': 0.08
    },
    'Procyon': {
        'longitude': 115.62, 'nature': ['mercury', 'mars'], 'magnitude': 0.4,
        'influence': 'neutral',  # 急速な成功だが持続性に欠ける
        'effect': 0.04
    },
    'Betelgeuse': {
        'longitude': 88.79, 'nature': ['mars', 'mercury'], 'magnitude': 0.5,
        'influence': 'benefic',  # 名声と幸運
        'effect': 0.08
    },
    'Altair': {
        'longitude': 301.82, 'nature': ['mars', 'jupiter'], 'magnitude': 0.8,
        'influence': 'benefic',  # 勇気と野心
        'effect': 0.08
    },
    'Deneb': {
        'longitude': 320.02, 'nature': ['venus', 'mercury'], 'magnitude': 1.3,
        'influence': 'benefic',  # 知性と芸術性
        'effect': 0.06
    },
    'Polaris': {
        'longitude': 28.55, 'nature': ['saturn', 'venus'], 'magnitude': 2.0,
        'influence': 'neutral',  # 方向性と安定（良くも悪くもない）
        'effect': 0.04
    },
    'Vindemiatrix': {
        'longitude': 189.79, 'nature': ['saturn', 'mercury'], 'magnitude': 2.8,
        'influence': 'malefic',  # 寡婦の星、喪失
        'effect': -0.08
    },
    'Scheat': {
        'longitude': 359.37, 'nature': ['mars', 'mercury'], 'magnitude': 2.4,
        'influence': 'malefic',  # 災難と不運
        'effect': -0.10
    },
}

# 恒星とのコンジャンクション許容オーブ
FIXED_STAR_ORB = 1.5  # 1.5度以内

# Antiscia（対称点）- 各サインの対称軸（蟹座/獅子座0度を軸とする）
ANTISCIA_PAIRS = {
    'Aries': 'Virgo', 'Virgo': 'Aries',
    'Taurus': 'Leo', 'Leo': 'Taurus',
    'Gemini': 'Cancer', 'Cancer': 'Gemini',
    'Libra': 'Pisces', 'Pisces': 'Libra',
    'Scorpio': 'Aquarius', 'Aquarius': 'Scorpio',
    'Sagittarius': 'Capricorn', 'Capricorn': 'Sagittarius'
}

# Contra-Antiscia（反対称点）- Antisciaの反対側
CONTRA_ANTISCIA_PAIRS = {
    'Aries': 'Pisces', 'Pisces': 'Aries',
    'Taurus': 'Aquarius', 'Aquarius': 'Taurus',
    'Gemini': 'Capricorn', 'Capricorn': 'Gemini',
    'Cancer': 'Sagittarius', 'Sagittarius': 'Cancer',
    'Leo': 'Scorpio', 'Scorpio': 'Leo',
    'Virgo': 'Libra', 'Libra': 'Virgo'
}

# 月相の定義（正負対称：各月相が強める軸と弱める軸を持つ）
# 占星術的根拠：
# - 新月〜上弦：内向き、自己確立期 → 起動・判断↑、共鳴↓
# - 上弦〜満月：外向き、行動拡大期 → 選択・共鳴↑、自覚↓
# - 満月〜下弦：成熟、共有期 → 共鳴・自覚↑、起動↓
# - 下弦〜新月：内省、浄化期 → 自覚↑、判断・選択↓
MOON_PHASES = {
    'new_moon': {
        'range': (0, 45), 'meaning': '始まり・種まき',
        'axis_effect': {'起動': 0.10, '自覚': 0.05, '共鳴': -0.08, '選択': -0.03}
    },
    'crescent': {
        'range': (45, 90), 'meaning': '努力・挑戦',
        'axis_effect': {'起動': 0.08, '判断': 0.05, '共鳴': -0.05, '自覚': -0.03}
    },
    'first_quarter': {
        'range': (90, 135), 'meaning': '行動・決断',
        'axis_effect': {'起動': 0.10, '選択': 0.08, '自覚': -0.08, '共鳴': -0.03}
    },
    'gibbous': {
        'range': (135, 180), 'meaning': '分析・調整',
        'axis_effect': {'判断': 0.10, '選択': 0.05, '自覚': -0.05, '起動': -0.03}
    },
    'full_moon': {
        'range': (180, 225), 'meaning': '実現・完成',
        'axis_effect': {'共鳴': 0.12, '選択': 0.05, '自覚': -0.05, '判断': -0.03}
    },
    'disseminating': {
        'range': (225, 270), 'meaning': '共有・伝達',
        'axis_effect': {'共鳴': 0.10, '自覚': 0.05, '起動': -0.08, '判断': -0.03}
    },
    'last_quarter': {
        'range': (270, 315), 'meaning': '見直し・転換',
        'axis_effect': {'自覚': 0.10, '判断': 0.05, '起動': -0.05, '選択': -0.05}
    },
    'balsamic': {
        'range': (315, 360), 'meaning': '浄化・準備',
        'axis_effect': {'自覚': 0.12, '共鳴': 0.05, '起動': -0.05, '判断': -0.05}
    }
}

# 軸ごとの関連Node効果（正負対称：North/South Nodeは対極の関係）
# 占星術的根拠：
# - North Node（ドラゴンヘッド）：魂の成長方向、未知への挑戦
#   → 外向き（起動・選択）を強め、内向き（自覚・共鳴）を弱める傾向
# - South Node（ドラゴンテイル）：過去世からの蓄積、慣れた領域
#   → 内向き（自覚・共鳴）を強め、外向き（起動・選択）を弱める傾向
NODE_AXIS_EFFECTS = {
    'north_node': {  # ドラゴンヘッド = 成長の方向（未来志向）
        '起動': 0.12, '判断': 0.05, '選択': 0.08, '共鳴': -0.05, '自覚': -0.08
    },
    'south_node': {  # ドラゴンテイル = 過去の蓄積（既知の領域）
        '起動': -0.08, '判断': 0.03, '選択': -0.05, '共鳴': 0.10, '自覚': 0.12
    }
}

# Chiron（キロン）の軸への影響（正負対称：傷と癒しの両面）
# 占星術的根拠：
# - Chironは「傷ついた癒し手」の象徴
# - 外向きの行動（起動・選択）には傷・ためらいとして現れる（マイナス）
# - 内向きの認識（自覚・共鳴）には深い洞察・癒しとして現れる（プラス）
# - 判断は中立（傷を分析的に捉える）
CHIRON_AXIS_EFFECTS = {
    '起動': -0.10,   # 行動への傷・ためらい
    '判断': 0.03,    # 傷を分析する力（中立寄り）
    '選択': -0.05,   # 選択への不安
    '共鳴': 0.12,    # 傷を通じた深い共感
    '自覚': 0.15     # 傷を通じた深い自己認識
}

PLANETARY_DIGNITIES = {
    'sun': {
        'domicile': ['Leo'],
        'exaltation': ['Aries'],
        'detriment': ['Aquarius'],
        'fall': ['Libra']
    },
    'moon': {
        'domicile': ['Cancer'],
        'exaltation': ['Taurus'],
        'detriment': ['Capricorn'],
        'fall': ['Scorpio']
    },
    'mercury': {
        'domicile': ['Gemini', 'Virgo'],
        'exaltation': ['Virgo'],
        'detriment': ['Sagittarius', 'Pisces'],
        'fall': ['Pisces']
    },
    'venus': {
        'domicile': ['Taurus', 'Libra'],
        'exaltation': ['Pisces'],
        'detriment': ['Aries', 'Scorpio'],
        'fall': ['Virgo']
    },
    'mars': {
        'domicile': ['Aries', 'Scorpio'],
        'exaltation': ['Capricorn'],
        'detriment': ['Taurus', 'Libra'],
        'fall': ['Cancer']
    },
    'jupiter': {
        'domicile': ['Sagittarius', 'Pisces'],
        'exaltation': ['Cancer'],
        'detriment': ['Gemini', 'Virgo'],
        'fall': ['Capricorn']
    },
    'saturn': {
        'domicile': ['Capricorn', 'Aquarius'],
        'exaltation': ['Libra'],
        'detriment': ['Cancer', 'Leo'],
        'fall': ['Aries']
    },
    'uranus': {
        'domicile': ['Aquarius'],
        'exaltation': ['Scorpio'],
        'detriment': ['Leo'],
        'fall': ['Taurus']
    },
    'neptune': {
        'domicile': ['Pisces'],
        'exaltation': ['Cancer'],
        'detriment': ['Virgo'],
        'fall': ['Capricorn']
    },
    'pluto': {
        'domicile': ['Scorpio'],
        'exaltation': ['Leo'],
        'detriment': ['Taurus'],
        'fall': ['Aquarius']
    }
}

# 軸ごとの関連ハウス（西洋占星術の理論に基づく）
AXIS_RELATED_HOUSES = {
    '起動': [1, 5, 9],    # 火のハウス: 自己表現、創造性、哲学
    '判断': [3, 6, 10],   # 知性・労働・社会的達成のハウス
    '選択': [2, 7, 11],   # 価値・パートナーシップ・希望のハウス
    '共鳴': [4, 7, 8],    # 家庭・関係性・深い絆のハウス
    '自覚': [8, 12, 4],   # 変容・無意識・内面のハウス
}

# 逆行の軸への影響
RETROGRADE_AXIS_EFFECTS = {
    '起動': -0.25,  # 行動が抑制される
    '判断': 0.10,   # 再考を促す
    '選択': 0.0,    # 中立
    '共鳴': -0.10,  # コミュニケーションの遅れ
    '自覚': 0.30,   # 内省が深まる
}

# タイプグループ（同グループ内の遷移は自然）
TYPE_GROUPS = {
    'AC': ['ACPU', 'ACBL', 'ACCV', 'ACJG', 'ACRN', 'ACCP'],  # 起動軸グループ
    'JD': ['JDPU', 'JDRA', 'JDCP', 'JDCV'],                   # 判断軸グループ
    'CH': ['CHRA', 'CHJA', 'CHAT', 'CHJG', 'CHJC'],           # 選択軸グループ
    'RS': ['RSAW', 'RSCV', 'RSAB', 'RSBL'],                   # 共鳴軸グループ
    'AW': ['AWAB', 'AWRN'],                                    # 認識軸グループ
    'BL': ['BLNC', 'CMPL', 'ADPT'],                           # バランス軸グループ
}

# 24タイプ定義（axis_signature付き）
STRUCT_TYPES = {
    'ACPU': {'name': 'マーズ', 'vector': [0.72, 0.35, 0.35, 0.35, 0.48],
             'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'L', '共鳴': 'L', '自覚': 'M'},
             'group': 'AC', 'primary_axes': ['起動']},
    'ACBL': {'name': 'ソーラー', 'vector': [0.68, 0.52, 0.35, 0.48, 0.38],
             'axis_signature': {'起動': 'H', '判断': 'M', '選択': 'L', '共鳴': 'M', '自覚': 'L'},
             'group': 'AC', 'primary_axes': ['起動']},
    'ACCV': {'name': 'フレア', 'vector': [0.68, 0.35, 0.68, 0.35, 0.48],
             'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'H', '共鳴': 'L', '自覚': 'M'},
             'group': 'AC', 'primary_axes': ['起動', '選択']},
    'ACJG': {'name': 'パルサー', 'vector': [0.66, 0.66, 0.36, 0.36, 0.50],
             'axis_signature': {'起動': 'H', '判断': 'H', '選択': 'L', '共鳴': 'L', '自覚': 'M'},
             'group': 'AC', 'primary_axes': ['起動', '判断']},
    'ACRN': {'name': 'レディエント', 'vector': [0.68, 0.35, 0.50, 0.68, 0.48],
             'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'M', '共鳴': 'H', '自覚': 'M'},
             'group': 'AC', 'primary_axes': ['起動', '共鳴']},
    'ACCP': {'name': 'フォーカス', 'vector': [0.66, 0.66, 0.50, 0.35, 0.68],
             'axis_signature': {'起動': 'H', '判断': 'H', '選択': 'M', '共鳴': 'L', '自覚': 'H'},
             'group': 'AC', 'primary_axes': ['起動', '判断', '自覚']},
    'JDPU': {'name': 'マーキュリー', 'vector': [0.35, 0.72, 0.35, 0.35, 0.50],
             'axis_signature': {'起動': 'L', '判断': 'H', '選択': 'L', '共鳴': 'L', '自覚': 'M'},
             'group': 'JD', 'primary_axes': ['判断']},
    'JDRA': {'name': 'クリスタル', 'vector': [0.35, 0.68, 0.35, 0.48, 0.68],
             'axis_signature': {'起動': 'L', '判断': 'H', '選択': 'L', '共鳴': 'M', '自覚': 'H'},
             'group': 'JD', 'primary_axes': ['判断', '自覚']},
    'JDCP': {'name': 'コスモス', 'vector': [0.50, 0.66, 0.50, 0.50, 0.66],
             'axis_signature': {'起動': 'M', '判断': 'H', '選択': 'M', '共鳴': 'M', '自覚': 'H'},
             'group': 'JD', 'primary_axes': ['判断', '自覚']},
    'JDCV': {'name': 'マトリックス', 'vector': [0.48, 0.68, 0.66, 0.35, 0.68],
             'axis_signature': {'起動': 'M', '判断': 'H', '選択': 'H', '共鳴': 'L', '自覚': 'H'},
             'group': 'JD', 'primary_axes': ['判断', '選択', '自覚']},
    'CHRA': {'name': 'ヴィーナス', 'vector': [0.35, 0.35, 0.72, 0.52, 0.50],
             'axis_signature': {'起動': 'L', '判断': 'L', '選択': 'H', '共鳴': 'M', '自覚': 'M'},
             'group': 'CH', 'primary_axes': ['選択']},
    'CHJA': {'name': 'ディアナ', 'vector': [0.35, 0.48, 0.68, 0.35, 0.68],
             'axis_signature': {'起動': 'L', '判断': 'M', '選択': 'H', '共鳴': 'L', '自覚': 'H'},
             'group': 'CH', 'primary_axes': ['選択', '自覚']},
    'CHAT': {'name': 'ユーレカ', 'vector': [0.66, 0.35, 0.72, 0.48, 0.35],
             'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'H', '共鳴': 'M', '自覚': 'L'},
             'group': 'CH', 'primary_axes': ['起動', '選択']},
    'CHJG': {'name': 'アテナ', 'vector': [0.35, 0.66, 0.68, 0.35, 0.50],
             'axis_signature': {'起動': 'L', '判断': 'H', '選択': 'H', '共鳴': 'L', '自覚': 'M'},
             'group': 'CH', 'primary_axes': ['判断', '選択']},
    'CHJC': {'name': 'オプティマス', 'vector': [0.50, 0.66, 0.68, 0.48, 0.35],
             'axis_signature': {'起動': 'M', '判断': 'H', '選択': 'H', '共鳴': 'M', '自覚': 'L'},
             'group': 'CH', 'primary_axes': ['判断', '選択']},
    'RSAW': {'name': 'ルナ', 'vector': [0.35, 0.35, 0.48, 0.72, 0.68],
             'axis_signature': {'起動': 'L', '判断': 'L', '選択': 'M', '共鳴': 'H', '自覚': 'H'},
             'group': 'RS', 'primary_axes': ['共鳴', '自覚']},
    'RSCV': {'name': 'ミューズ', 'vector': [0.48, 0.35, 0.66, 0.68, 0.50],
             'axis_signature': {'起動': 'M', '判断': 'L', '選択': 'H', '共鳴': 'H', '自覚': 'M'},
             'group': 'RS', 'primary_axes': ['選択', '共鳴']},
    'RSAB': {'name': 'ボンド', 'vector': [0.66, 0.48, 0.48, 0.68, 0.35],
             'axis_signature': {'起動': 'H', '判断': 'M', '選択': 'M', '共鳴': 'H', '自覚': 'L'},
             'group': 'RS', 'primary_axes': ['起動', '共鳴']},
    'RSBL': {'name': 'ハーモニー', 'vector': [0.50, 0.50, 0.50, 0.66, 0.66],
             'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'H', '自覚': 'H'},
             'group': 'RS', 'primary_axes': ['共鳴', '自覚']},
    'AWAB': {'name': 'パノラマ', 'vector': [0.66, 0.50, 0.48, 0.48, 0.68],
             'axis_signature': {'起動': 'H', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'H'},
             'group': 'AW', 'primary_axes': ['起動', '自覚']},
    'AWRN': {'name': 'レーダー', 'vector': [0.48, 0.35, 0.48, 0.66, 0.68],
             'axis_signature': {'起動': 'M', '判断': 'L', '選択': 'M', '共鳴': 'H', '自覚': 'H'},
             'group': 'AW', 'primary_axes': ['共鳴', '自覚']},
    'BLNC': {'name': 'センター', 'vector': [0.50, 0.50, 0.50, 0.50, 0.50],
             'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'M'},
             'group': 'BL', 'primary_axes': []},
    'CMPL': {'name': 'シナジー', 'vector': [0.55, 0.55, 0.55, 0.55, 0.45],
             'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'M'},
             'group': 'BL', 'primary_axes': []},
    'ADPT': {'name': 'カメレオン', 'vector': [0.45, 0.45, 0.55, 0.55, 0.50],
             'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'M'},
             'group': 'BL', 'primary_axes': []},
}

AXIS_ORDER = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
AXIS_ORDER_SHORT = ['起動', '判断', '選択', '共鳴', '自覚']


# ============================================================
# データクラス
# ============================================================

class TransitionState(Enum):
    """タイプ遷移状態"""
    STABLE = "stable"           # 安定（ネイタルタイプに近い）
    TRANSITIONING = "transitioning"  # 遷移中
    TRANSFORMED = "transformed"  # 変容完了（新タイプに定着）


@dataclass
class LifeCycleEvent:
    """人生サイクルイベント"""
    event_type: str          # 'saturn_return', 'jupiter_return', 'progressed_moon_return', etc.
    event_date: datetime     # イベント発生日
    age_at_event: float      # イベント時の年齢
    affected_axes: List[str] # 影響を受ける軸
    influence_strength: float  # 影響の強さ（0-1）
    description: str         # 説明


@dataclass
class TransitInfluence:
    """トランジット影響"""
    transit_planet: str      # トランジット惑星
    natal_planet: str        # ネイタル惑星
    aspect_type: str         # アスペクトタイプ
    affected_axes: List[str] # 影響を受ける軸
    influence_vector: List[float]  # 5軸への影響ベクトル
    strength: float          # 強度
    nature: str              # 'intensify', 'tension', 'flow', 'challenge', 'opportunity'
    is_applying: bool        # 形成中か分離中か


@dataclass
class GrowthVector:
    """成長ベクトル（トランジット過程の累積影響）"""
    vector: List[float]      # 5軸への累積影響
    major_events: List[LifeCycleEvent]  # 主要イベント履歴
    current_phase: str       # 現在のライフフェーズ
    maturity_level: float    # 成熟度（0-1）


@dataclass
class DynamicClassificationResult:
    """動的分類結果"""
    # 基本結果
    natal_type: str          # ネイタルタイプ（基本構造）
    current_type: str        # カレントタイプ（現在の状態）
    confidence: float        # 信頼度

    # 5軸データ
    natal_axes: Dict[str, float]      # ネイタル5軸
    current_axes: Dict[str, float]    # カレント5軸（統合後）
    growth_axes: Dict[str, float]     # 成長による変化分
    transit_axes: Dict[str, float]    # トランジットによる一時的変化
    questionnaire_axes: Dict[str, float]  # 設問回答からの軸

    # 遷移情報
    transition_state: TransitionState  # 遷移状態
    transition_path: List[str]        # 遷移経路（ネイタル→現在）
    potential_next_types: List[str]   # 今後移行する可能性のあるタイプ

    # 占星術データ
    life_cycle_events: List[LifeCycleEvent]  # ライフサイクルイベント
    current_transits: List[TransitInfluence]  # 現在のトランジット
    growth_vector: GrowthVector       # 成長ベクトル

    # 詳細
    natal_chart_summary: Dict[str, Any]  # ネイタルチャートサマリー
    interpretation: str               # 解釈テキスト


# ============================================================
# 動的タイプ分類器
# ============================================================

class DynamicTypeClassifier:
    """
    動的タイプ分類器

    占星術的な時間軸を完全に考慮し、
    ネイタル→トランジット過程→現在トランジット→設問回答
    を統合して動的にタイプを判定する。
    """

    def __init__(self):
        self.astro_engine = get_astrological_engine()
        self.struct_types = STRUCT_TYPES
        logger.info("DynamicTypeClassifier initialized")

    # ========================================
    # Phase 1: ネイタルタイプ確定
    # ========================================

    def calculate_natal_type(
        self,
        birth_date: str,
        birth_time: Optional[str],
        birth_place: str
    ) -> Tuple[str, Dict[str, float], Chart]:
        """
        ネイタルタイプを計算

        Returns:
            (ネイタルタイプ, ネイタル5軸, ネイタルチャート)
        """
        # ネイタルチャート計算
        natal_chart = self.astro_engine.calculate_natal_chart(
            birth_date, birth_time, birth_place
        )

        # ネイタル5軸を計算
        natal_axes = self._calculate_axes_from_chart(natal_chart)

        # ネイタルタイプを判定
        natal_type, _ = self._classify_type(natal_axes)

        logger.info(f"Natal type calculated: {natal_type}")
        return natal_type, natal_axes, natal_chart

    def _calculate_axes_from_chart(self, chart: Chart) -> Dict[str, float]:
        """
        チャートから5軸を計算（完全な西洋占星術システム）

        【計算ロジック v3.0 - 世界最高精度版】

        === 惑星基本スコア (45%) ===
        1. Essential Dignity (25%): Domicile/Exaltation/Triplicity/Terms/Face/Peregrine/Detriment/Fall
        2. Accidental Dignity (12%):
           - ハウス強度 (Angular > Succedent > Cadent)
           - アングル惑星ボーナス (ASC/MC/DC/IC近傍)
           - Combustion (太陽燃焼)
           - 惑星速度 (Fast/Slow/Stationary)
           - Oriental/Occidental
        3. エレメント/クオリティ適合 (8%): 軸との相性

        === 動的修正 (10%) ===
        4. 逆行効果
        5. Sect（昼夜区分）による調整
        6. Mutual Reception

        === パターン認識 (25%) ===
        7. アスペクトパターン
        8. グランドパターン (Grand Trine, T-Square等)
        9. 惑星クラスター（ステリウム）
        10. チャートルーラー影響
        11. 恒星との合

        === 追加ポイント (20%) ===
        12. Node（ドラゴンヘッド/テイル）
        13. Chiron（キロン）
        14. Part of Fortune
        15. 月相
        """
        axes = {}

        # 事前計算
        is_day = chart.is_day_chart if chart.is_day_chart is not None else self._is_day_chart(chart)
        sun_pos = chart.planets.get('sun')

        # 出生年からの経過年数（恒星の歳差補正用）
        years_from_2000 = (chart.datetime.year - 2000) + (chart.datetime.month - 1) / 12

        # チャートルーラーの影響を計算
        ruler_influence = self._get_chart_ruler_influence(chart)

        # グランドパターン検出
        grand_patterns = self._detect_grand_patterns(chart.aspects)

        # 惑星クラスター検出
        clusters = self._detect_planet_clusters(chart.planets)

        # Mutual Reception検出
        mutual_receptions = self._calculate_mutual_reception(chart.planets)

        for axis_name in AXIS_ORDER:
            axis_short = axis_name.replace('軸', '')
            planet_weights = PLANET_AXIS_INFLUENCE.get(axis_name, {})

            # 惑星からの寄与を集計
            planet_contributions = []
            total_weight = 0.0

            for planet_name, weight in planet_weights.items():
                if planet_name in chart.planets:
                    pos = chart.planets[planet_name]

                    # === 1. Essential Dignity (完全版 + Terms) ===
                    dignity_score = self._get_dignity_score(
                        planet_name, pos.sign, pos.sign_degree, is_day
                    )

                    # Terms/Boundsのボーナス
                    terms_ruler = self._get_terms_ruler(pos.sign, pos.sign_degree)
                    if terms_ruler == planet_name:
                        dignity_score = min(1.0, dignity_score + 0.15)  # Termsボーナス

                    dignity_normalized = (dignity_score + 1.0) / 2.0  # -1~1 → 0~1

                    # === 2. Accidental Dignity ===
                    # 2a. ハウス強度
                    house_strength = self._get_house_strength(pos.house, axis_short) if pos.house else 0.5

                    # 2b. アングル惑星ボーナス
                    angular_bonus = self._calculate_angular_bonus(pos, chart.houses)

                    # 2c. Combustion（太陽燃焼）
                    combustion_mod = 0.0
                    if sun_pos:
                        combustion_mod = self._calculate_combustion_modifier(
                            planet_name, pos, sun_pos
                        )

                    # 2d. 惑星速度
                    speed_mod = self._calculate_speed_modifier(planet_name, pos)

                    # 2e. Oriental/Occidental
                    oriental_mod = 0.0
                    if sun_pos and planet_name not in ['sun', 'moon']:
                        is_oriental = self._is_oriental(pos, sun_pos)
                        # 水星・金星はモーニングスター（Oriental）で活発
                        if planet_name in ['mercury', 'venus']:
                            oriental_mod = 0.05 if is_oriental else -0.03
                        else:
                            # 外惑星はOriental（太陽前）で独立的
                            oriental_mod = 0.03 if is_oriental else 0.0

                    # Accidental Dignityの合成
                    accidental = (
                        house_strength * 0.4 +
                        angular_bonus * 0.8 +
                        combustion_mod * 0.3 +
                        speed_mod * 0.2 +
                        oriental_mod
                    )
                    accidental_normalized = max(0.0, min(1.0, 0.5 + accidental))

                    # === 3. エレメント/クオリティ適合 ===
                    element_mod = self._get_element_modifier(pos.element, axis_short)
                    element_normalized = (element_mod - 0.7) / 0.7

                    quality_mod = self._get_quality_modifier(pos.quality, axis_short)
                    quality_normalized = (quality_mod - 0.8) / 0.5

                    elemental = (element_normalized * 0.6 + quality_normalized * 0.4)
                    elemental = max(0.0, min(1.0, elemental))

                    # === 4. 逆行効果 ===
                    retrograde_mod = self._get_retrograde_modifier(planet_name, pos, axis_short)

                    # === 5. Mutual Receptionボーナス ===
                    reception_bonus = 0.0
                    for reception in mutual_receptions:
                        if planet_name in [reception['planet1'], reception['planet2']]:
                            reception_bonus += reception['strength']

                    # === 6. 恒星との合（吉凶対応） ===
                    fixed_star_effect = 0.0
                    star_influence = self._calculate_fixed_star_influence(
                        pos, years_from_2000, dignity_score
                    )
                    if star_influence:
                        # 恒星の効果（吉星は正、凶星は負）
                        fixed_star_effect = star_influence['effect']
                        # 惑星との相性ボーナス（恒星の性質に惑星が含まれる場合）
                        star_natures = star_influence['nature']
                        if planet_name in star_natures:
                            # 相性が良いと効果1.5倍
                            fixed_star_effect *= 1.5

                    # === 重み付き合成（惑星基本値は100%で正規化） ===
                    # 主要要素は0〜1スケール、追加要素は正負の調整
                    planet_value = (
                        dignity_normalized * 0.50 +      # Essential Dignity (主要)
                        accidental_normalized * 0.30 +   # Accidental Dignity
                        elemental * 0.15 +               # エレメント/クオリティ
                        retrograde_mod * 0.05 +          # 逆行（0〜1スケール）
                        reception_bonus * 0.10 +         # Mutual Reception（0〜の加算）
                        fixed_star_effect               # Fixed Stars（正負の効果、既にスケール済み）
                    )
                    # planet_valueは0-1のスケール、この後さらに他の要素で調整

                    # 惑星の重みを適用
                    planet_contributions.append(planet_value * weight)
                    total_weight += weight

            # 惑星寄与の集計（重み正規化）
            if total_weight > 0:
                base_axis_value = sum(planet_contributions) / total_weight
            else:
                base_axis_value = 0.5

            # === 6. アスペクトパターンからの影響 ===
            aspect_influence = self._calculate_enhanced_aspect_influence(
                chart.aspects, axis_short, chart.planets
            )

            # === 7. グランドパターンの影響（品位依存） ===
            pattern_boost = 0.0
            for pattern in grand_patterns:
                # パターンに含まれる惑星が軸に関連しているかチェック
                pattern_planets = set(pattern['planets'])
                axis_planets = set(planet_weights.keys())
                if pattern_planets & axis_planets:
                    # パターン構成惑星の平均品位を計算
                    pattern_dignities = []
                    for p_name in pattern['planets']:
                        if p_name in chart.planets:
                            p_pos = chart.planets[p_name]
                            dignity = self._get_dignity_score(p_name, p_pos.sign, p_pos.sign_degree, is_day)
                            pattern_dignities.append(dignity)

                    if pattern_dignities:
                        avg_dignity = sum(pattern_dignities) / len(pattern_dignities)
                    else:
                        avg_dignity = 0.0

                    base_boost = pattern['boost']
                    pattern_type = pattern.get('type', '')

                    if pattern_type == 'grand_trine':
                        # Grand Trine: 品位が良いほど効果大、悪くても0（マイナスにはしない）
                        # avg_dignity: -1〜+1 → 係数: 0.3〜1.0
                        dignity_factor = 0.65 + avg_dignity * 0.35
                        pattern_boost += base_boost * max(0.3, dignity_factor)
                    elif pattern_type == 't_square':
                        # T-Square: 品位が良いと成長のエンジン、悪いと障害
                        # avg_dignity: -1〜+1 → 係数: -0.5〜+1.0
                        dignity_factor = 0.25 + avg_dignity * 0.75
                        pattern_boost += base_boost * dignity_factor
                    else:
                        # その他のパターン
                        pattern_boost += base_boost

            # === 8. クラスターの影響 ===
            cluster_influence = 0.0
            for cluster in clusters:
                cluster_planets = set(cluster['planets'])
                axis_planets = set(planet_weights.keys())
                overlap = cluster_planets & axis_planets
                if overlap:
                    # クラスターのエレメントが軸と相性が良いか
                    element_match = self._get_element_modifier(cluster['element'], axis_short)
                    cluster_influence += cluster['strength'] * (element_match - 0.9)

            # === 9. チャートルーラー影響 ===
            ruler_mod = ruler_influence.get(axis_name, 0.0)

            # === 10. Node（ドラゴンヘッド/テイル）の影響 ===
            node_influence = self._calculate_node_influence(chart, axis_short)

            # === 11. Chiron（キロン）の影響 ===
            chiron_influence = self._calculate_chiron_influence(chart, axis_short)

            # === 12. Part of Fortuneの影響 ===
            pof_influence = self._calculate_part_of_fortune_influence(chart, axis_short)

            # === 13. 月相の影響 ===
            moon_phase_influence = self._calculate_moon_phase_influence(chart, axis_short)

            # === 最終値の計算 ===
            # 設計思想: base_axis_valueが主軸、追加要素は正負の調整として加算
            # 全ての要素が正負対称なので、0.5を中心とした自然な分布になる

            # 追加要素の合計（正負対称な調整値）
            additional_influence = (
                aspect_influence * 0.20 +           # アスペクト（-0.5〜+0.5）
                (pattern_boost + cluster_influence) * 0.15 +  # パターン
                ruler_mod * 0.10 +                  # チャートルーラー
                node_influence * 0.15 +             # Node（正負対称）
                chiron_influence * 0.10 +           # Chiron（正負対称）
                pof_influence * 0.10 +              # Part of Fortune（正負対称）
                moon_phase_influence * 0.15         # 月相（正負対称）
            )

            # base_axis_value (0〜1) + 追加影響 (正負の調整)
            # base_axis_valueの中央は約0.5、追加影響は正負対称
            final_value = base_axis_value + additional_influence

            # 分散を広げるための非線形変換
            final_value = self._apply_sigmoid_transform(final_value)

            # 0-1にクリップ
            axes[axis_name] = max(0.0, min(1.0, final_value))

        return axes

    def _get_dignity_score(self, planet_name: str, sign: str,
                           sign_degree: float = 15.0, is_day_chart: bool = True) -> float:
        """
        惑星の品位スコアを取得（完全な古典的品位システム）

        Essential Dignityポイントシステム:
        - Domicile: +5
        - Exaltation: +4
        - Triplicity: +3
        - Face/Decan: +1
        - Detriment: -4
        - Fall: -5
        - Peregrine（どの品位も持たない）: -5

        Returns:
            float: -1.0 (最弱) ~ +1.0 (最強) にスケール
        """
        if planet_name not in PLANETARY_DIGNITIES:
            return 0.0

        dignity = PLANETARY_DIGNITIES[planet_name]
        total_points = 0
        has_any_dignity = False

        # Essential Dignities (加算)
        if sign in dignity.get('domicile', []):
            total_points += 5
            has_any_dignity = True

        if sign in dignity.get('exaltation', []):
            total_points += 4
            has_any_dignity = True

        # Triplicity（昼/夜で支配星が異なる）
        element = self._get_element_for_sign(sign)
        if element and element in TRIPLICITY_RULERS:
            triplicity = TRIPLICITY_RULERS[element]
            day_ruler = triplicity.get('day')
            night_ruler = triplicity.get('night')
            participating = triplicity.get('participating')

            if is_day_chart and planet_name == day_ruler:
                total_points += 3
                has_any_dignity = True
            elif not is_day_chart and planet_name == night_ruler:
                total_points += 3
                has_any_dignity = True
            elif planet_name == participating:
                total_points += 1  # 参加支配星は弱いボーナス
                has_any_dignity = True

        # Face/Decan（10度ずつの区分）
        if sign in FACE_RULERS:
            face_index = min(2, int(sign_degree / 10))
            face_ruler = FACE_RULERS[sign][face_index]
            if planet_name == face_ruler:
                total_points += 1
                has_any_dignity = True

        # Essential Debilities (減算)
        if sign in dignity.get('detriment', []):
            total_points -= 4

        if sign in dignity.get('fall', []):
            total_points -= 5

        # Peregrine判定（どの品位も持たない場合はペナルティ）
        if not has_any_dignity and total_points >= 0:
            total_points = -5  # Peregrineは弱い

        # -9 ~ +9 の範囲を -1.0 ~ +1.0 にスケール
        # 実際の範囲は約 -9 (Fall + Detriment) ~ +9 (Domicile + Exaltation + Triplicity)
        normalized = max(-1.0, min(1.0, total_points / 9.0))

        return normalized

    def _get_element_for_sign(self, sign: str) -> Optional[str]:
        """サインからエレメントを取得"""
        for element, signs in ELEMENT_SIGNS.items():
            if sign in signs:
                return element
        return None

    def _is_day_chart(self, chart: 'Chart') -> bool:
        """昼のチャートかどうかを判定（Sect判定）"""
        if 'sun' not in chart.planets:
            return True  # デフォルトは昼

        sun = chart.planets['sun']

        # ハウス情報がある場合はハウスで判定
        if sun.house:
            # 7-12ハウスは地平線上（昼）
            return sun.house >= 7

        # ハウス情報がない場合は太陽の黄経で大まかに判定
        # ASCがある場合
        if chart.houses:
            asc = chart.houses.asc
            sun_lon = sun.longitude

            # 太陽がASCからDSCの間（地平線上）にあるか
            dc = (asc + 180) % 360
            if asc < dc:
                return asc <= sun_lon <= dc
            else:
                return sun_lon >= asc or sun_lon <= dc

        return True  # デフォルト

    def _calculate_combustion_modifier(self, planet_name: str,
                                        planet_pos: 'PlanetPosition',
                                        sun_pos: 'PlanetPosition') -> float:
        """
        太陽燃焼（Combustion）による修正を計算

        - Cazimi (0.283度以内): 超強化 +0.3
        - Combustion (8.5度以内): 弱体化 -0.25
        - Under the Beams (17度以内): 軽度弱体化 -0.10

        Returns:
            float: -0.25 ~ +0.3
        """
        # 太陽自身と月は燃焼しない
        if planet_name in ['sun', 'moon']:
            return 0.0

        # 太陽との角度差
        diff = abs(planet_pos.longitude - sun_pos.longitude)
        if diff > 180:
            diff = 360 - diff

        if diff <= CAZIMI_ORB:
            return 0.30  # Cazimi: 太陽の中心にいる = 超強化
        elif diff <= COMBUSTION_ORB:
            return -0.25  # Combustion: 焼かれている = 弱体化
        elif diff <= UNDER_BEAMS_ORB:
            return -0.10  # Under the Beams: 光に隠れている = 軽度弱体化

        return 0.0

    def _calculate_angular_bonus(self, planet_pos: 'PlanetPosition',
                                  houses: Optional['HouseCusps']) -> float:
        """
        アングル惑星（ASC/MC/DC/IC付近）のボーナスを計算

        惑星がアングル（1, 4, 7, 10ハウスのカスプ）に近いほど強力

        Returns:
            float: 0.0 ~ 0.25
        """
        if not houses:
            return 0.0

        angles = [
            houses.asc,   # ASC (1ハウスカスプ)
            houses.ic,    # IC (4ハウスカスプ)
            houses.dc,    # DC (7ハウスカスプ)
            houses.mc     # MC (10ハウスカスプ)
        ]

        planet_lon = planet_pos.longitude

        # 各アングルとの距離を計算
        min_distance = 360
        for angle in angles:
            diff = abs(planet_lon - angle)
            if diff > 180:
                diff = 360 - diff
            min_distance = min(min_distance, diff)

        # 10度以内でボーナス（近いほど強い）
        if min_distance <= 10:
            return 0.25 * (1 - min_distance / 10)

        return 0.0

    def _get_chart_ruler_influence(self, chart: 'Chart') -> Dict[str, float]:
        """
        チャートルーラー（ASC支配星）の影響を計算

        ASCサインの支配星が強い場合、その惑星に関連する軸が強化される

        Returns:
            Dict[str, float]: 各軸への追加影響
        """
        if not chart.houses:
            return {axis: 0.0 for axis in AXIS_ORDER}

        asc = chart.houses.asc
        asc_sign_index = int(asc / 30) % 12
        asc_sign = ZODIAC_SIGNS[asc_sign_index]

        # 伝統的支配星
        ruler = SIGN_RULERS.get(asc_sign)
        # モダン支配星（該当する場合）
        modern_ruler = MODERN_RULERS.get(asc_sign)

        ruler_influence = {axis: 0.0 for axis in AXIS_ORDER}

        if ruler and ruler in chart.planets:
            ruler_pos = chart.planets[ruler]
            is_day = self._is_day_chart(chart)

            # ルーラーの品位を取得
            ruler_dignity = self._get_dignity_score(
                ruler, ruler_pos.sign, ruler_pos.sign_degree, is_day
            )

            # ルーラーが関与する軸を特定し、品位に応じてボーナス/ペナルティ
            for axis_name, planets in PLANET_AXIS_INFLUENCE.items():
                if ruler in planets:
                    # ルーラーが強いと軸も強化、弱いと軸も弱化
                    ruler_influence[axis_name] = ruler_dignity * 0.15

        return ruler_influence

    def _detect_planet_clusters(self, planets: Dict[str, 'PlanetPosition']) -> List[Dict]:
        """
        惑星クラスター（ステリウム等）を検出

        30度以内に3つ以上の惑星が集中している場合を検出

        Returns:
            List[Dict]: 検出されたクラスターのリスト
        """
        clusters = []
        planet_list = list(planets.items())

        for i, (p1_name, p1_pos) in enumerate(planet_list):
            cluster_planets = [p1_name]
            cluster_center = p1_pos.longitude

            for j, (p2_name, p2_pos) in enumerate(planet_list):
                if i == j:
                    continue

                diff = abs(p1_pos.longitude - p2_pos.longitude)
                if diff > 180:
                    diff = 360 - diff

                if diff <= CLUSTER_ORB:
                    cluster_planets.append(p2_name)

            # 3惑星以上のクラスター
            if len(cluster_planets) >= 3:
                # 既存のクラスターと重複チェック
                is_duplicate = False
                for existing in clusters:
                    overlap = set(cluster_planets) & set(existing['planets'])
                    if len(overlap) >= 2:
                        # 重複が多い場合は大きい方を残す
                        if len(cluster_planets) > len(existing['planets']):
                            existing['planets'] = list(set(cluster_planets))
                        is_duplicate = True
                        break

                if not is_duplicate:
                    # クラスターのサインを特定
                    cluster_sign = p1_pos.sign
                    clusters.append({
                        'planets': list(set(cluster_planets)),
                        'sign': cluster_sign,
                        'element': p1_pos.element,
                        'strength': len(cluster_planets) * 0.05
                    })

        return clusters

    def _detect_grand_patterns(self, aspects: List['Aspect']) -> List[Dict]:
        """
        グランドパターン（Grand Trine, T-Square, Yod等）を検出

        Returns:
            List[Dict]: 検出されたパターンのリスト
        """
        patterns = []

        # Grand Trine検出（3つのトライン）
        trines = [a for a in aspects if a.aspect_type == 'trine']
        if len(trines) >= 3:
            # 3つのトラインが三角形を形成するか確認
            for i, t1 in enumerate(trines):
                for j, t2 in enumerate(trines[i+1:], i+1):
                    for t3 in trines[j+1:]:
                        planets = set([t1.planet1, t1.planet2, t2.planet1, t2.planet2,
                                       t3.planet1, t3.planet2])
                        if len(planets) == 3:
                            patterns.append({
                                'type': 'grand_trine',
                                'planets': list(planets),
                                'boost': GRAND_PATTERNS['grand_trine']['boost']
                            })

        # T-Square検出（2つのスクエアと1つのオポジション）
        squares = [a for a in aspects if a.aspect_type == 'square']
        oppositions = [a for a in aspects if a.aspect_type == 'opposition']

        for opp in oppositions:
            opp_planets = {opp.planet1, opp.planet2}
            for sq1 in squares:
                sq1_planets = {sq1.planet1, sq1.planet2}
                if len(opp_planets & sq1_planets) == 1:
                    apex = (sq1_planets - opp_planets).pop() if sq1_planets - opp_planets else None
                    if apex:
                        for sq2 in squares:
                            sq2_planets = {sq2.planet1, sq2.planet2}
                            if apex in sq2_planets and len(opp_planets & sq2_planets) == 1:
                                all_planets = opp_planets | {apex}
                                if len(all_planets) == 3:
                                    patterns.append({
                                        'type': 't_square',
                                        'planets': list(all_planets),
                                        'apex': apex,
                                        'boost': GRAND_PATTERNS['t_square']['boost']
                                    })

        return patterns

    def _get_terms_ruler(self, sign: str, degree: float) -> Optional[str]:
        """
        Terms/Bounds（エジプト式）の支配星を取得

        Args:
            sign: サイン名
            degree: サイン内度数

        Returns:
            支配惑星名 or None
        """
        if sign not in EGYPTIAN_TERMS:
            return None

        for end_degree, ruler in EGYPTIAN_TERMS[sign]:
            if degree < end_degree:
                return ruler
        return None

    def _calculate_speed_modifier(self, planet_name: str,
                                   planet_pos: 'PlanetPosition') -> float:
        """
        惑星速度による修正を計算

        速い = 活発 (+0.1)
        遅い = 慎重 (-0.05)
        停滞 = 内省的 (+0.05 for 自覚, -0.1 for others)

        Returns:
            float: -0.15 ~ +0.15
        """
        if planet_pos.speed is None:
            return 0.0

        avg_speed = PLANET_AVERAGE_SPEED.get(planet_name, 1.0)
        speed_status = planet_pos.get_speed_status(avg_speed)

        if speed_status == 'fast':
            return 0.10
        elif speed_status == 'slow':
            return -0.05
        elif speed_status == 'stationary':
            return 0.0  # 軸ごとに別途処理
        return 0.0

    def _is_oriental(self, planet_pos: 'PlanetPosition',
                     sun_pos: 'PlanetPosition') -> bool:
        """
        惑星が太陽より東（Oriental）かどうかを判定

        Oriental: 日の出前に昇る（太陽より黄経が小さい方向）
        水星・金星: Oriental = モーニングスター（活発）
        その他: Oriental = より独立的
        """
        diff = planet_pos.longitude - sun_pos.longitude
        if diff < -180:
            diff += 360
        elif diff > 180:
            diff -= 360

        # 0-180: Occidental（太陽の後）
        # -180-0: Oriental（太陽の前）
        return diff < 0

    def _calculate_mutual_reception(self, planets: Dict[str, 'PlanetPosition']) -> List[Dict]:
        """
        Mutual Reception（相互レセプション）を検出

        2つの惑星が互いのサインにいる場合、両方とも強化される

        Returns:
            List[Dict]: 検出されたMutual Receptionのリスト
        """
        receptions = []

        for p1_name, p1_pos in planets.items():
            for p2_name, p2_pos in planets.items():
                if p1_name >= p2_name:  # 重複を避ける
                    continue

                # p1のサインの支配星がp2で、p2のサインの支配星がp1
                p1_ruler = SIGN_RULERS.get(p1_pos.sign)
                p2_ruler = SIGN_RULERS.get(p2_pos.sign)

                if p1_ruler == p2_name and p2_ruler == p1_name:
                    receptions.append({
                        'planet1': p1_name,
                        'planet2': p2_name,
                        'sign1': p1_pos.sign,
                        'sign2': p2_pos.sign,
                        'strength': 0.15  # 強いボーナス
                    })

        return receptions

    def _calculate_fixed_star_influence(self, planet_pos: 'PlanetPosition',
                                         years_from_2000: float = 0,
                                         planet_dignity: float = 0.0) -> Optional[Dict]:
        """
        恒星との合を検出（吉凶情報付き）

        Args:
            planet_pos: 惑星位置
            years_from_2000: 2000年からの経過年数（歳差補正用）
            planet_dignity: 惑星の品位スコア（intense恒星の判定用）

        Returns:
            恒星との合がある場合はDict（effect値含む）、なければNone
        """
        # 歳差補正（年約50秒 = 0.0139度）
        precession = years_from_2000 * 0.0139

        for star_name, star_info in FIXED_STARS.items():
            star_lon = (star_info['longitude'] + precession) % 360

            diff = abs(planet_pos.longitude - star_lon)
            if diff > 180:
                diff = 360 - diff

            if diff <= FIXED_STAR_ORB:
                influence_type = star_info.get('influence', 'neutral')
                base_effect = star_info.get('effect', 0.0)

                # オーブによる減衰（近いほど効果大）
                orb_factor = 1 - (diff / FIXED_STAR_ORB)

                # intenseタイプ（Antaresなど）は惑星品位で正負が決まる
                if influence_type == 'intense':
                    # 品位が良いと成功、悪いと破滅
                    effect = planet_dignity * 0.10 * orb_factor
                else:
                    effect = base_effect * orb_factor

                return {
                    'star': star_name,
                    'nature': star_info['nature'],
                    'magnitude': star_info['magnitude'],
                    'influence': influence_type,
                    'effect': effect,
                    'orb': diff
                }

        return None

    def _calculate_antiscia_point(self, longitude: float) -> float:
        """
        Antiscia（対称点）を計算

        Cancer 0 / Leo 0 の軸（黄経90度/270度の軸）に対する対称点
        """
        # 対称軸は黄経90度（Cancer 0度）
        # 対称点 = 180 - longitude （の後0-360に調整）
        antiscia = (180 - longitude) % 360
        return antiscia

    def _calculate_node_influence(self, chart: 'Chart', axis: str) -> float:
        """
        Node（ドラゴンヘッド/テイル）の軸への影響を計算

        Args:
            chart: チャート
            axis: 軸名（'起動', '判断', etc.）

        Returns:
            float: -0.10 ~ +0.20
        """
        influence = 0.0

        # North Node
        if chart.north_node:
            node_house = chart.north_node.house
            if node_house:
                axis_houses = AXIS_RELATED_HOUSES.get(axis, [])
                if node_house in axis_houses:
                    influence += NODE_AXIS_EFFECTS['north_node'].get(axis, 0.0)

        # South Node
        if chart.south_node:
            node_house = chart.south_node.house
            if node_house:
                axis_houses = AXIS_RELATED_HOUSES.get(axis, [])
                if node_house in axis_houses:
                    influence += NODE_AXIS_EFFECTS['south_node'].get(axis, 0.0)

        return influence

    def _calculate_chiron_influence(self, chart: 'Chart', axis: str) -> float:
        """
        Chiron（キロン）の軸への影響を計算

        傷と癒しの小惑星。自覚軸と共鳴軸に特に影響。

        Returns:
            float: -0.05 ~ +0.20
        """
        if not chart.chiron:
            return 0.0

        chiron_house = chart.chiron.house
        if not chiron_house:
            return 0.0

        # キロンが軸関連ハウスにいる場合に影響
        axis_houses = AXIS_RELATED_HOUSES.get(axis, [])
        if chiron_house in axis_houses:
            return CHIRON_AXIS_EFFECTS.get(axis, 0.0)

        return 0.0

    def _calculate_moon_phase_influence(self, chart: 'Chart', axis: str) -> float:
        """
        月相の軸への影響を計算

        Returns:
            float: 0.0 ~ +0.15
        """
        if chart.moon_phase is None:
            return 0.0

        phase_angle = chart.moon_phase

        for phase_name, phase_info in MOON_PHASES.items():
            min_angle, max_angle = phase_info['range']
            if min_angle <= phase_angle < max_angle:
                return phase_info['axis_effect'].get(axis, 0.0)

        return 0.0

    def _calculate_part_of_fortune_influence(self, chart: 'Chart', axis: str) -> float:
        """
        Part of Fortune（運命の部分）の軸への影響を計算（正負対称）

        占星術的根拠：
        - Part of Fortuneは幸運・適性のポイント
        - 軸関連ハウスにある場合: その軸が自然に発揮される（+）
        - 対向ハウス（180度）にある場合: その軸に葛藤・緊張がある（-）

        Returns:
            float: -0.06 ~ +0.08
        """
        if chart.part_of_fortune is None or not chart.houses:
            return 0.0

        pof_lon = chart.part_of_fortune

        # Part of Fortuneのハウスを計算
        pof_house = None
        for i in range(12):
            cusp1 = chart.houses.cusps[i]
            cusp2 = chart.houses.cusps[(i + 1) % 12]
            if cusp1 > cusp2:
                if pof_lon >= cusp1 or pof_lon < cusp2:
                    pof_house = i + 1
                    break
            else:
                if cusp1 <= pof_lon < cusp2:
                    pof_house = i + 1
                    break

        if pof_house:
            axis_houses = AXIS_RELATED_HOUSES.get(axis, [])

            # 関連ハウスにいれば正の影響
            if pof_house in axis_houses:
                return 0.08

            # 対向ハウス（180度 = 6ハウス先）にいれば負の影響
            opposite_houses = [(h + 5) % 12 + 1 for h in axis_houses]  # 6ハウス先
            if pof_house in opposite_houses:
                return -0.06

        return 0.0

    def _get_house_strength(self, house: int, axis: str) -> float:
        """
        ハウス強度を計算（Angular/Succedent/Cadent + 軸関連）

        Returns:
            float: 0.0 ~ 1.0
        """
        if not house:
            return 0.5

        # 基本のハウス強度（アングル > サクシーデント > カデント）
        angular_houses = [1, 4, 7, 10]
        succedent_houses = [2, 5, 8, 11]
        cadent_houses = [3, 6, 9, 12]

        if house in angular_houses:
            base_strength = 0.8
        elif house in succedent_houses:
            base_strength = 0.5
        else:  # cadent
            base_strength = 0.3

        # 軸関連ハウスにいる場合はボーナス
        axis_houses = AXIS_RELATED_HOUSES.get(axis, [])
        if house in axis_houses:
            base_strength += 0.2

        return min(1.0, base_strength)

    def _get_retrograde_modifier(self, planet_name: str, pos: 'PlanetPosition', axis: str) -> float:
        """
        逆行による軸への影響を計算

        Returns:
            float: 0.0 ~ 1.0（0.5が中立）
        """
        # 太陽と月は逆行しない
        if planet_name in ['sun', 'moon']:
            return 0.5

        # 逆行判定（retrograde属性がある場合）
        is_retrograde = getattr(pos, 'retrograde', False)

        if not is_retrograde:
            return 0.5  # 順行は中立

        # 逆行時の軸への影響
        effect = RETROGRADE_AXIS_EFFECTS.get(axis, 0.0)

        # -0.25 ~ +0.30 → 0.25 ~ 0.80 にスケール
        return 0.5 + effect

    def _calculate_enhanced_aspect_influence(
        self,
        aspects: List['Aspect'],
        axis: str,
        planets: Dict[str, 'PlanetPosition']
    ) -> float:
        """
        アスペクトパターンからの軸への影響を計算（強化版）

        アスペクトの種類と関与する惑星の品位を考慮

        Returns:
            float: -0.5 ~ +0.5
        """
        if not aspects:
            return 0.0

        # 軸に関連する惑星
        axis_name = f"{axis}軸"
        relevant_planets = set(PLANET_AXIS_INFLUENCE.get(axis_name, {}).keys())

        total_influence = 0.0
        aspect_count = 0

        for aspect in aspects:
            # この軸に関連する惑星が関与しているか
            planet1_relevant = aspect.planet1 in relevant_planets
            planet2_relevant = aspect.planet2 in relevant_planets

            if not (planet1_relevant or planet2_relevant):
                continue

            # アスペクトの基本影響
            aspect_info = ASPECT_INFLUENCE.get(aspect.aspect_type, {'modifier': 0.3, 'nature': 'neutral'})
            modifier = aspect_info['modifier']
            nature = aspect_info['nature']

            # 惑星の品位を考慮
            planet1_dignity = 0.0
            planet2_dignity = 0.0

            if aspect.planet1 in planets:
                planet1_dignity = self._get_dignity_score(
                    aspect.planet1, planets[aspect.planet1].sign
                )
            if aspect.planet2 in planets:
                planet2_dignity = self._get_dignity_score(
                    aspect.planet2, planets[aspect.planet2].sign
                )

            # 両惑星の平均品位（-1〜+1のスケール）
            avg_dignity = (planet1_dignity + planet2_dignity) / 2.0

            # アスペクトの性質による影響方向（全て品位依存で正負対称）
            # 占星術的根拠：
            # - アスペクトは「エネルギーの流れ方」を示す
            # - 品位が良い惑星同士のアスペクト → そのエネルギーが建設的に働く
            # - 品位が悪い惑星同士のアスペクト → そのエネルギーが破壊的/停滞的に働く
            if nature == 'intensify':
                # コンジャンクション：品位がそのまま強化される
                # 品位+なら強い正、品位-なら強い負
                influence = modifier * avg_dignity * 0.5
            elif nature == 'flow':
                # トライン：調和的な流れだが、品位に依存
                # 品位+なら良い流れ、品位-なら怠惰・停滞の流れ
                influence = modifier * avg_dignity * 0.4
            elif nature == 'tension':
                # オポジション：対立・気づきだが、品位に依存
                # 品位+なら建設的な気づき、品位-なら破壊的な対立
                influence = modifier * avg_dignity * 0.3
            elif nature == 'challenge':
                # スクエア：挑戦・摩擦、品位で方向が決まる
                # 品位+なら成長の糧、品位-なら障害
                influence = modifier * avg_dignity * 0.35
            elif nature == 'opportunity':
                # セクスタイル：機会だが、品位で活かせるかが決まる
                # 品位+なら活かせる機会、品位-なら逃す機会
                influence = modifier * avg_dignity * 0.3
            elif nature == 'adjustment':
                # クインカンクス：調整が必要、品位で難易度が変わる
                influence = modifier * avg_dignity * 0.25
            elif nature == 'friction':
                # セミスクエア等：軽い摩擦、品位に依存
                influence = modifier * avg_dignity * 0.2
            elif nature == 'talent':
                # クインタイル：才能、品位で発揮度が変わる
                influence = modifier * avg_dignity * 0.25
            elif nature == 'growth':
                # セミセクスタイル：成長の種、品位で育つか決まる
                influence = modifier * avg_dignity * 0.15
            else:
                influence = 0.0

            total_influence += influence
            aspect_count += 1

        if aspect_count == 0:
            return 0.0

        # 正規化して-0.5~+0.5の範囲に
        return max(-0.5, min(0.5, total_influence / max(1, aspect_count)))

    def _apply_sigmoid_transform(self, value: float) -> float:
        """
        分布変換で H/M/L の自然な分布を実現

        正負対称な計算体系により、入力値は自然に0.5を中心に分布する。
        この変換は分布を適度に広げ、H/M/Lの閾値に対して適切に分散させる。

        閾値:
        - H (High): >= 0.60
        - M (Medium): 0.40 - 0.60
        - L (Low): < 0.40

        設計思想:
        - 全ての占星術要素が正負対称に計算されるため、バイアス補正は不要
        - 中央からの距離を線形に増幅し、分布を広げる
        - 増幅率1.5: 入力0.43→出力0.395(L), 入力0.57→出力0.605(H)
        """
        # base_axis_valueの分布が0.5より高めに偏っているため、
        # 中央補正を行った上で増幅する
        # 実測平均: 約0.55 → 補正後の中央: 0.5
        center_adjusted = value - 0.05

        # 中央（0.5）からの距離で評価
        deviation = center_adjusted - 0.5

        # 線形増幅
        # 増幅率2.5: 分布をH/M/Lに適切に広げる
        amplified = deviation * 2.5

        # 変換後の値
        transformed = 0.5 + amplified

        # 0-1にクリップ
        return max(0.0, min(1.0, transformed))

    def _get_element_modifier(self, element: str, axis: str) -> float:
        """エレメントによる軸への影響修正"""
        modifiers = {
            '起動': {'fire': 1.3, 'air': 1.1, 'earth': 0.9, 'water': 0.8},
            '判断': {'air': 1.3, 'earth': 1.2, 'fire': 0.9, 'water': 0.8},
            '選択': {'air': 1.2, 'fire': 1.1, 'water': 1.0, 'earth': 0.9},
            '共鳴': {'water': 1.3, 'earth': 1.1, 'air': 0.9, 'fire': 0.8},
            '自覚': {'water': 1.2, 'earth': 1.2, 'fire': 0.9, 'air': 0.9},
        }
        return modifiers.get(axis, {}).get(element, 1.0)

    def _get_quality_modifier(self, quality: str, axis: str) -> float:
        """クオリティによる軸への影響修正"""
        modifiers = {
            '起動': {'cardinal': 1.3, 'fixed': 0.9, 'mutable': 1.0},
            '判断': {'fixed': 1.2, 'cardinal': 1.0, 'mutable': 0.9},
            '選択': {'mutable': 1.2, 'cardinal': 1.0, 'fixed': 0.9},
            '共鳴': {'mutable': 1.1, 'fixed': 1.1, 'cardinal': 0.9},
            '自覚': {'fixed': 1.2, 'mutable': 1.0, 'cardinal': 0.9},
        }
        return modifiers.get(axis, {}).get(quality, 1.0)

    # ========================================
    # Phase 2: トランジット過程計算
    # ========================================

    def calculate_growth_vector(
        self,
        natal_chart: Chart,
        birth_date: str,
        current_date: datetime
    ) -> GrowthVector:
        """
        出生から現在までのトランジット過程を計算し、
        成長ベクトルを生成
        """
        birth_dt = datetime.strptime(birth_date, "%Y-%m-%d")
        years_elapsed = (current_date - birth_dt).days / 365.25

        # ライフサイクルイベントを収集
        events = []

        # 1. サターンリターン（約29.5年周期）
        saturn_returns = self._calculate_saturn_returns(years_elapsed)
        for sr in saturn_returns:
            events.append(LifeCycleEvent(
                event_type='saturn_return',
                event_date=birth_dt + timedelta(days=sr['age'] * 365.25),
                age_at_event=sr['age'],
                affected_axes=['自覚軸', '判断軸'],
                influence_strength=sr['strength'],
                description=f"サターンリターン（{sr['number']}回目）: 自己の限界と責任の認識"
            ))

        # 2. ジュピターリターン（約12年周期）
        jupiter_returns = self._calculate_jupiter_returns(years_elapsed)
        for jr in jupiter_returns:
            events.append(LifeCycleEvent(
                event_type='jupiter_return',
                event_date=birth_dt + timedelta(days=jr['age'] * 365.25),
                age_at_event=jr['age'],
                affected_axes=['共鳴軸', '選択軸'],
                influence_strength=jr['strength'],
                description=f"ジュピターリターン（{jr['number']}回目）: 拡張と成長の機会"
            ))

        # 3. プログレス月のサイクル（約27.3年で一周）
        progressed_moon_phases = self._calculate_progressed_moon_phases(years_elapsed)
        for phase in progressed_moon_phases:
            events.append(LifeCycleEvent(
                event_type='progressed_moon_phase',
                event_date=birth_dt + timedelta(days=phase['age'] * 365.25),
                age_at_event=phase['age'],
                affected_axes=['共鳴軸', '自覚軸'],
                influence_strength=phase['strength'],
                description=f"プログレス月{phase['phase']}: 感情サイクルの{phase['meaning']}"
            ))

        # 4. プログレス太陽のサイン移動（約30年で1サイン）
        progressed_sun_changes = self._calculate_progressed_sun_changes(
            natal_chart, years_elapsed
        )
        for change in progressed_sun_changes:
            events.append(LifeCycleEvent(
                event_type='progressed_sun_sign_change',
                event_date=birth_dt + timedelta(days=change['age'] * 365.25),
                age_at_event=change['age'],
                affected_axes=['起動軸'],
                influence_strength=change['strength'],
                description=f"プログレス太陽が{change['to_sign']}へ: アイデンティティの変容"
            ))

        # 5. 重要なトランジット履歴（過去の土星・冥王星のハードアスペクト）
        major_transit_history = self._calculate_major_transit_history(
            natal_chart, birth_dt, current_date
        )
        events.extend(major_transit_history)

        # イベントを日付順にソート
        events.sort(key=lambda e: e.event_date)

        # 成長ベクトルを計算
        growth_vector = [0.0] * 5  # 5軸

        for event in events:
            # イベントからの経過年数による減衰
            years_since_event = (current_date - event.event_date).days / 365.25
            decay = math.exp(-years_since_event / 10)  # 10年で約37%に減衰

            for axis in event.affected_axes:
                idx = AXIS_ORDER.index(axis)
                growth_vector[idx] += event.influence_strength * decay * 0.1

        # 現在のライフフェーズを判定
        current_phase = self._determine_life_phase(years_elapsed, events)

        # 成熟度を計算
        maturity_level = self._calculate_maturity_level(years_elapsed, events)

        return GrowthVector(
            vector=growth_vector,
            major_events=events,
            current_phase=current_phase,
            maturity_level=maturity_level
        )

    def _calculate_saturn_returns(self, years_elapsed: float) -> List[Dict]:
        """サターンリターンを計算"""
        returns = []
        saturn_period = 29.46

        for i in range(1, 4):  # 最大3回まで
            return_age = saturn_period * i
            if return_age <= years_elapsed:
                # 経過してからの年数による影響の減衰
                years_since = years_elapsed - return_age
                strength = 1.0 * math.exp(-years_since / 5)  # 5年で減衰
                returns.append({
                    'number': i,
                    'age': return_age,
                    'strength': strength
                })
            elif return_age <= years_elapsed + 2:  # 2年以内に来る
                # 接近中の影響
                years_until = return_age - years_elapsed
                strength = 0.5 * (1 - years_until / 2)
                returns.append({
                    'number': i,
                    'age': return_age,
                    'strength': max(0, strength)
                })

        return returns

    def _calculate_jupiter_returns(self, years_elapsed: float) -> List[Dict]:
        """ジュピターリターンを計算"""
        returns = []
        jupiter_period = 11.86

        for i in range(1, 10):  # 最大9回まで
            return_age = jupiter_period * i
            if return_age <= years_elapsed:
                years_since = years_elapsed - return_age
                strength = 0.7 * math.exp(-years_since / 3)  # 3年で減衰
                if strength > 0.1:
                    returns.append({
                        'number': i,
                        'age': return_age,
                        'strength': strength
                    })

        return returns

    def _calculate_progressed_moon_phases(self, years_elapsed: float) -> List[Dict]:
        """プログレス月のフェーズを計算"""
        phases = []
        moon_cycle = 27.3  # プログレスでは27.3年で一周

        phase_names = [
            ('新月', '始まり'),
            ('上弦', '挑戦'),
            ('満月', '実現'),
            ('下弦', '解放')
        ]

        for cycle in range(int(years_elapsed / moon_cycle) + 2):
            for i, (phase, meaning) in enumerate(phase_names):
                phase_age = cycle * moon_cycle + (i * moon_cycle / 4)
                if abs(years_elapsed - phase_age) < 1.5:  # 前後1.5年
                    distance = abs(years_elapsed - phase_age)
                    strength = 0.6 * (1 - distance / 1.5)
                    phases.append({
                        'phase': phase,
                        'meaning': meaning,
                        'age': phase_age,
                        'strength': max(0, strength)
                    })

        return phases

    def _calculate_progressed_sun_changes(
        self,
        natal_chart: Chart,
        years_elapsed: float
    ) -> List[Dict]:
        """プログレス太陽のサイン移動を計算"""
        changes = []

        if 'sun' not in natal_chart.planets:
            return changes

        natal_sun = natal_chart.planets['sun']
        natal_degree = natal_sun.longitude

        # プログレス太陽は1年で約1度進む
        # サイン境界（30度ごと）を超えるタイミングを計算

        current_sign_index = int(natal_degree / 30)
        degree_in_sign = natal_degree % 30

        # 次のサインまでの年数
        years_to_next_sign = 30 - degree_in_sign

        for i in range(4):  # 最大4回のサイン変更まで
            change_age = years_to_next_sign + (i * 30)
            if change_age <= years_elapsed + 5:  # 5年先まで
                new_sign_index = (current_sign_index + i + 1) % 12
                new_sign = ZODIAC_SIGNS[new_sign_index]

                if change_age <= years_elapsed:
                    years_since = years_elapsed - change_age
                    strength = 0.8 * math.exp(-years_since / 7)
                else:
                    years_until = change_age - years_elapsed
                    strength = 0.4 * (1 - years_until / 5)

                if strength > 0.1:
                    changes.append({
                        'age': change_age,
                        'to_sign': new_sign,
                        'strength': max(0, strength)
                    })

        return changes

    def _calculate_major_transit_history(
        self,
        natal_chart: Chart,
        birth_dt: datetime,
        current_date: datetime
    ) -> List[LifeCycleEvent]:
        """過去の主要トランジット履歴を計算"""
        events = []

        # サンプリング間隔（6ヶ月ごとにチェック）
        sample_interval = timedelta(days=180)
        check_date = birth_dt + timedelta(days=365 * 7)  # 7歳から

        # 注目する外惑星
        outer_planets = ['saturn', 'uranus', 'neptune', 'pluto']

        # 注目するネイタル天体
        natal_points = ['sun', 'moon', 'mercury', 'venus', 'mars']

        while check_date < current_date:
            try:
                transit_chart = self.astro_engine.calculate_transit_chart(check_date)

                for t_planet in outer_planets:
                    if t_planet not in transit_chart.planets:
                        continue
                    t_pos = transit_chart.planets[t_planet]

                    for n_planet in natal_points:
                        if n_planet not in natal_chart.planets:
                            continue
                        n_pos = natal_chart.planets[n_planet]

                        # アスペクトチェック
                        diff = abs(t_pos.longitude - n_pos.longitude)
                        if diff > 180:
                            diff = 360 - diff

                        # ハードアスペクトのみ（コンジャンクション、スクエア、オポジション）
                        for aspect_type in ['conjunction', 'square', 'opposition']:
                            aspect_def = ASPECTS[aspect_type]
                            orb = abs(diff - aspect_def['angle'])

                            if orb <= aspect_def['orb'] / 2:  # 厳密なオーブ
                                age = (check_date - birth_dt).days / 365.25

                                # 影響する軸を決定
                                affected_axes = self._get_affected_axes_by_planets(
                                    t_planet, n_planet
                                )

                                events.append(LifeCycleEvent(
                                    event_type=f'transit_{t_planet}_{aspect_type}_{n_planet}',
                                    event_date=check_date,
                                    age_at_event=age,
                                    affected_axes=affected_axes,
                                    influence_strength=aspect_def['strength'] * 0.5,
                                    description=f"T.{t_planet} {aspect_type} N.{n_planet}"
                                ))
            except Exception as e:
                logger.warning(f"Transit calculation failed for {check_date}: {e}")

            check_date += sample_interval

        # 重複を除去し、最も強い影響のみ残す
        events = self._deduplicate_events(events)

        return events

    def _get_affected_axes_by_planets(
        self,
        transit_planet: str,
        natal_planet: str
    ) -> List[str]:
        """惑星の組み合わせから影響を受ける軸を判定"""
        affected = set()

        for axis_name, planets in PLANET_AXIS_INFLUENCE.items():
            if transit_planet in planets or natal_planet in planets:
                affected.add(axis_name)

        return list(affected)

    def _deduplicate_events(
        self,
        events: List[LifeCycleEvent]
    ) -> List[LifeCycleEvent]:
        """近い日付のイベントを統合"""
        if not events:
            return []

        events.sort(key=lambda e: e.event_date)
        deduplicated = []

        for event in events:
            # 同じタイプのイベントが90日以内にあれば統合
            merged = False
            for i, existing in enumerate(deduplicated):
                if existing.event_type == event.event_type:
                    days_diff = abs((event.event_date - existing.event_date).days)
                    if days_diff < 90:
                        # より強い方を残す
                        if event.influence_strength > existing.influence_strength:
                            deduplicated[i] = event
                        merged = True
                        break

            if not merged:
                deduplicated.append(event)

        return deduplicated

    def _determine_life_phase(
        self,
        years_elapsed: float,
        events: List[LifeCycleEvent]
    ) -> str:
        """現在のライフフェーズを判定"""
        if years_elapsed < 7:
            return "幼年期（形成期）"
        elif years_elapsed < 14:
            return "少年期（探索期）"
        elif years_elapsed < 21:
            return "青年期（自立期）"
        elif years_elapsed < 29:
            return "成人前期（確立期）"
        elif years_elapsed < 30:
            return "第1サターンリターン期（転換期）"
        elif years_elapsed < 42:
            return "成人中期（発展期）"
        elif years_elapsed < 50:
            return "中年前期（統合期）"
        elif years_elapsed < 59:
            return "中年後期（成熟期）"
        elif years_elapsed < 60:
            return "第2サターンリターン期（再転換期）"
        else:
            return "熟年期（完成期）"

    def _calculate_maturity_level(
        self,
        years_elapsed: float,
        events: List[LifeCycleEvent]
    ) -> float:
        """成熟度を計算（0-1）"""
        # 基本的な年齢による成熟
        base_maturity = min(1.0, years_elapsed / 60)

        # サターンリターン経験による成熟加算
        saturn_returns = [e for e in events if e.event_type == 'saturn_return']
        saturn_bonus = len([e for e in saturn_returns if e.event_date < datetime.now()]) * 0.15

        return min(1.0, base_maturity + saturn_bonus)

    # ========================================
    # Phase 3: 現在トランジット影響
    # ========================================

    def calculate_current_transit_influence(
        self,
        natal_chart: Chart,
        current_date: datetime
    ) -> Tuple[List[TransitInfluence], List[float]]:
        """
        現在のトランジットがネイタルに与える影響を計算

        Returns:
            (トランジット影響リスト, 5軸への影響ベクトル)
        """
        transit_chart = self.astro_engine.calculate_transit_chart(current_date)

        influences = []
        transit_vector = [0.0] * 5

        # トランジット×ネイタルのアスペクトを取得
        aspects = self.astro_engine.calculate_transit_to_natal_aspects(
            transit_chart, natal_chart
        )

        for aspect in aspects:
            transit_planet = aspect.planet1.replace('(tr/pr)', '').strip()
            natal_planet = aspect.planet2.replace('(n)', '').strip()

            # 外惑星のアスペクトを重視
            if transit_planet in ['saturn', 'uranus', 'neptune', 'pluto']:
                weight = 1.0
            elif transit_planet in ['jupiter', 'mars']:
                weight = 0.6
            else:
                weight = 0.3

            # 影響する軸を特定
            affected_axes = self._get_affected_axes_by_planets(transit_planet, natal_planet)

            # 影響ベクトルを計算
            influence_vec = [0.0] * 5
            for axis in affected_axes:
                idx = AXIS_ORDER.index(axis)
                aspect_info = ASPECT_INFLUENCE.get(aspect.aspect_type, {})
                modifier = aspect_info.get('modifier', 0.5)
                nature = aspect_info.get('nature', 'neutral')

                # 影響の方向（強化/緊張）
                if nature in ['intensify', 'flow', 'opportunity']:
                    influence_vec[idx] = modifier * aspect.strength * weight * 0.1
                elif nature in ['tension', 'challenge']:
                    influence_vec[idx] = modifier * aspect.strength * weight * 0.05

            influences.append(TransitInfluence(
                transit_planet=transit_planet,
                natal_planet=natal_planet,
                aspect_type=aspect.aspect_type,
                affected_axes=affected_axes,
                influence_vector=influence_vec,
                strength=aspect.strength * weight,
                nature=ASPECT_INFLUENCE.get(aspect.aspect_type, {}).get('nature', 'neutral'),
                is_applying=aspect.applying
            ))

            # 全体のトランジットベクトルに加算
            for i in range(5):
                transit_vector[i] += influence_vec[i]

        # 強度でソート
        influences.sort(key=lambda x: x.strength, reverse=True)

        return influences, transit_vector

    # ========================================
    # Phase 4 & 5: 統合計算
    # ========================================

    def integrate_all_factors(
        self,
        natal_axes: Dict[str, float],
        growth_vector: GrowthVector,
        transit_vector: List[float],
        questionnaire_axes: Dict[str, float]
    ) -> Dict[str, float]:
        """
        全要素を統合してカレント5軸を計算

        【STRUCT CODE v2.1 統合アルゴリズム】

        Step 1: ネイタル5軸の算出
        - 占星術チャート (70%): 先天的素質（natal_axesはチャートのみから計算済み）
        - 設問回答 (30%): 後天的な自己認識

        Step 2: カレント5軸の算出
        - ネイタル5軸 + 時期的変調（成長ベクトル + トランジット影響）

        これにより:
        - ネイタル診断: 占星術70% + 設問30% の融合
        - カレント診断: ネイタル + 時期的変調（トランジット/プログレス）
        """
        current_axes = {}

        # 重み付け定義
        CHART_WEIGHT = 0.70      # 占星術チャートの重み
        QUESTIONNAIRE_WEIGHT = 0.30  # 設問回答の重み

        # 変調の最大影響範囲（±0.15程度に制限）
        MAX_GROWTH_MODULATION = 0.10
        MAX_TRANSIT_MODULATION = 0.08

        for i, axis_name in enumerate(AXIS_ORDER):
            # チャートから算出されたネイタル値
            chart_natal_val = natal_axes.get(axis_name, 0.5)
            # 設問回答から算出された値
            quest_val = questionnaire_axes.get(axis_name, 0.5)

            # Step 1: ネイタル5軸 = チャート(70%) + 設問(30%)
            natal_enhanced = chart_natal_val * CHART_WEIGHT + quest_val * QUESTIONNAIRE_WEIGHT

            # 成長ベクトルとトランジットベクトルを変調として適用
            growth_val = growth_vector.vector[i]
            transit_val = transit_vector[i]

            # 変調を適切な範囲に制限（累積で大きくなりすぎないように）
            growth_modulation = max(-MAX_GROWTH_MODULATION, min(MAX_GROWTH_MODULATION, growth_val * 0.15))
            transit_modulation = max(-MAX_TRANSIT_MODULATION, min(MAX_TRANSIT_MODULATION, transit_val * 0.20))

            # Step 2: カレント5軸 = ネイタル5軸 + 時期的変調
            current_val = natal_enhanced + growth_modulation + transit_modulation

            current_axes[axis_name] = max(0.0, min(1.0, current_val))

        return current_axes

    # ========================================
    # Phase 6: 動的タイプ判定
    # ========================================

    def classify_dynamic_type(
        self,
        natal_type: str,
        natal_axes: Dict[str, float],
        current_axes: Dict[str, float],
        growth_vector: GrowthVector
    ) -> Tuple[str, float, TransitionState, List[str]]:
        """
        動的にタイプを判定

        単純な距離計算ではなく、ネイタルタイプからの遷移可能性を考慮

        Returns:
            (カレントタイプ, 信頼度, 遷移状態, 遷移経路)
        """
        natal_group = self.struct_types[natal_type]['group']

        # 候補タイプを優先度付きで収集
        candidates = []

        for type_code, type_info in self.struct_types.items():
            # 基本スコア（距離ベース）
            base_score = self._calculate_type_score(current_axes, type_info)

            # グループボーナス（同グループ内は自然な遷移）
            type_group = type_info['group']
            if type_group == natal_group:
                group_bonus = 0.15
            elif self._are_adjacent_groups(natal_group, type_group):
                group_bonus = 0.05
            else:
                group_bonus = -0.10  # 異グループへの急激な遷移はペナルティ

            # 成熟度による調整
            # 成熟度が高いほど、より複雑なタイプへの遷移が自然
            primary_axes_count = len(type_info['primary_axes'])
            maturity_adjustment = 0.0
            if primary_axes_count >= 3 and growth_vector.maturity_level < 0.5:
                maturity_adjustment = -0.05  # 未成熟で複雑タイプはペナルティ
            elif primary_axes_count >= 3 and growth_vector.maturity_level > 0.7:
                maturity_adjustment = 0.03  # 成熟していれば複雑タイプにボーナス

            total_score = base_score + group_bonus + maturity_adjustment

            candidates.append({
                'type': type_code,
                'name': type_info['name'],
                'group': type_group,
                'base_score': base_score,
                'group_bonus': group_bonus,
                'maturity_adj': maturity_adjustment,
                'total_score': total_score
            })

        # スコア順にソート
        candidates.sort(key=lambda x: x['total_score'], reverse=True)

        best = candidates[0]
        current_type = best['type']
        confidence = best['total_score']

        # 遷移状態を判定
        if current_type == natal_type:
            transition_state = TransitionState.STABLE
            transition_path = [natal_type]
        elif best['group'] == natal_group:
            transition_state = TransitionState.TRANSITIONING
            transition_path = [natal_type, current_type]
        else:
            transition_state = TransitionState.TRANSFORMED
            transition_path = self._find_transition_path(natal_type, current_type)

        return current_type, confidence, transition_state, transition_path

    def _calculate_type_score(
        self,
        axes: Dict[str, float],
        type_info: Dict
    ) -> float:
        """タイプとの適合スコアを計算"""
        type_vector = type_info['vector']
        type_sig = type_info['axis_signature']

        # シグネチャベースのスコア
        input_sig = self._get_signature(axes)

        # H位置の一致
        input_h = {i for i, c in enumerate(input_sig) if c == 'H'}
        type_h = {i for i, (axis, level) in enumerate(
            [(a, type_sig[a.replace('軸', '')]) for a in AXIS_ORDER]
        ) if level == 'H'}

        h_intersection = len(input_h & type_h)
        h_union = len(input_h | type_h)
        h_jaccard = h_intersection / h_union if h_union > 0 else 1.0

        # L位置の一致
        input_l = {i for i, c in enumerate(input_sig) if c == 'L'}
        type_l = {i for i, (axis, level) in enumerate(
            [(a, type_sig[a.replace('軸', '')]) for a in AXIS_ORDER]
        ) if level == 'L'}

        l_intersection = len(input_l & type_l)
        l_union = len(input_l | type_l)
        l_jaccard = l_intersection / l_union if l_union > 0 else 1.0

        # ベクトル距離
        input_vector = [axes[axis] for axis in AXIS_ORDER]
        euc_dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(input_vector, type_vector)))
        dist_score = max(0, 1.0 - euc_dist / 0.8)

        # 総合スコア
        score = h_jaccard * 0.45 + l_jaccard * 0.20 + dist_score * 0.35

        return score

    def _get_signature(self, axes: Dict[str, float]) -> str:
        """軸値からシグネチャを生成"""
        sig = ''
        for axis in AXIS_ORDER:
            val = axes.get(axis, 0.5)
            if val >= 0.62:
                sig += 'H'
            elif val >= 0.42:
                sig += 'M'
            else:
                sig += 'L'
        return sig

    def _are_adjacent_groups(self, group1: str, group2: str) -> bool:
        """隣接グループかどうか判定"""
        adjacency = {
            'AC': ['CH', 'RS', 'AW'],  # 起動軸と関連
            'JD': ['CH', 'AW'],        # 判断軸と関連
            'CH': ['AC', 'JD', 'RS'],  # 選択軸と関連
            'RS': ['AC', 'CH', 'AW'],  # 共鳴軸と関連
            'AW': ['AC', 'JD', 'RS'],  # 認識軸と関連
            'BL': ['AC', 'JD', 'CH', 'RS', 'AW'],  # バランスは全てと隣接
        }
        return group2 in adjacency.get(group1, [])

    def _find_transition_path(self, from_type: str, to_type: str) -> List[str]:
        """遷移経路を推定"""
        from_group = self.struct_types[from_type]['group']
        to_group = self.struct_types[to_type]['group']

        if from_group == to_group:
            return [from_type, to_type]

        # 中間タイプを探索（簡易版）
        # 両方のグループと関連するタイプを探す
        for type_code, type_info in self.struct_types.items():
            if type_info['group'] == 'BL':  # バランスタイプは中継点
                return [from_type, type_code, to_type]

        return [from_type, to_type]

    def _classify_type(self, axes: Dict[str, float]) -> Tuple[str, float]:
        """シンプルなタイプ分類（ネイタル用）"""
        best_type = None
        best_score = -1

        for type_code, type_info in self.struct_types.items():
            score = self._calculate_type_score(axes, type_info)
            if score > best_score:
                best_score = score
                best_type = type_code

        return best_type, best_score

    # ========================================
    # メイン処理
    # ========================================

    def classify(
        self,
        birth_date: str,
        birth_time: Optional[str],
        birth_place: str,
        questionnaire_axes: Dict[str, float],
        diagnosis_date: datetime = None
    ) -> DynamicClassificationResult:
        """
        動的タイプ分類のメイン処理

        Args:
            birth_date: 生年月日 (YYYY-MM-DD)
            birth_time: 出生時刻 (HH:MM) - オプション
            birth_place: 出生地
            questionnaire_axes: 設問回答から算出した5軸
            diagnosis_date: 診断日（デフォルトは現在）

        Returns:
            DynamicClassificationResult: 分類結果
        """
        if diagnosis_date is None:
            diagnosis_date = datetime.now()

        logger.info(f"Starting dynamic classification for birth_date={birth_date}")

        # Phase 1: ネイタルタイプ確定
        natal_type, natal_axes, natal_chart = self.calculate_natal_type(
            birth_date, birth_time, birth_place
        )

        # Phase 2: トランジット過程計算
        growth_vector = self.calculate_growth_vector(
            natal_chart, birth_date, diagnosis_date
        )

        # Phase 3: 現在トランジット影響
        current_transits, transit_vector = self.calculate_current_transit_influence(
            natal_chart, diagnosis_date
        )

        # Phase 4 & 5: 統合計算
        current_axes = self.integrate_all_factors(
            natal_axes, growth_vector, transit_vector, questionnaire_axes
        )

        # Phase 6: 動的タイプ判定
        current_type, confidence, transition_state, transition_path = \
            self.classify_dynamic_type(
                natal_type, natal_axes, current_axes, growth_vector
            )

        # 今後の可能性のあるタイプを推定
        potential_next = self._estimate_potential_next_types(
            current_type, current_transits, growth_vector
        )

        # ネイタルチャートサマリー
        natal_summary = self._create_natal_summary(natal_chart)

        # 解釈テキスト生成
        interpretation = self._generate_interpretation(
            natal_type, current_type, transition_state,
            growth_vector, current_transits
        )

        # 成長軸・トランジット軸をDict形式に変換
        growth_axes = {
            AXIS_ORDER[i]: growth_vector.vector[i]
            for i in range(5)
        }
        transit_axes = {
            AXIS_ORDER[i]: transit_vector[i]
            for i in range(5)
        }

        return DynamicClassificationResult(
            natal_type=natal_type,
            current_type=current_type,
            confidence=confidence,
            natal_axes=natal_axes,
            current_axes=current_axes,
            growth_axes=growth_axes,
            transit_axes=transit_axes,
            questionnaire_axes=questionnaire_axes,
            transition_state=transition_state,
            transition_path=transition_path,
            potential_next_types=potential_next,
            life_cycle_events=growth_vector.major_events,
            current_transits=current_transits,
            growth_vector=growth_vector,
            natal_chart_summary=natal_summary,
            interpretation=interpretation
        )

    def _estimate_potential_next_types(
        self,
        current_type: str,
        current_transits: List[TransitInfluence],
        growth_vector: GrowthVector
    ) -> List[str]:
        """今後移行する可能性のあるタイプを推定"""
        current_group = self.struct_types[current_type]['group']
        potential = []

        # 同グループ内のタイプ
        for type_code in TYPE_GROUPS.get(current_group, []):
            if type_code != current_type:
                potential.append(type_code)

        # 強いトランジットがある場合、その影響を受けるグループのタイプも追加
        for transit in current_transits[:3]:  # 上位3つ
            if transit.strength > 0.5:
                for axis in transit.affected_axes:
                    # その軸が主要なタイプを探す
                    for type_code, type_info in self.struct_types.items():
                        if axis.replace('軸', '') in type_info.get('primary_axes', []):
                            if type_code not in potential and type_code != current_type:
                                potential.append(type_code)

        return potential[:5]  # 上位5つまで

    def _create_natal_summary(self, natal_chart: Chart) -> Dict[str, Any]:
        """ネイタルチャートのサマリーを作成"""
        summary = {
            'datetime': natal_chart.datetime.isoformat(),
            'planets': {},
            'houses': None,
            'major_aspects': []
        }

        for name, pos in natal_chart.planets.items():
            summary['planets'][name] = {
                'sign': pos.sign,
                'degree': round(pos.sign_degree, 1),
                'house': pos.house,
                'element': pos.element,
                'quality': pos.quality
            }

        if natal_chart.houses:
            summary['houses'] = {
                'asc': round(natal_chart.houses.asc, 1),
                'mc': round(natal_chart.houses.mc, 1)
            }

        # 主要アスペクト（強度上位5つ）
        sorted_aspects = sorted(natal_chart.aspects, key=lambda a: a.strength, reverse=True)
        for aspect in sorted_aspects[:5]:
            summary['major_aspects'].append({
                'planets': f"{aspect.planet1} - {aspect.planet2}",
                'type': aspect.aspect_type,
                'nature': aspect.nature
            })

        return summary

    def _generate_interpretation(
        self,
        natal_type: str,
        current_type: str,
        transition_state: TransitionState,
        growth_vector: GrowthVector,
        current_transits: List[TransitInfluence]
    ) -> str:
        """解釈テキストを生成"""
        natal_info = self.struct_types[natal_type]
        current_info = self.struct_types[current_type]

        lines = []

        # 基本構造
        lines.append(f"【基本構造（ネイタル）】")
        lines.append(f"あなたの基本タイプは{natal_type}（{natal_info['name']}）です。")

        # 現在の状態
        lines.append(f"\n【現在の状態（カレント）】")
        if transition_state == TransitionState.STABLE:
            lines.append(f"現在も{natal_type}の特性が中心となっています。")
        elif transition_state == TransitionState.TRANSITIONING:
            lines.append(f"現在は{current_type}（{current_info['name']}）への移行過程にあります。")
        else:
            lines.append(f"現在は{current_type}（{current_info['name']}）の特性が前面に出ています。")

        # ライフフェーズ
        lines.append(f"\n【ライフフェーズ】")
        lines.append(f"現在は「{growth_vector.current_phase}」の時期です。")
        lines.append(f"成熟度: {growth_vector.maturity_level:.0%}")

        # 主要なトランジット
        if current_transits:
            lines.append(f"\n【現在の天体影響】")
            for transit in current_transits[:3]:
                lines.append(
                    f"- {transit.transit_planet}が{transit.natal_planet}と"
                    f"{transit.aspect_type}（{transit.nature}）"
                )

        # 主要なライフイベント
        recent_events = [
            e for e in growth_vector.major_events
            if e.event_date > datetime.now() - timedelta(days=365*3)
        ]
        if recent_events:
            lines.append(f"\n【最近の重要なサイクル】")
            for event in recent_events[:3]:
                lines.append(f"- {event.description}")

        return "\n".join(lines)


# シングルトンインスタンス
_classifier_instance = None

def get_dynamic_classifier() -> DynamicTypeClassifier:
    """DynamicTypeClassifierのシングルトンインスタンスを取得"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DynamicTypeClassifier()
    return _classifier_instance

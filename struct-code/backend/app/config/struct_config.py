"""
STRUCT CODE Configuration Management
設定の外部化と管理
"""

from typing import Dict, List, Tuple, Optional
from pathlib import Path
import os
import time
import threading
from functools import lru_cache

# geopy for geocoding
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    print("Warning: geopy not installed. Using fallback coordinates.")

# Pydantic設定を使わずにシンプルな設定クラス
class StructCodeConfig:
    """STRUCT CODE システム設定"""
    
    def __init__(self):
        # === 基本設定 ===
        self.app_name = "STRUCT CODE Ultimate"
        self.app_version = "1.0.0"
        self.debug_mode = False
        
        # === データパス設定 ===
        self.data_path = "/app/data"
        self.bsp_file = "de421.bsp"
        
        # === 占星術設定 ===
        self.default_birth_hour = 12
        self.aspect_orb_conjunction = 10.0
        self.aspect_orb_square = 8.0
        self.aspect_orb_trine = 8.0
        self.aspect_orb_opposition = 10.0
        self.aspect_orb_sextile = 6.0
        
        # === 軸計算の重み設定 ===
        self.weight_astronomy = 0.7
        self.weight_questionnaire = 0.3
        self.weight_aspects = 0.2
        self.weight_time_layer = 0.1
        
        # === タイプ決定の閾値 ===
        self.type_confidence_threshold = 0.5
        self.axis_high_threshold = 0.65
        self.axis_medium_threshold = 0.35
        
        # === ログ設定 ===
        self.log_level = "INFO"
        self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # === デフォルト都市座標 ===
        self.default_coordinates = (35.6762, 139.6503)  # Tokyo

# グローバル設定インスタンス
config = StructCodeConfig()

# === 都市座標データ ===
CITY_COORDINATES = {
    'Tokyo': (35.6762, 139.6503),
    'Osaka': (34.6937, 135.5023),
    'Kyoto': (35.0116, 135.7681),
    'Yokohama': (35.4437, 139.6380),
    'Sapporo': (43.0642, 141.3469),
    'Fukuoka': (33.5904, 130.4017),
    'Kobe': (34.6901, 135.1955),
    'Nagoya': (35.1815, 136.9066),
    'Sendai': (38.2682, 140.8694),
    'Hiroshima': (34.3853, 132.4553),
    'Kanazawa': (36.5944, 136.6256),
    'Okinawa': (26.2124, 127.6809),
    'Niigata': (37.9162, 139.0364),
    'Kumamoto': (32.7898, 130.7417),
    'Kagoshima': (31.5966, 130.5571),
    'Morioka': (39.7036, 141.1527),
    'Takayama': (36.1461, 137.2521),
    'Matsue': (35.4723, 133.0505),
    'Takamatsu': (34.3428, 134.0467),
    'Tokushima': (34.0658, 134.5593)
}

# === 星座情報 ===
ZODIAC_SIGNS = [
    '牡羊座', '牡牛座', '双子座', '蟹座',
    '獅子座', '乙女座', '天秤座', '蠍座', 
    '射手座', '山羊座', '水瓶座', '魚座'
]

ZODIAC_ELEMENTS = {
    '牡羊座': 'fire', '獅子座': 'fire', '射手座': 'fire',
    '牡牛座': 'earth', '乙女座': 'earth', '山羊座': 'earth',
    '双子座': 'air', '天秤座': 'air', '水瓶座': 'air',
    '蟹座': 'water', '蠍座': 'water', '魚座': 'water'
}

# === アスペクト設定 ===
ASPECT_DEFINITIONS = {
    'conjunction': {
        'angle': 0,
        'orb': config.aspect_orb_conjunction,
        'nature': 'fusion',
        'intensity': 1.5
    },
    'sextile': {
        'angle': 60,
        'orb': config.aspect_orb_sextile,
        'nature': 'harmony',
        'intensity': 1.2
    },
    'square': {
        'angle': 90,
        'orb': config.aspect_orb_square,
        'nature': 'tension',
        'intensity': 1.3
    },
    'trine': {
        'angle': 120,
        'orb': config.aspect_orb_trine,
        'nature': 'flow',
        'intensity': 1.25
    },
    'opposition': {
        'angle': 180,
        'orb': config.aspect_orb_opposition,
        'nature': 'polarity',
        'intensity': 1.4
    }
}

# === 選択肢の数値マッピング ===
CHOICE_VALUES = {
    'A': 0.8,
    'B': 0.6,
    'C': 0.4,
    'D': 0.2
}

# === 天体のアーキタイプデータ ===
PLANETARY_ARCHETYPES = {
    'sun': {
        'essence': '自我・生命力・目的意識',
        'shadow': '傲慢・自己中心性',
        'gift': '輝き・リーダーシップ・創造性',
        'color': '#FFD700',
        'symbol': '☉'
    },
    'moon': {
        'essence': '感情・本能・無意識',
        'shadow': '依存・不安定性',
        'gift': '共感・養育・直感',
        'color': '#C0C0C0',
        'symbol': '☽'
    },
    'mercury': {
        'essence': '知性・コミュニケーション・学習',
        'shadow': '表層的理解・噂話',
        'gift': '理解力・表現力・適応力',
        'color': '#FFA500',
        'symbol': '☿'
    },
    'venus': {
        'essence': '愛・美・調和',
        'shadow': '虚栄・怠惰',
        'gift': '魅力・芸術性・平和',
        'color': '#FF69B4',
        'symbol': '♀'
    },
    'mars': {
        'essence': '行動・欲望・闘争',
        'shadow': '攻撃性・衝動性',
        'gift': '勇気・実行力・情熱',
        'color': '#FF0000',
        'symbol': '♂'
    },
    'jupiter': {
        'essence': '拡大・成長・幸運',
        'shadow': '過剰・傲慢',
        'gift': '寛容・楽観・知恵',
        'color': '#4169E1',
        'symbol': '♃'
    },
    'saturn': {
        'essence': '制限・責任・成熟',
        'shadow': '抑圧・恐れ',
        'gift': '規律・忍耐・達成',
        'color': '#708090',
        'symbol': '♄'
    },
    'uranus': {
        'essence': '革新・独立・覚醒',
        'shadow': '反逆・不安定',
        'gift': '独創性・自由・進化',
        'color': '#40E0D0',
        'symbol': '♅'
    },
    'neptune': {
        'essence': '霊性・幻想・統合',
        'shadow': '幻想・逃避',
        'gift': '想像力・慈悲・超越',
        'color': '#4169E1',
        'symbol': '♆'
    },
    'pluto': {
        'essence': '変容・死と再生・力',
        'shadow': '破壊・執着',
        'gift': '再生・深層理解・真の力',
        'color': '#8B0000',
        'symbol': '♇'
    }
}

def get_data_path() -> Path:
    """データパスを取得"""
    if os.path.exists("/app/data"):
        return Path("/app/data")
    else:
        current_dir = Path(__file__).parent.parent.parent.parent
        return current_dir / "data"

# === ジオコーディングキャッシュ ===
_geocode_cache: Dict[str, Tuple[float, float]] = {}
_geocode_cache_lock = threading.Lock()

# Nominatim geocoder instance (lazy initialization)
_geocoder = None

def _get_geocoder():
    """Nominatim geocoderを取得（遅延初期化）"""
    global _geocoder
    if _geocoder is None and GEOPY_AVAILABLE:
        _geocoder = Nominatim(user_agent="struct_code_astrology_v1.0")
    return _geocoder


def _geocode_with_retry(query: str, retries: int = 3) -> Optional[Tuple[float, float]]:
    """リトライ付きジオコーディング"""
    geocoder = _get_geocoder()
    if not geocoder:
        return None

    for attempt in range(retries):
        try:
            # Rate limiting: Nominatimは1秒に1リクエスト制限
            time.sleep(1.1)

            location = geocoder.geocode(query, timeout=10)
            if location:
                return (location.latitude, location.longitude)
            return None

        except GeocoderTimedOut:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return None
        except GeocoderServiceError as e:
            print(f"Geocoding service error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected geocoding error: {e}")
            return None

    return None


def geocode_japanese_location(location: str) -> Optional[Tuple[float, float]]:
    """日本の地名から座標を取得（キャッシュ付き）"""
    if not GEOPY_AVAILABLE:
        return None

    # キャッシュ確認
    cache_key = location.lower().strip()
    with _geocode_cache_lock:
        if cache_key in _geocode_cache:
            return _geocode_cache[cache_key]

    # 日本の地名として検索（「, Japan」を追加）
    queries = [
        f"{location}, Japan",
        f"{location}, 日本",
        location
    ]

    for query in queries:
        result = _geocode_with_retry(query)
        if result:
            lat, lon = result
            # 日本の座標範囲内かチェック (緯度: 20-46, 経度: 122-154)
            if 20 <= lat <= 46 and 122 <= lon <= 154:
                # キャッシュに保存
                with _geocode_cache_lock:
                    _geocode_cache[cache_key] = result
                return result

    return None


def get_city_coordinates(location: str) -> Tuple[float, float]:
    """都市名から座標を取得（geopy対応版）"""
    # 1. まず既存のハードコードされた座標をチェック
    for city, coords in CITY_COORDINATES.items():
        if city.lower() in location.lower():
            return coords

    # 2. geopyでジオコーディング
    if GEOPY_AVAILABLE:
        geocoded = geocode_japanese_location(location)
        if geocoded:
            print(f"Geocoded '{location}' to {geocoded}")
            return geocoded

    # 3. フォールバック: デフォルト座標（東京）
    print(f"Warning: Could not geocode '{location}', using default coordinates")
    return config.default_coordinates


def get_city_coordinates_async(location: str) -> Tuple[float, float]:
    """非同期対応の座標取得（同期版のラッパー）"""
    return get_city_coordinates(location)

def validate_config() -> bool:
    """設定値の妥当性チェック"""
    try:
        # 重みの合計チェック
        total_weight = config.weight_astronomy + config.weight_questionnaire
        if abs(total_weight - 1.0) > 0.01:
            print(f"Warning: Astronomy + Questionnaire weights = {total_weight}, should be 1.0")
        
        # データパス存在チェック
        data_path = get_data_path()
        if not data_path.exists():
            print(f"Warning: Data path {data_path} does not exist")
            return False
        
        # BSPファイル存在チェック
        bsp_path = data_path / config.bsp_file
        if not bsp_path.exists():
            print(f"Warning: BSP file {bsp_path} does not exist")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error validating config: {e}")
        return False
"""
STRUCT CODE v2.0 - Astrological Engine
天文計算エンジン：ネイタル、プログレス、トランジットチャートの計算

Features:
- ネイタルチャート（出生図）の計算
- プログレスチャート（進行図）の計算（Secondary Progression: 1日=1年）
- トランジットチャート（経過図）の計算
- アスペクト計算（メジャーアスペクト5種）
- ハウスカスプ計算（Placidusシステム）
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from skyfield.api import load, Topos, Star
from skyfield.framelib import ecliptic_frame
import numpy as np

from ..config.struct_config import CITY_COORDINATES
from ..utils.logging_config import logger


# 天体定義
PLANETS = {
    'sun': 'sun',
    'moon': 'moon',
    'mercury': 'mercury',
    'venus': 'venus',
    'mars': 'mars',
    'jupiter': 'jupiter barycenter',
    'saturn': 'saturn barycenter',
    'uranus': 'uranus barycenter',
    'neptune': 'neptune barycenter',
    'pluto': 'pluto barycenter',
}

# 追加天体（Node、Chironなど）
# Note: Skyfieldで直接計算できないものは近似計算を使用
ADDITIONAL_POINTS = {
    'north_node': 'mean_lunar_node',  # 平均月ノード
    'chiron': 'chiron',  # キロン（2060 Chiron）
}

# 黄道十二宮
ZODIAC_SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer',
    'Leo', 'Virgo', 'Libra', 'Scorpio',
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

# エレメント
SIGN_ELEMENTS = {
    'Aries': 'fire', 'Taurus': 'earth', 'Gemini': 'air', 'Cancer': 'water',
    'Leo': 'fire', 'Virgo': 'earth', 'Libra': 'air', 'Scorpio': 'water',
    'Sagittarius': 'fire', 'Capricorn': 'earth', 'Aquarius': 'air', 'Pisces': 'water'
}

# クオリティ
SIGN_QUALITIES = {
    'Aries': 'cardinal', 'Taurus': 'fixed', 'Gemini': 'mutable', 'Cancer': 'cardinal',
    'Leo': 'fixed', 'Virgo': 'mutable', 'Libra': 'cardinal', 'Scorpio': 'fixed',
    'Sagittarius': 'mutable', 'Capricorn': 'cardinal', 'Aquarius': 'fixed', 'Pisces': 'mutable'
}

# アスペクト定義（角度、オーブ、性質）
# メジャーアスペクト
ASPECTS = {
    'conjunction': {'angle': 0, 'orb': 8, 'nature': 'fusion', 'strength': 1.0},
    'opposition': {'angle': 180, 'orb': 8, 'nature': 'tension', 'strength': 0.9},
    'trine': {'angle': 120, 'orb': 8, 'nature': 'harmony', 'strength': 0.7},
    'square': {'angle': 90, 'orb': 7, 'nature': 'challenge', 'strength': 0.8},
    'sextile': {'angle': 60, 'orb': 5, 'nature': 'opportunity', 'strength': 0.5},
}

# マイナーアスペクト（精度向上のため追加）
MINOR_ASPECTS = {
    'quincunx': {'angle': 150, 'orb': 3, 'nature': 'adjustment', 'strength': 0.5},
    'semisextile': {'angle': 30, 'orb': 2, 'nature': 'growth', 'strength': 0.25},
    'semisquare': {'angle': 45, 'orb': 2, 'nature': 'friction', 'strength': 0.35},
    'sesquiquadrate': {'angle': 135, 'orb': 2, 'nature': 'friction', 'strength': 0.35},
    'quintile': {'angle': 72, 'orb': 2, 'nature': 'talent', 'strength': 0.3},
    'biquintile': {'angle': 144, 'orb': 2, 'nature': 'talent', 'strength': 0.3},
}

# 全アスペクト（メジャー + マイナー）
ALL_ASPECTS = {**ASPECTS, **MINOR_ASPECTS}


@dataclass
class PlanetPosition:
    """天体位置"""
    planet: str
    longitude: float  # 黄経（0-360度）
    latitude: float   # 黄緯
    sign: str         # 黄道十二宮
    sign_degree: float  # サイン内度数
    house: Optional[int] = None  # ハウス
    retrograde: bool = False  # 逆行中か
    speed: Optional[float] = None  # 日速度（度/日）
    declination: Optional[float] = None  # 赤緯（Parallel計算用）

    @property
    def element(self) -> str:
        return SIGN_ELEMENTS.get(self.sign, 'unknown')

    @property
    def quality(self) -> str:
        return SIGN_QUALITIES.get(self.sign, 'unknown')

    @property
    def is_oriental(self) -> Optional[bool]:
        """太陽より東（Oriental）かどうか - 外部から太陽位置を与えて判定が必要"""
        return None  # 単体では判定不可

    def get_speed_status(self, average_speed: float) -> str:
        """惑星速度のステータスを取得"""
        if self.speed is None:
            return 'unknown'
        ratio = abs(self.speed) / average_speed if average_speed > 0 else 1.0
        if ratio < 0.1:
            return 'stationary'
        elif ratio < 0.8:
            return 'slow'
        elif ratio > 1.2:
            return 'fast'
        return 'average'


@dataclass
class Aspect:
    """アスペクト"""
    planet1: str
    planet2: str
    aspect_type: str  # conjunction, opposition, trine, square, sextile
    angle: float      # 実際の角度
    orb: float        # 許容誤差からのズレ
    nature: str       # fusion, tension, harmony, challenge, opportunity
    strength: float   # 強度（0-1）
    applying: bool = True  # 形成中（True）か分離中（False）か


@dataclass
class HouseCusps:
    """ハウスカスプ"""
    cusps: List[float]  # 12ハウスのカスプ位置（黄経）
    asc: float          # アセンダント
    mc: float           # MC
    ic: float           # IC
    dc: float           # ディセンダント


@dataclass
class Chart:
    """チャート（出生図/進行図/経過図）"""
    chart_type: str  # 'natal', 'progressed', 'transit'
    datetime: datetime
    location: Optional[Tuple[float, float]] = None  # (lat, lon)
    planets: Dict[str, PlanetPosition] = field(default_factory=dict)
    houses: Optional[HouseCusps] = None
    aspects: List[Aspect] = field(default_factory=list)
    # 追加ポイント
    north_node: Optional[PlanetPosition] = None  # ドラゴンヘッド
    south_node: Optional[PlanetPosition] = None  # ドラゴンテイル
    chiron: Optional[PlanetPosition] = None      # キロン
    part_of_fortune: Optional[float] = None      # パート・オブ・フォーチュン（黄経）
    moon_phase: Optional[float] = None           # 月相（0-360度、太陽からの角度）
    is_day_chart: Optional[bool] = None          # 昼のチャートかどうか


class AstrologicalEngine:
    """
    天文計算エンジン
    """

    def __init__(self):
        self.ts = load.timescale()
        self.eph = None
        self._load_ephemeris()
        logger.info("AstrologicalEngine initialized")

    def _load_ephemeris(self):
        """エフェメリスファイルの読み込み"""
        try:
            self.eph = load('de421.bsp')
            logger.info("Ephemeris de421.bsp loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load ephemeris: {e}")
            raise

    def _get_location(self, birth_place: str) -> Tuple[float, float]:
        """場所名から座標を取得"""
        coords = CITY_COORDINATES.get(birth_place.lower())
        if coords:
            return coords['lat'], coords['lon']
        # デフォルトは東京
        return 35.6762, 139.6503

    def _longitude_to_sign(self, longitude: float) -> Tuple[str, float]:
        """黄経からサインと度数を計算"""
        longitude = longitude % 360
        sign_index = int(longitude / 30)
        sign_degree = longitude % 30
        return ZODIAC_SIGNS[sign_index], sign_degree

    def _calculate_planet_position(self, planet_name: str, t, observer=None,
                                     calculate_speed: bool = True) -> PlanetPosition:
        """天体位置の計算（速度・赤緯含む）"""
        earth = self.eph['earth']

        if planet_name == 'sun':
            target = self.eph['sun']
        elif planet_name == 'moon':
            target = self.eph['moon']
        else:
            target = self.eph[PLANETS[planet_name]]

        # 地心座標での天体位置
        if observer:
            astrometric = (earth + observer).at(t).observe(target)
        else:
            astrometric = earth.at(t).observe(target)

        # 黄道座標に変換
        lat, lon, distance = astrometric.frame_latlon(ecliptic_frame)

        longitude = lon.degrees
        latitude = lat.degrees
        sign, sign_degree = self._longitude_to_sign(longitude)

        # 赤緯（Parallel/Contraparallel計算用）
        ra, dec, _ = astrometric.radec()
        declination = dec.degrees

        # 速度計算（前後1時間での差分）
        speed = None
        retrograde = False
        if calculate_speed:
            try:
                # 1時間後の位置
                t_future = self.ts.tt_jd(t.tt + 1/24)  # 1時間 = 1/24日
                if observer:
                    future_astrometric = (earth + observer).at(t_future).observe(target)
                else:
                    future_astrometric = earth.at(t_future).observe(target)
                _, future_lon, _ = future_astrometric.frame_latlon(ecliptic_frame)

                # 日速度に変換
                lon_diff = future_lon.degrees - longitude
                # 360度境界をまたぐ場合の処理
                if lon_diff > 180:
                    lon_diff -= 360
                elif lon_diff < -180:
                    lon_diff += 360

                speed = lon_diff * 24  # 1時間の差分を24倍して日速度に
                retrograde = speed < 0
            except Exception:
                pass

        return PlanetPosition(
            planet=planet_name,
            longitude=longitude,
            latitude=latitude,
            sign=sign,
            sign_degree=sign_degree,
            retrograde=retrograde,
            speed=speed,
            declination=declination
        )

    def _calculate_lunar_node(self, t) -> Tuple[float, float]:
        """
        月のノード（ドラゴンヘッド/テイル）を計算

        平均ノード（Mean Node）を使用
        真のノード（True Node）は月軌道の摂動で揺れるため

        Returns:
            (north_node_longitude, south_node_longitude)
        """
        # JD2000からの経過ユリウス世紀
        jd = t.tt
        T = (jd - 2451545.0) / 36525.0

        # 平均月ノードの黄経（Meeus式）
        # 単位: 度
        omega = 125.0445479 - 1934.1362891 * T + 0.0020754 * T**2 + T**3 / 467441.0

        north_node = omega % 360
        south_node = (north_node + 180) % 360

        return north_node, south_node

    def _calculate_chiron(self, t, observer=None) -> Optional[PlanetPosition]:
        """
        キロン（2060 Chiron）の位置を計算

        Note: de421.bspにはキロンは含まれていないため、
        簡易的な軌道要素からの計算を行う
        """
        try:
            # キロンの軌道要素（J2000.0エポック、簡易版）
            # 周期約50.7年、遠日点土星軌道付近、近日点土星と天王星の間
            jd = t.tt
            T = (jd - 2451545.0) / 36525.0

            # 平均黄経（非常に簡略化した計算）
            # 元期: 2000年1月1日のキロン黄経約269度
            # 平均日運動: 約0.0195度/日
            days_since_j2000 = jd - 2451545.0
            mean_longitude = (269.0 + 0.0195 * days_since_j2000) % 360

            sign, sign_degree = self._longitude_to_sign(mean_longitude)

            return PlanetPosition(
                planet='chiron',
                longitude=mean_longitude,
                latitude=0.0,  # 簡略化
                sign=sign,
                sign_degree=sign_degree
            )
        except Exception as e:
            logger.warning(f"Chiron calculation failed: {e}")
            return None

    def _calculate_part_of_fortune(self, asc: float, sun_lon: float,
                                    moon_lon: float, is_day: bool) -> float:
        """
        パート・オブ・フォーチュン（運命の部分）を計算

        昼チャート: ASC + Moon - Sun
        夜チャート: ASC + Sun - Moon
        """
        if is_day:
            pof = asc + moon_lon - sun_lon
        else:
            pof = asc + sun_lon - moon_lon

        return pof % 360

    def _calculate_moon_phase(self, sun_lon: float, moon_lon: float) -> float:
        """
        月相を計算（太陽からの角度）

        0度: 新月
        90度: 上弦
        180度: 満月
        270度: 下弦
        """
        phase = (moon_lon - sun_lon) % 360
        return phase

    def _is_void_of_course(self, moon: PlanetPosition,
                           planets: Dict[str, PlanetPosition],
                           houses: Optional[HouseCusps]) -> bool:
        """
        月がVoid of Course（ボイド）かどうかを判定

        月が現在のサインを離れるまでに
        他の惑星とメジャーアスペクトを形成しないかどうか
        """
        if not moon:
            return False

        moon_sign = moon.sign
        moon_degree = moon.sign_degree

        # 月がサインを離れるまでの残り度数
        degrees_to_leave = 30 - moon_degree

        # メジャーアスペクトの角度
        major_aspect_angles = [0, 60, 90, 120, 180]

        for planet_name, planet_pos in planets.items():
            if planet_name == 'moon':
                continue

            # 現在の角度差
            diff = abs(moon.longitude - planet_pos.longitude)
            if diff > 180:
                diff = 360 - diff

            # 月が進んだ場合の角度差をシミュレート
            for future_degree in range(int(moon_degree), 30):
                future_moon_lon = (moon.longitude - moon_degree + future_degree) % 360
                future_diff = abs(future_moon_lon - planet_pos.longitude)
                if future_diff > 180:
                    future_diff = 360 - future_diff

                # メジャーアスペクトを形成するか
                for aspect_angle in major_aspect_angles:
                    if abs(future_diff - aspect_angle) <= 8:  # オーブ8度
                        return False  # アスペクト形成するのでVOCではない

        return True  # サインを離れるまでアスペクトなし = VOC

    def _calculate_parallel_aspects(self, planets: Dict[str, PlanetPosition]) -> List[Dict]:
        """
        Parallel（同緯）とContraparallel（反対緯）のアスペクトを計算

        赤緯が同じ（±1度）または反対（符号が逆で絶対値が同じ）
        """
        parallels = []
        planet_list = list(planets.items())

        for i, (p1_name, p1) in enumerate(planet_list):
            if p1.declination is None:
                continue
            for p2_name, p2 in planet_list[i+1:]:
                if p2.declination is None:
                    continue

                # Parallel（同緯）
                if abs(p1.declination - p2.declination) <= 1.0:
                    parallels.append({
                        'planet1': p1_name,
                        'planet2': p2_name,
                        'type': 'parallel',
                        'declination1': p1.declination,
                        'declination2': p2.declination
                    })
                # Contraparallel（反対緯）
                elif abs(p1.declination + p2.declination) <= 1.0:
                    parallels.append({
                        'planet1': p1_name,
                        'planet2': p2_name,
                        'type': 'contraparallel',
                        'declination1': p1.declination,
                        'declination2': p2.declination
                    })

        return parallels

    def _calculate_aspects(self, planets: Dict[str, PlanetPosition],
                           include_minor: bool = True) -> List[Aspect]:
        """
        アスペクト計算

        Args:
            planets: 惑星位置の辞書
            include_minor: マイナーアスペクトも含めるかどうか（デフォルト: True）

        Returns:
            List[Aspect]: 検出されたアスペクトのリスト
        """
        aspects = []
        planet_names = list(planets.keys())

        # 使用するアスペクト定義を選択
        aspect_definitions = ALL_ASPECTS if include_minor else ASPECTS

        for i, p1_name in enumerate(planet_names):
            for p2_name in planet_names[i+1:]:
                p1 = planets[p1_name]
                p2 = planets[p2_name]

                # 角度差を計算
                diff = abs(p1.longitude - p2.longitude)
                if diff > 180:
                    diff = 360 - diff

                # 各アスペクトをチェック
                for aspect_name, aspect_def in aspect_definitions.items():
                    orb = abs(diff - aspect_def['angle'])
                    if orb <= aspect_def['orb']:
                        # アスペクトが成立
                        # 強度はオーブが小さいほど強い
                        strength = aspect_def['strength'] * (1 - orb / aspect_def['orb'])

                        aspects.append(Aspect(
                            planet1=p1_name,
                            planet2=p2_name,
                            aspect_type=aspect_name,
                            angle=diff,
                            orb=orb,
                            nature=aspect_def['nature'],
                            strength=strength
                        ))

        return aspects

    def _calculate_houses(self, t, lat: float, lon: float) -> HouseCusps:
        """ハウスカスプ計算（簡易版：等分ハウス + ASC/MC計算）"""
        # LST（地方恒星時）の計算
        jd = t.tt

        # グリニッジ恒星時
        T = (jd - 2451545.0) / 36525.0
        gst = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
        gst += 0.000387933 * T * T - T * T * T / 38710000.0
        gst = gst % 360

        # 地方恒星時
        lst = (gst + lon) % 360

        # ASC計算（簡易版）
        # tan(ASC) = cos(LST) / (-sin(LST)*cos(ε) - tan(lat)*sin(ε))
        eps = 23.4393  # 黄道傾斜角（度）
        eps_rad = math.radians(eps)
        lat_rad = math.radians(lat)
        lst_rad = math.radians(lst)

        y = math.cos(lst_rad)
        x = -math.sin(lst_rad) * math.cos(eps_rad) - math.tan(lat_rad) * math.sin(eps_rad)
        asc = math.degrees(math.atan2(y, x))
        asc = (asc + 180) % 360  # 調整

        # MC計算
        # tan(MC) = tan(LST) / cos(ε)
        mc = math.degrees(math.atan2(math.sin(lst_rad), math.cos(lst_rad) * math.cos(eps_rad)))
        mc = mc % 360

        # IC, DC
        ic = (mc + 180) % 360
        dc = (asc + 180) % 360

        # 等分ハウス（ASCを起点に30度ずつ）
        cusps = [(asc + i * 30) % 360 for i in range(12)]

        return HouseCusps(
            cusps=cusps,
            asc=asc,
            mc=mc,
            ic=ic,
            dc=dc
        )

    def _assign_houses(self, planets: Dict[str, PlanetPosition], houses: HouseCusps):
        """天体にハウスを割り当て"""
        for planet in planets.values():
            lon = planet.longitude
            for i in range(12):
                cusp1 = houses.cusps[i]
                cusp2 = houses.cusps[(i + 1) % 12]

                # カスプをまたぐ場合の処理
                if cusp1 > cusp2:  # 360度をまたぐ
                    if lon >= cusp1 or lon < cusp2:
                        planet.house = i + 1
                        break
                else:
                    if cusp1 <= lon < cusp2:
                        planet.house = i + 1
                        break

    def calculate_natal_chart(
        self,
        birthdate: str,
        birth_time: Optional[str],
        birth_place: str
    ) -> Chart:
        """
        ネイタルチャート（出生図）の計算

        Args:
            birthdate: 生年月日 (YYYY-MM-DD)
            birth_time: 出生時刻 (HH:MM) - Noneの場合は正午
            birth_place: 出生地

        Returns:
            Chart: ネイタルチャート
        """
        # 日時のパース
        if birth_time:
            dt = datetime.strptime(f"{birthdate} {birth_time}", "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(f"{birthdate} 12:00", "%Y-%m-%d %H:%M")

        # 座標取得
        lat, lon = self._get_location(birth_place)
        observer = Topos(latitude_degrees=lat, longitude_degrees=lon)

        # Skyfield時刻オブジェクト
        t = self.ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute)

        # 天体位置計算
        planets = {}
        for planet_name in PLANETS.keys():
            try:
                planets[planet_name] = self._calculate_planet_position(planet_name, t, observer)
            except Exception as e:
                logger.warning(f"Failed to calculate {planet_name}: {e}")

        # ハウス計算
        houses = self._calculate_houses(t, lat, lon)

        # ハウス割り当て
        self._assign_houses(planets, houses)

        # アスペクト計算
        aspects = self._calculate_aspects(planets)

        # === 追加ポイントの計算 ===

        # 月のノード（ドラゴンヘッド/テイル）
        north_node_lon, south_node_lon = self._calculate_lunar_node(t)
        north_node_sign, north_node_degree = self._longitude_to_sign(north_node_lon)
        south_node_sign, south_node_degree = self._longitude_to_sign(south_node_lon)

        north_node = PlanetPosition(
            planet='north_node',
            longitude=north_node_lon,
            latitude=0.0,
            sign=north_node_sign,
            sign_degree=north_node_degree
        )
        south_node = PlanetPosition(
            planet='south_node',
            longitude=south_node_lon,
            latitude=0.0,
            sign=south_node_sign,
            sign_degree=south_node_degree
        )

        # ノードにもハウスを割り当て
        for node in [north_node, south_node]:
            lon_val = node.longitude
            for i in range(12):
                cusp1 = houses.cusps[i]
                cusp2 = houses.cusps[(i + 1) % 12]
                if cusp1 > cusp2:
                    if lon_val >= cusp1 or lon_val < cusp2:
                        node.house = i + 1
                        break
                else:
                    if cusp1 <= lon_val < cusp2:
                        node.house = i + 1
                        break

        # キロン
        chiron = self._calculate_chiron(t, observer)
        if chiron:
            # キロンにもハウスを割り当て
            for i in range(12):
                cusp1 = houses.cusps[i]
                cusp2 = houses.cusps[(i + 1) % 12]
                if cusp1 > cusp2:
                    if chiron.longitude >= cusp1 or chiron.longitude < cusp2:
                        chiron.house = i + 1
                        break
                else:
                    if cusp1 <= chiron.longitude < cusp2:
                        chiron.house = i + 1
                        break

        # 昼/夜チャートの判定
        is_day_chart = False
        if 'sun' in planets:
            sun_house = planets['sun'].house
            if sun_house and sun_house >= 7:
                is_day_chart = True
            elif houses:
                # ハウスがない場合はASCと太陽位置で判定
                sun_lon = planets['sun'].longitude
                asc = houses.asc
                dc = (asc + 180) % 360
                if asc < dc:
                    is_day_chart = asc <= sun_lon <= dc
                else:
                    is_day_chart = sun_lon >= asc or sun_lon <= dc

        # パート・オブ・フォーチュン
        part_of_fortune = None
        if 'sun' in planets and 'moon' in planets and houses:
            part_of_fortune = self._calculate_part_of_fortune(
                houses.asc,
                planets['sun'].longitude,
                planets['moon'].longitude,
                is_day_chart
            )

        # 月相
        moon_phase = None
        if 'sun' in planets and 'moon' in planets:
            moon_phase = self._calculate_moon_phase(
                planets['sun'].longitude,
                planets['moon'].longitude
            )

        return Chart(
            chart_type='natal',
            datetime=dt,
            location=(lat, lon),
            planets=planets,
            houses=houses,
            aspects=aspects,
            north_node=north_node,
            south_node=south_node,
            chiron=chiron,
            part_of_fortune=part_of_fortune,
            moon_phase=moon_phase,
            is_day_chart=is_day_chart
        )

    def calculate_progressed_chart(
        self,
        natal_chart: Chart,
        target_date: datetime
    ) -> Chart:
        """
        プログレスチャート（進行図）の計算
        Secondary Progression: 1日 = 1年

        Args:
            natal_chart: ネイタルチャート
            target_date: 進行先の日付

        Returns:
            Chart: プログレスチャート
        """
        natal_dt = natal_chart.datetime

        # 経過年数を計算
        years_elapsed = (target_date - natal_dt).days / 365.25

        # 進行日数（1年 = 1日）
        progressed_days = years_elapsed

        # 進行後の日時
        progressed_dt = natal_dt + timedelta(days=progressed_days)

        # Skyfield時刻オブジェクト
        t = self.ts.utc(
            progressed_dt.year, progressed_dt.month, progressed_dt.day,
            progressed_dt.hour, progressed_dt.minute
        )

        # 天体位置計算（内惑星のみ進行させる）
        # 外惑星（木星以遠）は動きが遅いのでネイタルとほぼ同じ
        planets = {}
        progressed_planets = ['sun', 'moon', 'mercury', 'venus', 'mars']

        if natal_chart.location:
            lat, lon = natal_chart.location
            observer = Topos(latitude_degrees=lat, longitude_degrees=lon)
        else:
            observer = None

        for planet_name in PLANETS.keys():
            try:
                if planet_name in progressed_planets:
                    planets[planet_name] = self._calculate_planet_position(planet_name, t, observer)
                else:
                    # 外惑星はネイタルの位置を使用
                    planets[planet_name] = natal_chart.planets.get(planet_name)
            except Exception as e:
                logger.warning(f"Failed to calculate progressed {planet_name}: {e}")

        # プログレスとネイタル間のアスペクト計算
        aspects = self._calculate_cross_aspects(planets, natal_chart.planets)

        return Chart(
            chart_type='progressed',
            datetime=target_date,
            location=natal_chart.location,
            planets=planets,
            houses=natal_chart.houses,  # ハウスはネイタルを継承
            aspects=aspects
        )

    def calculate_transit_chart(self, target_date: datetime) -> Chart:
        """
        トランジットチャート（経過図）の計算

        Args:
            target_date: 対象日時

        Returns:
            Chart: トランジットチャート
        """
        t = self.ts.utc(
            target_date.year, target_date.month, target_date.day,
            target_date.hour, target_date.minute
        )

        # 天体位置計算
        planets = {}
        for planet_name in PLANETS.keys():
            try:
                planets[planet_name] = self._calculate_planet_position(planet_name, t)
            except Exception as e:
                logger.warning(f"Failed to calculate transit {planet_name}: {e}")

        return Chart(
            chart_type='transit',
            datetime=target_date,
            planets=planets,
            aspects=[]  # トランジット内アスペクトは通常使わない
        )

    def _calculate_cross_aspects(
        self,
        planets1: Dict[str, PlanetPosition],
        planets2: Dict[str, PlanetPosition]
    ) -> List[Aspect]:
        """
        2つのチャート間のアスペクト計算
        （プログレス-ネイタル、トランジット-ネイタル用）
        """
        aspects = []

        for p1_name, p1 in planets1.items():
            if p1 is None:
                continue
            for p2_name, p2 in planets2.items():
                if p2 is None:
                    continue

                # 角度差を計算
                diff = abs(p1.longitude - p2.longitude)
                if diff > 180:
                    diff = 360 - diff

                # 各アスペクトをチェック
                for aspect_name, aspect_def in ASPECTS.items():
                    orb = abs(diff - aspect_def['angle'])
                    if orb <= aspect_def['orb']:
                        strength = aspect_def['strength'] * (1 - orb / aspect_def['orb'])

                        aspects.append(Aspect(
                            planet1=f"{p1_name}(tr/pr)",  # トランジット/プログレス側
                            planet2=f"{p2_name}(n)",      # ネイタル側
                            aspect_type=aspect_name,
                            angle=diff,
                            orb=orb,
                            nature=aspect_def['nature'],
                            strength=strength
                        ))

        return aspects

    def calculate_transit_to_natal_aspects(
        self,
        transit_chart: Chart,
        natal_chart: Chart
    ) -> List[Aspect]:
        """
        トランジット天体とネイタル天体間のアスペクト計算
        """
        return self._calculate_cross_aspects(transit_chart.planets, natal_chart.planets)

    def get_current_major_transits(
        self,
        natal_chart: Chart,
        target_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        現在の主要トランジットを取得
        外惑星（土星、天王星、海王星、冥王星）のネイタルへの影響
        """
        if target_date is None:
            target_date = datetime.now()

        transit_chart = self.calculate_transit_chart(target_date)
        aspects = self.calculate_transit_to_natal_aspects(transit_chart, natal_chart)

        # 外惑星のアスペクトのみフィルタ
        outer_planets = ['saturn', 'uranus', 'neptune', 'pluto']
        major_transits = []

        for aspect in aspects:
            transit_planet = aspect.planet1.replace('(tr/pr)', '').strip()
            if transit_planet in outer_planets:
                major_transits.append({
                    'transit_planet': transit_planet,
                    'natal_planet': aspect.planet2.replace('(n)', '').strip(),
                    'aspect': aspect.aspect_type,
                    'nature': aspect.nature,
                    'strength': aspect.strength,
                    'orb': aspect.orb
                })

        # 強度でソート
        major_transits.sort(key=lambda x: x['strength'], reverse=True)

        return major_transits


# シングルトンインスタンス
_engine_instance = None

def get_astrological_engine() -> AstrologicalEngine:
    """AstrologicalEngineのシングルトンインスタンスを取得"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AstrologicalEngine()
    return _engine_instance

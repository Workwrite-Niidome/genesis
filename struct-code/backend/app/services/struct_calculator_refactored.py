"""
STRUCT CODE Ultimate - Refactored Version
完全にリファクタリングされた内面構造解析システム

Features:
- 設定の外部化
- 包括的なエラーハンドリング
- 詳細なログ機能
- 型安全性の向上
- コードの可読性向上
"""

import json
import hashlib
import math
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from skyfield.api import load, Topos
from skyfield.framelib import ecliptic_frame

from ..models.schemas import QuestionResponse, DiagnosisResponse, TypeDetail, AnswerData
from ..config.struct_config import (
    config, CITY_COORDINATES, ZODIAC_SIGNS, ZODIAC_ELEMENTS,
    ASPECT_DEFINITIONS, CHOICE_VALUES, PLANETARY_ARCHETYPES,
    get_data_path, get_city_coordinates, validate_config
)
from ..utils.logging_config import (
    logger, log_exception, log_performance, log_diagnosis_context,
    log_system_info, log_diagnosis_start, log_diagnosis_complete,
    AstrologicalCalculationError, TypeDeterminationError,
    ConfigurationError, DataValidationError
)

# 占星術エンジン（精密計算用）
try:
    from .astrological_engine import get_astrological_engine, Chart
    ASTRO_ENGINE_AVAILABLE = True
except ImportError:
    ASTRO_ENGINE_AVAILABLE = False
    logger.warning("AstrologicalEngine not available")

# 動的タイプ分類器（v4.0）- 精密な軸計算に使用
try:
    from .dynamic_type_classifier import get_dynamic_classifier, DynamicClassificationResult
    DYNAMIC_CLASSIFIER_AVAILABLE = True
except ImportError:
    DYNAMIC_CLASSIFIER_AVAILABLE = False
    logger.warning("DynamicTypeClassifier not available, using static classification")

class StructCalculatorRefactored:
    """
    STRUCT CODE Ultimate - Refactored Version
    設定外部化・エラーハンドリング・ログ強化版
    """
    
    def __init__(self):
        self.data_path = get_data_path()
        self.questions = {}
        self.desc_db = {}
        self.stmap = {}
        self.ts = load.timescale()
        self.eph = None
        
        # 軸定義（設定から取得）
        self.axis_definitions = self._build_axis_definitions()
        
        # タイプ定義
        self.struct_types = self._build_struct_types()
        
        self._last_type_candidates = []  # TOP3タイプ候補

        # 占星術エンジン（精密計算用）
        self._astro_engine = None
        if ASTRO_ENGINE_AVAILABLE:
            try:
                self._astro_engine = get_astrological_engine()
                logger.info("AstrologicalEngine integrated for precise calculations")
            except Exception as e:
                logger.warning(f"Failed to initialize AstrologicalEngine: {e}")

        # 動的タイプ分類器（v4.0）- 精密な軸計算に使用
        self._dynamic_classifier = None
        if DYNAMIC_CLASSIFIER_AVAILABLE:
            try:
                self._dynamic_classifier = get_dynamic_classifier()
                logger.info("DynamicTypeClassifier integrated for precise axis calculation")
            except Exception as e:
                logger.warning(f"Failed to initialize DynamicTypeClassifier: {e}")

        logger.info("StructCalculatorRefactored initialized")
    
    def _build_axis_definitions(self) -> Dict[str, Dict]:
        """軸定義の構築"""
        return {
            '起動軸': {
                'index': 0,
                'essence': '行動を起こすエネルギーとタイミング',
                'high_traits': ['自発的', '積極的', '即座の行動'],
                'low_traits': ['慎重', '準備重視', '外的トリガー待ち'],
                'planetary_rulers': ['sun', 'mars', 'jupiter'],
                'houses': [1, 10],
                'element_modifiers': {'fire': 1.3, 'earth': 0.8, 'air': 1.0, 'water': 0.9}
            },
            '判断軸': {
                'index': 1,
                'essence': '意思決定の方法と思考プロセス',
                'high_traits': ['論理的', '分析的', '構造的'],
                'low_traits': ['直感的', '感覚的', '流動的'],
                'planetary_rulers': ['mercury', 'saturn', 'uranus'],
                'houses': [3, 6, 9],
                'element_modifiers': {'air': 1.4, 'earth': 1.1, 'fire': 0.9, 'water': 0.7}
            },
            '選択軸': {
                'index': 2,
                'essence': '価値判断と優先順位の基準',
                'high_traits': ['理想追求', '価値重視', '美的感覚'],
                'low_traits': ['実利的', '効率的', '現実的'],
                'planetary_rulers': ['venus', 'jupiter', 'neptune'],
                'houses': [2, 7],
                'element_modifiers': {'water': 1.2, 'earth': 1.1, 'air': 0.9, 'fire': 1.0}
            },
            '共鳴軸': {
                'index': 3,
                'essence': '他者との関係性と共感能力',
                'high_traits': ['深い共感', '協調', '相互理解'],
                'low_traits': ['独立的', '自律的', '境界明確'],
                'planetary_rulers': ['moon', 'venus', 'neptune'],
                'houses': [4, 7, 11],
                'element_modifiers': {'water': 1.4, 'air': 1.0, 'earth': 0.8, 'fire': 0.8}
            },
            '自覚軸': {
                'index': 4,
                'essence': '自己認識と内省の深さ',
                'high_traits': ['深い内省', '自己理解', '意識的'],
                'low_traits': ['外向的', '実践的', '無意識的'],
                'planetary_rulers': ['sun', 'saturn', 'pluto'],
                'houses': [8, 12],
                'element_modifiers': {'water': 1.3, 'earth': 1.1, 'air': 0.9, 'fire': 0.8}
            }
        }
    
    def _build_struct_types(self) -> Dict[str, Dict]:
        """STRUCT TYPE定義の構築

        ベクトル調整 v3.0 (2024-12-01):
        - v2からさらに強化: H値(0.70-0.78)→(0.65-0.72)
        - L値(0.28-0.35)→(0.32-0.40)
        - バランス型(CMPL/ADPT)をさらに中央寄りに調整
        - 目標: バランス型比率40%以下
        """
        return {
            # 活性化軸 (AC)
            'ACPU': {
                'name': 'マーズ',
                'archetype': '戦士',
                'core_pattern': '瞬間的な爆発的起動',
                'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'L', '共鳴': 'L', '自覚': 'M'},
                'vector': [0.72, 0.35, 0.35, 0.35, 0.48],
                'mission': '困難な状況を突破し、新たな道を切り開く'
            },
            'ACBL': {
                'name': 'ソーラー',
                'archetype': '太陽',
                'core_pattern': '継続的で安定した活性化',
                'axis_signature': {'起動': 'H', '判断': 'M', '選択': 'L', '共鳴': 'M', '自覚': 'L'},
                'vector': [0.68, 0.52, 0.35, 0.48, 0.38],
                'mission': '安定的なエネルギーで周囲を温かく照らす'
            },
            'ACCV': {
                'name': 'フレア',
                'archetype': '変革者',
                'core_pattern': '革新的な爆発的エネルギー',
                'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'H', '共鳴': 'L', '自覚': 'M'},
                'vector': [0.68, 0.35, 0.68, 0.35, 0.48],
                'mission': '既存の枠組みを打破し、新しい可能性を創造する'
            },
            'ACJG': {
                'name': 'パルサー',
                'archetype': '調整者',
                'core_pattern': '規則的で予測可能なリズム',
                'axis_signature': {'起動': 'H', '判断': 'H', '選択': 'L', '共鳴': 'L', '自覚': 'M'},
                'vector': [0.66, 0.66, 0.36, 0.36, 0.50],
                'mission': '組織に秩序と安定性をもたらす'
            },
            'ACRN': {
                'name': 'レディエント',
                'archetype': '感染源',
                'core_pattern': 'エネルギーの伝播と拡散',
                'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'M', '共鳴': 'H', '自覚': 'M'},
                'vector': [0.68, 0.35, 0.50, 0.68, 0.48],
                'mission': '周囲にポジティブな影響を与え、活力を伝える'
            },
            'ACCP': {
                'name': 'フォーカス',
                'archetype': '専門家',
                'core_pattern': '集中的で深い掘り下げ',
                'axis_signature': {'起動': 'H', '判断': 'H', '選択': 'M', '共鳴': 'L', '自覚': 'H'},
                'vector': [0.66, 0.66, 0.50, 0.35, 0.68],
                'mission': '専門分野で卓越し、深い価値を創造する'
            },
            
            # 判断軸 (JD)
            'JDPU': {
                'name': 'マーキュリー',
                'archetype': '知性の化身',
                'core_pattern': '論理的分析と情報統合',
                'axis_signature': {'起動': 'L', '判断': 'H', '選択': 'L', '共鳴': 'L', '自覚': 'M'},
                'vector': [0.35, 0.72, 0.35, 0.35, 0.50],
                'mission': '複雑な問題を論理的に解決し、明確な方向性を示す'
            },
            'JDRA': {
                'name': 'クリスタル',
                'archetype': '洞察者',
                'core_pattern': '透明で純粋な判断',
                'axis_signature': {'起動': 'L', '判断': 'H', '選択': 'L', '共鳴': 'M', '自覚': 'H'},
                'vector': [0.35, 0.68, 0.35, 0.48, 0.68],
                'mission': '曇りのない視点で真実を見抜く'
            },
            'JDCP': {
                'name': 'コスモス',
                'archetype': '戦略家',
                'core_pattern': '全体俯瞰と統合的思考',
                'axis_signature': {'起動': 'M', '判断': 'H', '選択': 'M', '共鳴': 'M', '自覚': 'H'},
                'vector': [0.50, 0.66, 0.50, 0.50, 0.66],
                'mission': '大きな視点で全体を統合し、方向性を定める'
            },
            'JDCV': {
                'name': 'マトリックス',
                'archetype': '知識の建築家',
                'core_pattern': '多次元的な情報統合',
                'axis_signature': {'起動': 'M', '判断': 'H', '選択': 'H', '共鳴': 'L', '自覚': 'H'},
                'vector': [0.48, 0.68, 0.66, 0.35, 0.68],
                'mission': '複雑な知識を体系化し、新たな理解を創造する'
            },
            
            # 選択軸 (CH)
            'CHRA': {
                'name': 'ヴィーナス',
                'archetype': '理想主義者',
                'core_pattern': '価値と美の追求',
                'axis_signature': {'起動': 'L', '判断': 'L', '選択': 'H', '共鳴': 'M', '自覚': 'M'},
                'vector': [0.35, 0.35, 0.72, 0.52, 0.50],
                'mission': '美しく価値あるものを選び、理想を実現する'
            },
            'CHJA': {
                'name': 'ディアナ',
                'archetype': '芸術家',
                'core_pattern': '優雅な美意識',
                'axis_signature': {'起動': 'L', '判断': 'M', '選択': 'H', '共鳴': 'L', '自覚': 'H'},
                'vector': [0.35, 0.48, 0.68, 0.35, 0.68],
                'mission': '洗練された美しさを追求し、質の高い作品を創造する'
            },
            'CHAT': {
                'name': 'ユーレカ',
                'archetype': 'イノベーター',
                'core_pattern': '創造的な価値発見',
                'axis_signature': {'起動': 'H', '判断': 'L', '選択': 'H', '共鳴': 'M', '自覚': 'L'},
                'vector': [0.66, 0.35, 0.72, 0.48, 0.35],
                'mission': '新しい価値を発見し、革新的な選択を行う'
            },
            'CHJG': {
                'name': 'アテナ',
                'archetype': '守護者',
                'core_pattern': '慎重で戦略的な選択',
                'axis_signature': {'起動': 'L', '判断': 'H', '選択': 'H', '共鳴': 'L', '自覚': 'M'},
                'vector': [0.35, 0.66, 0.68, 0.35, 0.50],
                'mission': 'リスクを管理し、安全で確実な選択を行う'
            },
            'CHJC': {
                'name': 'オプティマス',
                'archetype': '選択のマスター',
                'core_pattern': '最適化された選択',
                'axis_signature': {'起動': 'M', '判断': 'H', '選択': 'H', '共鳴': 'M', '自覚': 'L'},
                'vector': [0.50, 0.66, 0.68, 0.48, 0.35],
                'mission': '複雑な状況で最適な選択を見つけ出す'
            },
            
            # 共鳴軸 (RS)
            'RSAW': {
                'name': 'ルナ',
                'archetype': '癒し手',
                'core_pattern': '深い共感と癒し',
                'axis_signature': {'起動': 'L', '判断': 'L', '選択': 'M', '共鳴': 'H', '自覚': 'H'},
                'vector': [0.35, 0.35, 0.48, 0.72, 0.68],
                'mission': '他者の心に寄り添い、癒しと成長を支援する'
            },
            'RSCV': {
                'name': 'ミューズ',
                'archetype': 'インスピレーター',
                'core_pattern': '芸術的な感情表現',
                'axis_signature': {'起動': 'M', '判断': 'L', '選択': 'H', '共鳴': 'H', '自覚': 'M'},
                'vector': [0.48, 0.35, 0.66, 0.68, 0.50],
                'mission': '美しい表現を通じて人々の心を動かす'
            },
            'RSAB': {
                'name': 'ボンド',
                'archetype': '結束者',
                'core_pattern': 'チームの絆と協力',
                'axis_signature': {'起動': 'H', '判断': 'M', '選択': 'M', '共鳴': 'H', '自覚': 'L'},
                'vector': [0.66, 0.48, 0.48, 0.68, 0.35],
                'mission': 'チームの結束を高め、協力的な環境を創る'
            },
            'RSBL': {
                'name': 'ハーモニー',
                'archetype': '調停者',
                'core_pattern': '調和と統合',
                'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'H', '自覚': 'H'},
                'vector': [0.50, 0.50, 0.50, 0.66, 0.66],
                'mission': '対立を調和に変え、全体の統合を実現する'
            },
            
            # 認識軸 (AW)
            'AWAB': {
                'name': 'パノラマ',
                'archetype': '俯瞰者',
                'core_pattern': '広い視野と全体把握',
                'axis_signature': {'起動': 'H', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'H'},
                'vector': [0.66, 0.50, 0.48, 0.48, 0.68],
                'mission': '全体像を把握し、包括的な理解を提供する'
            },
            'AWRN': {
                'name': 'レーダー',
                'archetype': '感知者',
                'core_pattern': '微細な変化の感知',
                'axis_signature': {'起動': 'M', '判断': 'L', '選択': 'M', '共鳴': 'H', '自覚': 'H'},
                'vector': [0.48, 0.35, 0.48, 0.66, 0.68],
                'mission': '環境の変化を早期に察知し、適切な対応を促す'
            },
            
            # バランス軸 (BL) - 新規追加
            'BLNC': {
                'name': 'センター',
                'archetype': '調和者',
                'core_pattern': '全軸均衡型の安定',
                'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'M'},
                'vector': [0.50, 0.50, 0.50, 0.50, 0.50],
                'mission': '全ての要素を均等に活かし、安定した中心軸を保つ'
            },
            'CMPL': {
                'name': 'シナジー',
                'archetype': '統合者',
                'core_pattern': '複数軸の複合的活用',
                'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'M'},
                'vector': [0.55, 0.55, 0.55, 0.55, 0.45],
                'mission': '複数の強みを組み合わせ、相乗効果を生み出す'
            },
            'ADPT': {
                'name': 'カメレオン',
                'archetype': '適応者',
                'core_pattern': '状況対応型の柔軟性',
                'axis_signature': {'起動': 'M', '判断': 'M', '選択': 'M', '共鳴': 'M', '自覚': 'M'},
                'vector': [0.45, 0.45, 0.55, 0.55, 0.50],
                'mission': '状況に応じて柔軟に対応し、最適な形に変化する'
            }
        }
    
    @log_exception()
    @log_performance(threshold_seconds=2.0)
    async def initialize(self) -> None:
        """システム初期化"""
        logger.info(f"Initializing STRUCT CODE Refactored with data path: {self.data_path}")
        
        # 設定検証
        if not validate_config():
            raise ConfigurationError("Configuration validation failed")
        
        # JSONデータ読み込み
        self.questions = self._load_json("question_full_map.json")
        self.desc_db = self._load_json("DESCRIPTION_with_vectors_theoretical.json")
        self.stmap = self._load_json("SymbolicTimeMap.json")
        
        # 高度分析用データ読み込み
        self.drift_profiles = {}  # Optional data file not included
        self.field_weights = self._load_json("StructFieldWeight.json")
        
        # 天体暦読み込み
        bsp_path = self.data_path / config.bsp_file
        if not bsp_path.exists():
            raise ConfigurationError(f"BSP file not found: {bsp_path}")
        
        self.eph = load(str(bsp_path))
        
        log_system_info()
        logger.info(f"Loaded {len(self.questions)} questions")
        logger.info(f"Loaded {len(self.struct_types)} optimized types")
        logger.info("STRUCT CODE Refactored initialized successfully")
    
    def _load_json(self, filename: str) -> Dict:
        """JSONファイル読み込み（エラーハンドリング付き）"""
        file_path = self.data_path / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Loaded {filename}: {len(data)} items")
                return data
        except FileNotFoundError:
            raise ConfigurationError(f"Required data file not found: {filename}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {filename}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading {filename}: {e}")
    
    @log_exception()
    @log_performance(threshold_seconds=5.0)
    async def calculate_struct_code(self,
                                   birth_date: str,
                                   birth_location: str,
                                   answers: List[AnswerData]) -> DiagnosisResponse:
        """
        STRUCT CODE診断の実行（リファクタリング版）
        """
        # 入力検証
        self._validate_input(birth_date, birth_location, answers)
        
        # 診断開始ログ
        log_diagnosis_start(birth_date, birth_location, len(answers))
        
        try:
            # 1. 出生時間推定（占星術ロジック逆算）
            birth_hour = self._estimate_birth_time(answers, birth_date, birth_location)
            hour = int(birth_hour)
            minute = int((birth_hour - hour) * 60)
            logger.debug(f"Estimated birth time: {hour:02d}:{minute:02d}")
            
            # 2. 占星術計算
            astro_data = self._calculate_astrology(birth_date, birth_location, birth_hour)
            
            # 3. 先天的素質（占星術100%）
            innate_axes = self._calculate_axes(astro_data, answers)
            logger.debug(f"Innate axes (astrology): {innate_axes}")
            
            # 4. 後天的状態（設問回答100%）
            acquired_axes = self._calculate_current_state(answers)
            logger.debug(f"Acquired axes (questionnaire): {acquired_axes}")

            # 5. 動的タイプ分類（v4.0）- 成長ベクトルとトランジット影響を5軸に反映
            # 推定出生時刻を文字列形式に変換
            birth_time_str = f"{int(birth_hour):02d}:{int((birth_hour % 1) * 60):02d}"
            dynamic_result = self._perform_dynamic_classification(
                birth_date=birth_date,
                birth_time=birth_time_str,
                birth_location=birth_location,
                questionnaire_axes=acquired_axes
            )

            # 5.5. 最終5軸の計算
            # 動的分類が成功した場合: current_axes（占星術70% + 設問30% + 時期的変調）を使用
            # 失敗した場合: 従来計算（innate × 0.7 + acquired × 0.3）にフォールバック
            if dynamic_result and 'current_axes' in dynamic_result:
                final_axes = dynamic_result['current_axes']
                logger.debug(f"Final axes (dynamic v2.1: chart 70% + quest 30% + time modulation): {final_axes}")
                logger.info(f"Dynamic classification applied: natal={dynamic_result['natal_type']}, "
                          f"current={dynamic_result['current_type']}, "
                          f"transition={dynamic_result['transition_state']}, "
                          f"life_phase={dynamic_result.get('life_phase', 'unknown')}")
            else:
                # フォールバック: 従来計算（動的分類が利用不可の場合）
                # 動的分類では: chart 70% + questionnaire 30% + time modulation
                # フォールバックでは成長・トランジット情報がないため:
                # innate（占星術）70% + acquired（設問）30%
                # 注: 動的分類と同じ重み付けだが、時期的変調は適用されない
                INNATE_WEIGHT = 0.7
                ACQUIRED_WEIGHT = 0.3
                final_axes = {}
                for axis_name in innate_axes.keys():
                    innate_val = innate_axes[axis_name]
                    acquired_val = acquired_axes.get(axis_name, 0.5)
                    final_axes[axis_name] = innate_val * INNATE_WEIGHT + acquired_val * ACQUIRED_WEIGHT
                logger.debug(f"Final axes (fallback: innate 0.7 + acquired 0.3): {final_axes}")
                logger.warning("Dynamic classification unavailable, using fallback calculation (growth/transit not applied)")

            # 6. 成長分析（先天と後天の差分）
            growth_differential = self._calculate_growth_differential(innate_axes, acquired_axes)
            logger.debug(f"Growth differential: {growth_differential}")

            # 7. 成長レポート生成（平易な表現）
            growth_report = self._generate_growth_report(growth_differential)
            logger.debug(f"Growth report generated")

            # 8. バイアス補正適用
            corrected_axes = self._apply_bias_correction(final_axes, astro_data)
            logger.debug(f"Bias corrected axes: {corrected_axes}")

            # 9. タイプ決定（従来ロジック維持）
            struct_type, confidence = self._determine_struct_type(corrected_axes, astro_data)

            # 10. ドリフト検出
            drift_info = self._detect_drift_patterns(struct_type, corrected_axes)
            logger.debug(f"Drift analysis: {drift_info}")

            # 11. 未来予測
            future_potential = self._predict_future_potential(struct_type, corrected_axes, astro_data, drift_info)
            logger.debug(f"Future prediction: {future_potential}")

            # 12. STRUCT CODE生成
            unique_code = self._generate_struct_code(corrected_axes, astro_data, struct_type, birth_date, birth_location)

            # 13. レスポンス構築（E-Plan: 成長レポート追加 + 動的分類結果）
            response = self._build_response(
                struct_type, unique_code, confidence, corrected_axes, astro_data,
                drift_info, future_potential, growth_differential,
                innate_axes, acquired_axes, growth_report,
                dynamic_classification=dynamic_result
            )

            # 診断完了ログ
            log_diagnosis_complete(unique_code, struct_type, confidence)

            return response
            
        except Exception as e:
            logger.error(f"Error in calculate_struct_code: {e}")
            raise
    
    def _validate_input(self, birth_date: str, birth_location: str, answers: List[AnswerData]) -> None:
        """入力データの検証"""
        # 生年月日検証
        try:
            datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError:
            raise DataValidationError(f"Invalid birth_date format: {birth_date}", "birth_date", birth_date)
        
        # 出生地検証
        if not birth_location or len(birth_location.strip()) == 0:
            raise DataValidationError("Birth location cannot be empty", "birth_location", birth_location)
        
        # 回答数検証（25問）
        if len(answers) != 25:
            raise DataValidationError(f"Expected 25 answers, got {len(answers)}", "answers", len(answers))
        
        # 回答内容検証
        for i, answer in enumerate(answers):
            if answer.choice not in CHOICE_VALUES:
                raise DataValidationError(
                    f"Invalid choice '{answer.choice}' in question {i+1}",
                    "choice",
                    answer.choice
                )
    
    def _estimate_birth_time(self, answers: List[AnswerData], birth_date: str, birth_location: str) -> float:
        """設問回答から出生時間を精密に推定（占星術ロジック逆算版）

        STRUCT CODEの核心アルゴリズム v3:
        1. 設問回答から「現在の5軸パターン」を抽出
        2. 各時間帯（0:00〜23:59）での占星術的5軸影響を計算
        3. 回答パターンと最も整合性の高い時間を推定出生時間とする

        理論的背景:
        - 設問回答は「先天的素質 + 後天的経験」の結果を反映
        - 占星術計算は「先天的素質」を出力
        - 両者の整合性が高い時間 = その人の出生時間である可能性が高い

        Returns:
            float: 推定出生時間（0.0〜24.0、例: 14.5 = 14:30）
        """
        import math

        # Step 1: 設問回答から5軸パターンを抽出
        questionnaire_axes = self._extract_axes_from_answers(answers)

        # Step 2: 各時間での占星術的5軸影響を計算し、最適時間を探索
        best_score = -1.0
        best_time = 12.0

        # 10分刻みで粗探索（144ポイント）
        for hour in range(24):
            for minute in range(0, 60, 10):
                test_time = hour + minute / 60.0
                score = self._evaluate_time_consistency(
                    test_time, birth_date, birth_location, questionnaire_axes
                )
                if score > best_score:
                    best_score = score
                    best_time = test_time

        # 最適時間の前後30分を1分刻みで精密探索
        refined_best_time = best_time
        refined_best_score = best_score

        start_time = max(0.0, best_time - 0.5)
        end_time = min(24.0, best_time + 0.5)

        test_time = start_time
        while test_time <= end_time:
            score = self._evaluate_time_consistency(
                test_time, birth_date, birth_location, questionnaire_axes
            )
            if score > refined_best_score:
                refined_best_score = score
                refined_best_time = test_time
            test_time += 1/60  # 1分刻み

        return refined_best_time

    def _extract_axes_from_answers(self, answers: List[AnswerData]) -> Dict[str, float]:
        """設問回答から5軸パターンを抽出"""
        axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
        axes = {}

        for axis_name in axis_names:
            value = self._calculate_axis_questionnaire_influence(axis_name, answers)
            axes[axis_name] = value

        return axes

    def _evaluate_time_consistency(self, test_time: float, birth_date: str, 
                                   birth_location: str, questionnaire_axes: Dict[str, float]) -> float:
        """指定時間での占星術的5軸と設問回答5軸の整合性を評価

        Returns:
            整合性スコア（0.0〜1.0、高いほど整合性が高い）
        """
        import math

        try:
            # その時間での占星術データを計算
            astro_data = self._calculate_astrology(birth_date, birth_location, test_time)

            # 占星術的5軸影響を計算
            astro_axes = {}
            for axis_name in ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']:
                astro_axes[axis_name] = self._calculate_axis_astro_influence(axis_name, astro_data)

            # 整合性スコアを計算
            # 方針: 設問回答が示す軸の「相対的な高低」と、占星術が示す軸の「相対的な高低」が一致するか

            # 各軸の相対順位を取得
            q_sorted = sorted(questionnaire_axes.items(), key=lambda x: x[1], reverse=True)
            a_sorted = sorted(astro_axes.items(), key=lambda x: x[1], reverse=True)

            q_ranks = {axis: rank + 1 for rank, (axis, _) in enumerate(q_sorted)}
            a_ranks = {axis: rank + 1 for rank, (axis, _) in enumerate(a_sorted)}

            # 順位の一致度を計算（スピアマン順位相関に類似）
            rank_diff_sum = 0
            for axis in q_ranks:
                diff = abs(q_ranks[axis] - a_ranks[axis])
                rank_diff_sum += diff ** 2

            # 最大差分は (5-1)^2 * 5 = 80
            max_diff = 80
            rank_score = 1.0 - (rank_diff_sum / max_diff)

            # 値の方向性一致度も考慮
            # 設問で高い軸が占星術でも高い傾向にあるか
            direction_score = 0.0
            for axis in questionnaire_axes:
                q_val = questionnaire_axes[axis]
                a_val = astro_axes[axis]
                # 両方とも0.5より高い、または両方とも0.5より低い場合に加点
                if (q_val > 0.5 and a_val > 0.5) or (q_val < 0.5 and a_val < 0.5):
                    direction_score += 0.2
                elif abs(q_val - 0.5) < 0.1 or abs(a_val - 0.5) < 0.1:
                    # 中間値の場合は軽く加点
                    direction_score += 0.1

            # 総合スコア
            total_score = rank_score * 0.6 + direction_score * 0.4

            return max(0.0, min(1.0, total_score))

        except Exception as e:
            # エラー時は低スコア
            return 0.0

    def _get_time_characteristics(self, minute: int) -> list:
        """時間帯を5軸特性ベクトルに変換

        占星術的な時間帯の特性をモデル化:
        - 起動軸: 朝6時にピーク（積極的始動の時間帯）
        - 判断軸: 午前10時にピーク（論理的思考の時間帯）
        - 選択軸: 正午にピーク（価値判断の時間帯）
        - 共鳴軸: 午後4時にピーク（社会的交流の時間帯）
        - 自覚軸: 深夜3時にピーク（深い内省の時間帯）

        Args:
            minute: 0〜1439（0:00〜23:59）

        Returns:
            5次元ベクトル [起動, 判断, 選択, 共鳴, 自覚]
        """
        import math

        # 時間を0〜2πに正規化（0時=0, 24時=2π）
        t = (minute / 1440) * 2 * math.pi

        # 各軸の位相オフセット（ピーク時間を設定）
        # 位相 = -2π * (ピーク時間/24)
        phase_activation = -2 * math.pi * (6 / 24)   # 起動軸: 6時ピーク
        phase_judgment = -2 * math.pi * (10 / 24)    # 判断軸: 10時ピーク
        phase_choice = -2 * math.pi * (12 / 24)      # 選択軸: 12時ピーク
        phase_resonance = -2 * math.pi * (16 / 24)   # 共鳴軸: 16時ピーク
        phase_awareness = -2 * math.pi * (3 / 24)    # 自覚軸: 3時ピーク

        # 正弦波でモデル化（振幅0.4、中心0.5 → 範囲0.1〜0.9）
        activation = 0.5 + 0.4 * math.sin(t + phase_activation)
        judgment = 0.5 + 0.4 * math.sin(t + phase_judgment)
        choice = 0.5 + 0.4 * math.sin(t + phase_choice)
        resonance = 0.5 + 0.4 * math.sin(t + phase_resonance)
        awareness = 0.5 + 0.4 * math.sin(t + phase_awareness)

        return [activation, judgment, choice, resonance, awareness]

    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """2つのベクトル間のコサイン類似度を計算

        Args:
            vec1, vec2: 5次元ベクトル

        Returns:
            類似度（-1.0〜1.0、1.0が最も類似）
        """
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
    
    @log_exception()
    def _calculate_astrology(self, birth_date: str, birth_location: str, birth_hour: float) -> Dict:
        """占星術計算（エラーハンドリング強化版）
        
        Args:
            birth_date: 生年月日 (YYYY-MM-DD形式)
            birth_location: 出生地
            birth_hour: 出生時間 (float, 例: 14.5 = 14:30)
        """
        try:
            # 日時設定（floatから時間と分を抽出）
            dt = datetime.strptime(birth_date, "%Y-%m-%d")
            hour = int(birth_hour)
            minute = int((birth_hour - hour) * 60)
            birth_dt = dt.replace(hour=hour, minute=minute, second=0)
            
            # 座標取得
            lat, lon = get_city_coordinates(birth_location)
            logger.debug(f"Using coordinates: {lat}, {lon} for {birth_location}")
            
            # 天体位置計算
            t = self.ts.utc(birth_dt.year, birth_dt.month, birth_dt.day,
                           birth_dt.hour, birth_dt.minute)
            
            earth = self.eph['earth']
            observer = earth + Topos(latitude_degrees=lat, longitude_degrees=lon)
            
            # 天体リスト
            planet_bodies = {
                'sun': self.eph['sun'],
                'moon': self.eph['moon'],
                'mercury': self.eph['mercury barycenter'],
                'venus': self.eph['venus barycenter'],
                'mars': self.eph['mars barycenter'],
                'jupiter': self.eph['jupiter barycenter'],
                'saturn': self.eph['saturn barycenter'],
                'uranus': self.eph['uranus barycenter'],
                'neptune': self.eph['neptune barycenter'],
                'pluto': self.eph['pluto barycenter']
            }
            
            # 正しいアセンダント計算
            asc_degree = self._calculate_ascendant_proper(t, lat, lon)
            logger.debug(f"Calculated ascendant: {asc_degree:.1f} degrees")

            positions = {}
            for name, body in planet_bodies.items():
                try:
                    if name == 'sun':
                        astrometric = earth.at(t).observe(body)
                    else:
                        astrometric = observer.at(t).observe(body)

                    ecliptic_latlon = astrometric.frame_latlon(ecliptic_frame)
                    lon_deg = ecliptic_latlon[1].degrees

                    positions[name] = {
                        'degree': lon_deg,
                        'sign': self._get_zodiac_sign(lon_deg),
                        'element': self._get_sign_element(lon_deg),
                        'house': self._calculate_house(lon_deg, asc_degree)
                    }
                    
                except Exception as e:
                    raise AstrologicalCalculationError(
                        f"Error calculating position for {name}: {e}",
                        planet=name,
                        context={'birth_date': birth_date, 'birth_hour': birth_hour}
                    )
            
            # アスペクト計算
            aspects = self._calculate_aspects(positions)

            return {
                'positions': positions,
                'aspects': aspects,
                'birth_hour': birth_hour,
                'birth_date': birth_date,  # 精密計算用に追加
                'birth_location': birth_location,  # 精密計算用に追加
                'location': {'lat': lat, 'lon': lon},
                'ascendant': asc_degree
            }
            
        except Exception as e:
            if isinstance(e, AstrologicalCalculationError):
                raise
            raise AstrologicalCalculationError(f"General astrology calculation error: {e}")
    
    def _calculate_axes(self, astro_data: Dict, answers: List[AnswerData]) -> Dict[str, float]:
        """5軸の値を計算（精密版: dynamic_type_classifierの計算を使用）

        STRUCT CODE 精密版:
        - 出生時間推定で設問回答を使用（現在→過去の逆算）
        - 最終5軸は精密な占星術計算（Essential/Accidental Dignity等）
        - 設問回答の二重計上を避ける

        精密計算では以下を考慮:
        - Essential Dignity (Domicile, Exaltation, Triplicity, Terms, Face)
        - Accidental Dignity (ハウス、アングル、燃焼、速度)
        - Mutual Reception, Fixed Stars, Antiscia
        - Node, Chiron, Part of Fortune, Moon Phase
        """
        # 精密計算が利用可能な場合
        if self._dynamic_classifier and self._astro_engine:
            try:
                # astro_dataから生年月日・場所・時間を復元
                birth_date = astro_data.get('birth_date')
                birth_location = astro_data.get('birth_location', 'tokyo')
                birth_hour = astro_data.get('birth_hour', 12.0)

                # 時間文字列に変換
                hour = int(birth_hour)
                minute = int((birth_hour - hour) * 60)
                birth_time_str = f"{hour:02d}:{minute:02d}"

                # Chartオブジェクトを生成
                natal_chart = self._astro_engine.calculate_natal_chart(
                    birth_date, birth_time_str, birth_location
                )

                # 精密な軸計算を実行
                axes = self._dynamic_classifier._calculate_axes_from_chart(natal_chart)

                logger.debug(f"Precise axes calculation used (v3.0): {axes}")
                return axes

            except Exception as e:
                logger.warning(f"Precise calculation failed, falling back to simple: {e}")

        # フォールバック: 従来のシンプル計算
        axes = {}
        for axis_name, definition in self.axis_definitions.items():
            astro_value = self._calculate_axis_astro_influence(axis_name, astro_data)
            axes[axis_name] = max(0.0, min(1.0, astro_value))

        logger.debug(f"Simple axes calculation used (fallback): {axes}")
        return axes
    
    def _calculate_current_state(self, answers: List[AnswerData]) -> Dict[str, float]:
        """設問回答から「現在の状態」を計算
        
        先天的素質（占星術5軸）との差分を見ることで、
        後天的な経験・環境による変化を可視化できる。
        """
        current = {}
        
        for axis_name in self.axis_definitions.keys():
            quest_value = self._calculate_axis_questionnaire_influence(axis_name, answers)
            current[axis_name] = max(0.0, min(1.0, quest_value))
        
        return current
    
    def _calculate_growth_differential(self, innate_axes: Dict[str, float], 
                                        current_state: Dict[str, float]) -> Dict[str, Dict]:
        """先天（占星術）と現在（設問）の差分を計算
        
        Returns:
            各軸の差分情報:
            - differential: 現在 - 先天（正=成長、負=抑制）
            - direction: 'growth'（成長）, 'suppression'（抑制）, 'stable'（安定）
            - magnitude: 変化の大きさ（0.0〜1.0）
        """
        differential = {}
        
        for axis_name in innate_axes.keys():
            innate = innate_axes[axis_name]
            current = current_state.get(axis_name, 0.5)
            
            diff = current - innate
            magnitude = abs(diff)
            
            if diff > 0.1:
                direction = 'growth'
            elif diff < -0.1:
                direction = 'suppression'
            else:
                direction = 'stable'
            
            differential[axis_name] = {
                'innate': innate,
                'current': current,
                'differential': diff,
                'direction': direction,
                'magnitude': magnitude
            }
        
        return differential
    
    def _generate_growth_report(self, growth_differential: Dict[str, Dict]) -> Dict[str, Any]:
        """成長レポートを生成（平易な表現で）

        軸という専門用語を使わず、ユーザーに分かりやすい表現で
        先天的素質と後天的発達の差分を説明する
        """
        axis_friendly_names = {
            '起動軸': '行動力',
            '判断軸': '考え方',
            '選択軸': '価値観',
            '共鳴軸': '人との繋がり',
            '自覚軸': '自己理解'
        }

        direction_messages = {
            'growth': {
                '起動軸': 'あなたは生まれ持った資質よりも、より積極的に行動できるようになっています。経験を通じて「まずやってみる」力が育っています。',
                '判断軸': 'あなたは生まれ持った傾向より、より論理的・計画的に物事を考えられるようになっています。分析力が磨かれてきました。',
                '選択軸': 'あなたは生まれ持った感性に加えて、より理想を追求する姿勢が強くなっています。美意識や価値基準が洗練されてきました。',
                '共鳴軸': 'あなたは生まれ持った以上に、人との繋がりを大切にできるようになっています。共感力や協調性が育っています。',
                '自覚軸': 'あなたは生まれ持った以上に、自分自身を深く理解できるようになっています。内省力が高まってきました。'
            },
            'suppression': {
                '起動軸': '環境や経験から、慎重に行動するようになっているかもしれません。本来の行動力を発揮できる機会を増やすと良いでしょう。',
                '判断軸': '直感や感覚を重視するようになっているかもしれません。それも大切ですが、時には分析的な視点も活用してみてください。',
                '選択軸': '現実的・実用的な判断を優先するようになっているかもしれません。時には理想を追う余裕も持ってみてください。',
                '共鳴軸': '自立を重視し、独自の道を歩むようになっているかもしれません。信頼できる人との繋がりも大切にしてみてください。',
                '自覚軸': '外の世界への関心が強くなっているかもしれません。時には立ち止まって自分と向き合う時間も大切です。'
            },
            'stable': {
                '起動軸': '行動力について、生まれ持った資質をそのまま活かせています。自然体でいられる強みです。',
                '判断軸': '考え方のスタイルが、生まれ持った傾向と調和しています。無理なく判断できる強みです。',
                '選択軸': '価値観が生まれ持った感性と一致しています。自分らしい選択ができている証拠です。',
                '共鳴軸': '人との関わり方が、本来の傾向と調和しています。自然な人間関係を築けています。',
                '自覚軸': '自己理解の深さが、生まれ持った傾向と一致しています。等身大の自分でいられています。'
            }
        }

        report = {'summary': '', 'details': [], 'recommendations': []}
        growth_count = suppression_count = stable_count = 0

        for axis_name, diff_info in growth_differential.items():
            direction = diff_info['direction']
            friendly_name = axis_friendly_names.get(axis_name, axis_name)

            if direction == 'growth':
                growth_count += 1
            elif direction == 'suppression':
                suppression_count += 1
            else:
                stable_count += 1

            detail = {
                'aspect': friendly_name,
                'direction': direction,
                'message': direction_messages[direction].get(axis_name, ''),
                'innate_level': 'H' if diff_info['innate'] >= 0.6 else ('L' if diff_info['innate'] < 0.4 else 'M'),
                'current_level': 'H' if diff_info['current'] >= 0.6 else ('L' if diff_info['current'] < 0.4 else 'M')
            }
            report['details'].append(detail)

        if growth_count > suppression_count:
            report['summary'] = '全体的に、あなたは生まれ持った資質をさらに伸ばす方向で成長しています。経験を通じて多くの能力が開花しています。'
        elif suppression_count > growth_count:
            report['summary'] = '環境への適応の中で、一部の資質を抑えている傾向があります。本来の強みを意識的に発揮する機会を増やすと良いでしょう。'
        else:
            report['summary'] = 'あなたは生まれ持った資質と現在の状態がバランスよく調和しています。自分らしさを保ちながら生きています。'

        if suppression_count > 0:
            report['recommendations'].append('抑制されている傾向のある領域について、意識的にチャレンジする機会を作ってみてください。')
        if growth_count > 0:
            report['recommendations'].append('成長している領域は、あなたの努力の成果です。さらに伸ばしていく価値があります。')
        if stable_count == 5:
            report['recommendations'].append('すべての領域で本来の自分と調和しています。この状態を維持しながら、新しい挑戦も楽しんでください。')

        return report

    def _calculate_axis_astro_influence(self, axis_name: str, astro_data: Dict) -> float:
        """軸への占星術的影響を計算

        係数設定:
        - ベース値: 0.5（中立）
        - 惑星影響係数: 0.15（正負両方向に影響）
        - ハウス増幅係数: 1.5（ハウスマッチ時）
        - エレメント修飾: 0.7-1.4（軸定義による）
        - アスペクト影響: ±0.06/0.04

        この設計により:
        - L(Low): 約13%、M(Medium): 約73%、H(High): 約14% の分布を実現
        - Mが多いのは「平均的な内面構造」を持つ人が多いことを反映
        """
        definition = self.axis_definitions[axis_name]
        value = 0.5  # ベース値（中立点）

        # 天体の影響（正負両方向）
        for planet in definition['planetary_rulers']:
            if planet in astro_data['positions']:
                pos = astro_data['positions'][planet]

                # 度数による影響（sin関数で-0.35〜+0.35の範囲）
                # これにより惑星位置によって軸値が上下する
                # 振幅を0.3→0.35に拡大し、H/Lがより明確に出やすくする
                planet_influence = 0.35 * math.sin(math.radians(pos['degree']))

                # 星座要素による修飾
                element = pos['element']
                element_modifier = definition['element_modifiers'].get(element, 1.0)
                planet_influence *= element_modifier

                # ハウスによる増幅（1.5倍）
                # 正しいハウス計算により、この影響が適切に反映される
                if pos['house'] in definition.get('houses', []):
                    planet_influence *= 1.5

                value += planet_influence * 0.15

        # アスペクトの影響（やや強化）
        for aspect in astro_data['aspects']:
            if any(p in definition['planetary_rulers'] for p in aspect['planets']):
                intensity = aspect.get('intensity', 1.0)
                if aspect['nature'] in ['harmony', 'flow']:
                    value += 0.06 * intensity
                elif aspect['nature'] in ['tension', 'polarity']:
                    value -= 0.04 * intensity

        return max(0.0, min(1.0, value))
    
    def _calculate_axis_questionnaire_influence(self, axis_name: str, answers: List[AnswerData]) -> float:
        """軸への設問影響を計算 - question_full_map.jsonのベクトルデータを使用

        各選択肢は5軸全てへの影響を持つベクトルとして定義されています。
        その軸に属する質問からの影響を主軸として、他の質問からの影響も副次的に考慮します。
        """
        # 軸インデックスマッピング: [起動軸, 判断軸, 選択軸, 共鳴軸, 自覚軸] = [0, 1, 2, 3, 4]
        axis_index = {
            '起動軸': 0,
            '判断軸': 1,
            '選択軸': 2,
            '共鳴軸': 3,
            '自覚軸': 4
        }

        idx = axis_index.get(axis_name)
        if idx is None:
            return 0.5

        primary_values = []   # その軸に属する質問からの影響（重み: 1.0）
        secondary_values = [] # 他の質問からの影響（重み: 0.3）

        for answer in answers:
            q_id = answer.question_id  # 例: "Q.01"
            if q_id in self.questions:
                question_data = self.questions[q_id]
                choice = answer.choice
                if choice in question_data.get('choices', {}):
                    vector = question_data['choices'][choice].get('vector', [0.5]*5)
                    if len(vector) > idx:
                        value = vector[idx]
                        # 質問の軸と一致する場合は主軸として、そうでなければ副次的に考慮
                        if question_data.get('axis') == axis_name:
                            primary_values.append(value)
                        else:
                            secondary_values.append(value)

        # 重み付き平均を計算
        total_weight = 0.0
        total_value = 0.0

        if primary_values:
            primary_weight = len(primary_values) * 1.0
            total_weight += primary_weight
            total_value += sum(primary_values)

        if secondary_values:
            # 副次影響を0.3→0.2に縮小し、主軸質問の弁別力を向上
            secondary_weight = len(secondary_values) * 0.2
            total_weight += secondary_weight
            total_value += sum(secondary_values) * 0.2

        return total_value / total_weight if total_weight > 0 else 0.5
    
    def _determine_struct_type(self, axes: Dict[str, float], astro_data: Dict) -> Tuple[str, float]:
        """STRUCT TYPEの決定（TOP3候補も計算）"""
        # 全タイプのスコアを計算
        type_scores = []
        for type_code, type_info in self.struct_types.items():
            score = self._calculate_type_compatibility(axes, type_info)
            type_scores.append({
                'type': type_code,
                'name': type_info['name'],
                'archetype': type_info.get('archetype', ''),
                'score': round(score, 4),
                'vector': type_info.get('vector', [])
            })

        # スコア降順でソート
        type_scores.sort(key=lambda x: x['score'], reverse=True)

        # スコアを0.0〜1.0の範囲にクランプ（100%を超えないようにする）
        for ts in type_scores:
            ts['score'] = round(min(1.0, max(0.0, ts['score'])), 4)

        # TOP3を保存（後で_build_responseで使用）
        self._last_type_candidates = type_scores[:3]

        best = type_scores[0]
        if best['score'] < config.type_confidence_threshold:
            logger.warning(f"Low type confidence: {best['score']:.3f} for {best['type']}")

        confidence = min(1.0, best['score'])
        return best['type'] or 'S0-MX', confidence

    def _calculate_type_compatibility(self, axes: Dict[str, float], type_info: Dict) -> float:
        """タイプとの適合度計算（v4.1: ガウス関数＋方向チェック）

        各タイプに定義された精密なベクトル値と直接比較し、
        ガウス関数による滑らかなスコアリングと、
        H/L軸の方向一致を厳密にチェックして精度向上。
        常に0〜1の範囲で出力。
        """
        import math

        axis_order = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
        axis_order_sig = ['起動', '判断', '選択', '共鳴', '自覚']

        # ユーザーの5軸値
        user_vector = [axes.get(axis, 0.5) for axis in axis_order]

        # タイプの理想ベクトル（精密な数値）
        type_vector = type_info.get('vector', [0.5, 0.5, 0.5, 0.5, 0.5])
        type_sig = type_info.get('axis_signature', {})

        total_score = 0.0
        total_weight = 0.0

        # ガウス関数のパラメータ（σ=0.25で距離に応じた滑らかな減衰）
        sigma = 0.25

        for i, (axis_short, user_val, type_val) in enumerate(zip(axis_order_sig, user_vector, type_vector)):
            level = type_sig.get(axis_short, 'M')

            # 軸の重要度（H軸をより重視、M軸の影響を軽減）
            weight = {'H': 0.30, 'L': 0.22, 'M': 0.08}[level]

            # ガウス関数によるスコアリング（距離に応じて滑らかに減衰）
            distance = abs(user_val - type_val)
            axis_score = math.exp(-(distance ** 2) / (2 * sigma ** 2))

            # H/L軸での方向チェック（ペナルティ方式）
            if level == 'H':
                # H軸タイプなのにユーザーがL寄り（0.45未満）ならペナルティ
                if user_val < 0.45:
                    axis_score *= 0.6  # 40%ペナルティ
                # H軸タイプでユーザーもH寄り（0.55以上）ならボーナス
                elif user_val >= 0.55:
                    axis_score = min(1.0, axis_score * 1.1)  # 10%ボーナス
            elif level == 'L':
                # L軸タイプなのにユーザーがH寄り（0.55超）ならペナルティ
                if user_val > 0.55:
                    axis_score *= 0.6  # 40%ペナルティ
                # L軸タイプでユーザーもL寄り（0.45以下）ならボーナス
                elif user_val <= 0.45:
                    axis_score = min(1.0, axis_score * 1.1)  # 10%ボーナス

            total_score += axis_score * weight
            total_weight += weight

        # 正規化して0〜1に収める
        return total_score / total_weight if total_weight > 0 else 0.5

    def _perform_dynamic_classification(
        self,
        birth_date: str,
        birth_time: Optional[str],
        birth_location: str,
        questionnaire_axes: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        """動的タイプ分類を実行（v4.0）

        占星術的な時間軸（ネイタル→トランジット過程→現在トランジット）を
        考慮した動的なタイプ分類を行う。

        Args:
            birth_date: 生年月日 (YYYY-MM-DD)
            birth_time: 出生時刻 (HH:MM) - オプション
            birth_location: 出生地
            questionnaire_axes: 設問回答から算出した5軸

        Returns:
            動的分類結果の辞書、または分類器が利用不可の場合はNone
        """
        if self._dynamic_classifier is None:
            return None

        try:
            result = self._dynamic_classifier.classify(
                birth_date=birth_date,
                birth_time=birth_time,
                birth_place=birth_location,
                questionnaire_axes=questionnaire_axes
            )

            # 結果を辞書形式に変換
            return {
                'natal_type': result.natal_type,
                'current_type': result.current_type,
                'confidence': result.confidence,
                'transition_state': result.transition_state.value,
                'transition_path': result.transition_path,
                'potential_next_types': result.potential_next_types,
                'natal_axes': result.natal_axes,
                'current_axes': result.current_axes,
                'growth_axes': result.growth_axes,
                'transit_axes': result.transit_axes,
                'life_phase': result.growth_vector.current_phase,
                'maturity_level': result.growth_vector.maturity_level,
                'interpretation': result.interpretation,
                'life_cycle_events_count': len(result.life_cycle_events),
                'current_transits_count': len(result.current_transits),
            }

        except Exception as e:
            logger.warning(f"Dynamic classification failed, falling back to static: {e}")
            return None

    def _generate_struct_code(self, axes: Dict, astro_data: Dict, struct_type: str,
                             birth_date: str, birth_location: str) -> str:
        """本来のSTRUCT CODE形式で生成"""
        # 5軸の値を0-999の範囲にスケーリング
        axis_values = []
        for axis_name in ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']:
            value = round(axes[axis_name] * 999)
            axis_values.append(f"{value:03d}")
        
        # STRUCT CODE: TYPE + 5軸数値
        axis_string = "-".join(axis_values)
        return f"{struct_type} {axis_string}"
    
    def _build_response(self, struct_type: str, unique_code: str, confidence: float,
                       axes: Dict[str, float], astro_data: Dict,
                       drift_info: Dict[str, Any] = None, future_potential: Dict[str, Any] = None,
                       growth_differential: Dict[str, Dict] = None,
                       innate_axes: Dict[str, float] = None, acquired_axes: Dict[str, float] = None,
                       growth_report: Dict[str, Any] = None,
                       dynamic_classification: Dict[str, Any] = None) -> DiagnosisResponse:
        """レスポンス構築

        D案対応: growth_differentialに先天（占星術）と現在（設問）の差分を含む
        v4.0対応: dynamic_classificationに動的タイプ分類結果を含む
        """
        type_info = self.struct_types[struct_type]
        
        # vectorsデータをnumpy型から変換
        # TOP3タイプ候補を取得
        type_candidates = getattr(self, '_last_type_candidates', [])

        vectors_data = {
            'axes': axes,  # E-Plan: 最終5軸（先天0.7 + 後天0.3）
            'innate_axes': innate_axes if innate_axes is not None else axes,  # 先天的素質（占星術100%）
            'acquired_axes': acquired_axes if acquired_axes is not None else {},  # 後天的状態（設問回答100%）
            'final_vector': list(axes.values()),
            'type_candidates': type_candidates,  # TOP3タイプ候補（AIプロンプト用）
            'planetary_positions': {k: v['degree'] for k, v in astro_data['positions'].items()},
            'house_positions': {k: v['house'] for k, v in astro_data['positions'].items()},
            'ascendant': astro_data.get('ascendant', 0),
            'aspects': astro_data['aspects'],
            'drift_analysis': drift_info or {},
            'future_prediction': future_potential or {},
            'growth_differential': growth_differential or {},  # 先天と現在の差分
            'growth_report': growth_report or {},  # E-Plan: 平易な成長レポート
            'advanced_weights': self.field_weights,
            # v4.0: 動的タイプ分類結果
            'dynamic_classification': dynamic_classification or {}
        }
        
        # 基本的なレスポンス構築
        return DiagnosisResponse(
            struct_type=struct_type,
            struct_code=unique_code,
            similarity_score=confidence,
            symbolic_time=self._get_symbolic_time(astro_data),
            symbolic_meaning=type_info['mission'],
            type_detail=self._create_type_detail(struct_type, type_info, axes),
            top_candidates=self._get_axis_insights(axes),
            vectors=self._clean_numpy_types(vectors_data),
            interpretation_prompt=self._generate_interpretation_prompt(unique_code, type_info, axes)
        )
    
    # === ヘルパーメソッド ===
    
    def _clean_numpy_types(self, obj):
        """numpy型をPythonネイティブ型に再帰的に変換"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, np.bool)):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, dict):
            return {key: self._clean_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_numpy_types(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._clean_numpy_types(item) for item in obj)
        else:
            return obj
    
    def _get_zodiac_sign(self, degree: float) -> str:
        """度数から星座を取得"""
        index = int(degree / 30) % 12
        return ZODIAC_SIGNS[index]
    
    def _get_sign_element(self, degree: float) -> str:
        """度数から星座の要素を取得"""
        sign = self._get_zodiac_sign(degree)
        return ZODIAC_ELEMENTS.get(sign, 'unknown')
    
    def _calculate_house(self, degree: float, asc_degree: float) -> int:
        """ハウス計算（Equal House System）

        Args:
            degree: 天体の黄経度数
            asc_degree: アセンダントの黄経度数

        Returns:
            ハウス番号（1-12）
        """
        house_degree = (degree - asc_degree + 360) % 360
        return int(house_degree / 30) + 1

    def _calculate_ascendant_proper(self, t, lat: float, lon: float) -> float:
        """正しいアセンダント計算（地方恒星時から算出）

        Args:
            t: Skyfield timeオブジェクト
            lat: 緯度
            lon: 経度

        Returns:
            アセンダントの黄経度数
        """
        # 地方恒星時（LST）を計算
        # Skyfieldのgmst()はグリニッジ平均恒星時を返す
        gmst = t.gmst  # グリニッジ平均恒星時（時間単位）
        lst = (gmst + lon / 15) % 24  # 地方恒星時（時間単位）
        lst_deg = lst * 15  # 度数に変換

        # 黄道傾斜角（現代の値）
        obliquity = 23.44
        obliquity_rad = math.radians(obliquity)
        lat_rad = math.radians(lat)
        lst_rad = math.radians(lst_deg)

        # アセンダント計算式
        # ASC = atan2(cos(LST), -sin(LST)*cos(ε) - tan(φ)*sin(ε))
        y = math.cos(lst_rad)
        x = -math.sin(lst_rad) * math.cos(obliquity_rad) - math.tan(lat_rad) * math.sin(obliquity_rad)

        asc_rad = math.atan2(y, x)
        asc_deg = math.degrees(asc_rad)

        # 0-360度に正規化
        asc_deg = (asc_deg + 360) % 360

        return asc_deg

    def _calculate_ascendant(self, birth_hour: int, lat: float) -> int:
        """アセンダント計算（後方互換性用のラッパー）"""
        # 注意: この関数は後方互換性のために残しているが、
        # 正しい計算には_calculate_ascendant_properを使用すべき
        return int((birth_hour * 15 + lat / 2) % 360)
    
    def _calculate_aspects(self, positions: Dict) -> List[Dict]:
        """アスペクト計算"""
        aspects = []
        planets = list(positions.keys())
        
        for i, planet1 in enumerate(planets):
            for planet2 in planets[i+1:]:
                deg1 = positions[planet1]['degree']
                deg2 = positions[planet2]['degree']
                diff = abs(deg1 - deg2)
                if diff > 180:
                    diff = 360 - diff
                
                for aspect_name, aspect_data in ASPECT_DEFINITIONS.items():
                    if abs(diff - aspect_data['angle']) <= aspect_data['orb']:
                        aspects.append({
                            'planets': [planet1, planet2],
                            'type': aspect_name,
                            'angle': diff,
                            'nature': aspect_data['nature'],
                            'intensity': aspect_data['intensity']
                        })
                        break
        
        return aspects
    
    def _get_symbolic_time(self, astro_data: Dict) -> str:
        """推定出生時間を返す（回答から推定した時間、分単位）
        
        birth_hourはfloat値（例: 14.5 = 14:30）で格納されている
        """
        birth_hour_float = astro_data.get('birth_hour', 12.0)
        
        # floatから時間と分を抽出
        hour = int(birth_hour_float)
        minute = int((birth_hour_float - hour) * 60)
        
        # 24時間形式に正規化
        hour = hour % 24
        
        return f"{hour:02d}:{minute:02d}"
    
    def _describe_decision_style(self, axes: Dict[str, float]) -> str:
        """意思決定スタイルの記述"""
        judgment = axes['判断軸']
        if judgment > config.axis_high_threshold:
            return "論理的で構造的な意思決定を重視"
        else:
            return "直感的で感覚的な意思決定を重視"
    
    def _describe_choice_pattern(self, axes: Dict[str, float]) -> str:
        """選択パターンの記述"""
        choice = axes['選択軸']
        if choice > config.axis_high_threshold:
            return "価値と美を重視する選択パターン"
        else:
            return "実用性と効率を重視する選択パターン"
    
    def _get_growth_challenges(self, axes: Dict[str, float]) -> str:
        """成長課題の特定"""
        weakest_axis = min(axes.items(), key=lambda x: x[1])
        return f"{weakest_axis[0]}（{weakest_axis[1]:.2f}）の発達が成長の鍵"
    
    def _describe_relations(self, axes: Dict[str, float]) -> str:
        """関係性の記述"""
        resonance = axes['共鳴軸']
        if resonance > config.axis_high_threshold:
            return "深い共感と感情的な繋がりを求める傾向"
        else:
            return "独立性と個人の空間を大切にする傾向"
    
    def _get_growth_tips(self, axes: Dict[str, float], type_info: Dict) -> str:
        """成長のヒント"""
        return f"{type_info['mission']}を実現するために、バランスの取れた軸の発達を心がけましょう。"
    
    def _get_axis_insights(self, axes: Dict[str, float]) -> List[Dict]:
        """軸の洞察"""
        insights = []
        for axis_name, value in axes.items():
            level = "高" if value > config.axis_high_threshold else "中" if value > config.axis_medium_threshold else "低"
            insights.append({
                'axis': axis_name,
                'value': value,
                'level': level,
                'insight': self.axis_definitions[axis_name]['essence']
            })
        return insights
    
    # === 高度計算メソッド ===
    
    def _detect_drift_patterns(self, struct_type: str, current_axes: Dict[str, float]) -> Dict[str, Any]:
        """ドリフト検出・パターン分析

        新タイプ形式（ACCP、AWAB等）と軸値から、理想ベクトルとの乖離を検出
        """
        # 新タイプ形式の解析: ACCP, AWAB, JDPU等
        # 先頭2文字が主軸を示す: AC=起動軸, JD=判断軸, CH=選択軸, RS=共鳴軸, AW=自覚軸
        if len(struct_type) < 2:
            return {'drift_detected': False, 'drift_magnitude': 0.0, 'trend_direction': 'stable'}

        axis_prefix = struct_type[:2]  # AC, JD, CH, RS, AW

        # 軸プレフィックスから主軸を特定
        primary_axis_map = {
            'AC': '起動軸',
            'JD': '判断軸',
            'CH': '選択軸',
            'RS': '共鳴軸',
            'AW': '自覚軸'
        }

        primary_axis = primary_axis_map.get(axis_prefix)
        if not primary_axis:
            return {'drift_detected': False, 'drift_magnitude': 0.0, 'trend_direction': 'stable'}

        # タイプの理想軸シグネチャを取得
        if struct_type not in self.struct_types:
            return {'drift_detected': False, 'drift_magnitude': 0.0, 'trend_direction': 'stable'}

        type_info = self.struct_types[struct_type]
        ideal_signature = type_info['axis_signature']

        # 理想ベクトルを構築（H=0.8, M=0.5, L=0.2）
        signature_to_value = {'H': 0.8, 'M': 0.5, 'L': 0.2}
        reference_vector = []
        for axis in ['起動', '判断', '選択', '共鳴', '自覚']:
            expected = ideal_signature.get(axis, 'M')
            reference_vector.append(signature_to_value[expected])

        # 現在の軸値をベクトル化（軸順序を合わせる）
        current_vector = [
            current_axes.get('起動軸', 0.5),
            current_axes.get('判断軸', 0.5),
            current_axes.get('選択軸', 0.5),
            current_axes.get('共鳴軸', 0.5),
            current_axes.get('自覚軸', 0.5)
        ]

        # ドリフト量計算（ユークリッド距離）
        drift_magnitude = np.linalg.norm(np.array(current_vector) - np.array(reference_vector))

        # ドリフト方向分析
        drift_vector = np.array(current_vector) - np.array(reference_vector)

        # 最大変化軸の特定
        axis_names = ['起動軸', '判断軸', '選択軸', '共鳴軸', '自覚軸']
        max_drift_idx = int(np.argmax(np.abs(drift_vector)))
        max_drift_axis = axis_names[max_drift_idx]
        drift_direction = 'positive' if float(drift_vector[max_drift_idx]) > 0 else 'negative'

        # ドリフト検出閾値（0.3以上で有意なドリフトとみなす）
        drift_threshold = 0.3

        return {
            'drift_detected': bool(drift_magnitude > drift_threshold),
            'drift_magnitude': float(drift_magnitude),
            'trend_direction': drift_direction,
            'primary_drift_axis': max_drift_axis,
            'primary_axis': primary_axis,
            'drift_vector': drift_vector.tolist(),
            'reference_vector': reference_vector,
            'type_signature': ideal_signature
        }
    
    def _apply_bias_correction(self, axes: Dict[str, float], astro_data: Dict) -> Dict[str, float]:
        """バイアス補正の適用

        beta補正と季節補正を適用し、最終値を0.0〜1.0に正規化
        """
        corrected_axes = axes.copy()

        # 天体エネルギーに基づく補正
        weights = self.field_weights.get('beta', {})

        for axis_name, value in axes.items():
            corrected_value = value

            # ベータ補正の適用
            if axis_name in weights:
                beta_correction = weights[axis_name]
                corrected_value *= beta_correction

            # 天体位置による季節補正
            if 'positions' in astro_data:
                sun_sign = astro_data['positions']['sun']['sign']
                seasonal_correction = self._get_seasonal_correction(axis_name, sun_sign)
                corrected_value *= seasonal_correction

            # 正規化（0.0〜1.0の範囲に収める）
            corrected_axes[axis_name] = max(0.0, min(1.0, corrected_value))

        return corrected_axes
    
    def _get_seasonal_correction(self, axis_name: str, sun_sign: str) -> float:
        """季節補正係数の計算

        sun_signは日本語の星座名（牡羊座、牡牛座等）で渡される
        """
        seasonal_modifiers = {
            'spring_signs': ['牡羊座', '牡牛座', '双子座'],
            'summer_signs': ['蟹座', '獅子座', '乙女座'],
            'autumn_signs': ['天秤座', '蠍座', '射手座'],
            'winter_signs': ['山羊座', '水瓶座', '魚座']
        }

        axis_seasonal_effects = {
            '起動軸': {'spring': 1.05, 'summer': 1.03, 'autumn': 0.98, 'winter': 0.95},
            '判断軸': {'spring': 1.00, 'summer': 0.98, 'autumn': 1.05, 'winter': 1.03},
            '選択軸': {'spring': 1.03, 'summer': 1.05, 'autumn': 1.00, 'winter': 0.98},
            '共鳴軸': {'spring': 0.98, 'summer': 1.03, 'autumn': 1.00, 'winter': 1.05},
            '自覚軸': {'spring': 1.00, 'summer': 1.00, 'autumn': 1.03, 'winter': 1.03}
        }

        # 星座から季節を判定
        season = 'spring'
        for season_name, signs in seasonal_modifiers.items():
            if sun_sign in signs:
                season = season_name.split('_')[0]
                break

        return axis_seasonal_effects.get(axis_name, {}).get(season, 1.0)
    
    def _predict_future_potential(self, struct_type: str, axes: Dict[str, float], 
                                 astro_data: Dict, drift_info: Dict) -> Dict[str, Any]:
        """未来予測・成長可能性分析"""
        # 3ヶ月後の予測計算
        future_axes = axes.copy()
        
        # ドリフトトレンドの延長
        if drift_info['drift_detected']:
            drift_vector = np.array(drift_info['drift_vector'])
            future_projection = drift_vector * 0.3  # 3ヶ月分の予測
            
            axis_names = list(axes.keys())
            for i, axis_name in enumerate(axis_names):
                future_axes[axis_name] = float(max(0, min(1, axes[axis_name] + future_projection[i])))
        
        # 木星・土星サイクルによる成長予測
        jupiter_phase = self._get_jupiter_influence(astro_data['positions']['jupiter'])
        saturn_phase = self._get_saturn_influence(astro_data['positions']['saturn'])
        
        growth_multiplier = (jupiter_phase + saturn_phase) / 2
        
        # 成長可能性の最も高い軸を特定
        growth_potential = {}
        for axis_name, current_value in axes.items():
            potential_growth = (1.0 - current_value) * growth_multiplier
            growth_potential[axis_name] = float(potential_growth)
        
        # 最高成長軸の特定
        max_growth_axis = max(growth_potential.items(), key=lambda x: x[1])
        
        return {
            'timeline': '3months',
            'predicted_axes': future_axes,
            'growth_potential': growth_potential,
            'max_growth_axis': max_growth_axis[0],
            'max_growth_potential': float(max_growth_axis[1]),
            'jupiter_influence': float(jupiter_phase),
            'saturn_influence': float(saturn_phase),
            'overall_growth_forecast': float(growth_multiplier)
        }
    
    def _get_jupiter_influence(self, jupiter_pos: Dict) -> float:
        """木星の成長影響度計算"""
        # 木星の星座による成長エネルギー
        jupiter_growth_power = {
            'Aries': 0.9, 'Taurus': 0.7, 'Gemini': 0.8, 'Cancer': 0.8,
            'Leo': 0.9, 'Virgo': 0.6, 'Libra': 0.7, 'Scorpio': 0.8,
            'Sagittarius': 1.0, 'Capricorn': 0.8, 'Aquarius': 0.9, 'Pisces': 0.8
        }
        return jupiter_growth_power.get(jupiter_pos['sign'], 0.7)
    
    def _get_saturn_influence(self, saturn_pos: Dict) -> float:
        """土星の構造化影響度計算"""
        # 土星の星座による構造化エネルギー
        saturn_structure_power = {
            'Aries': 0.6, 'Taurus': 0.9, 'Gemini': 0.7, 'Cancer': 0.7,
            'Leo': 0.6, 'Virgo': 0.9, 'Libra': 0.8, 'Scorpio': 0.8,
            'Sagittarius': 0.7, 'Capricorn': 1.0, 'Aquarius': 0.8, 'Pisces': 0.6
        }
        return saturn_structure_power.get(saturn_pos['sign'], 0.7)
    
    def _create_type_detail(self, struct_type: str, type_info: Dict, axes: Dict[str, float]) -> TypeDetail:
        """TypeDetail作成（詳細ページと統一）"""
        detailed_chars = self._get_detailed_characteristics(struct_type)
        
        return TypeDetail(
            code=struct_type,
            label=type_info['name'],
            summary=detailed_chars['summary'],
            decision_style=detailed_chars['decision_style'],
            choice_pattern=detailed_chars['choice_pattern'],
            risk_note=detailed_chars['risk_note'],
            relation_hint=detailed_chars['relation_hint'],
            growth_tip=detailed_chars['growth_tip'],
            vector=list(axes.values()),  # 診断結果では実際の軸値を使用
            character_icon=None
        )
    
    def _get_detailed_characteristics(self, type_code: str) -> Dict[str, str]:
        """各タイプの詳細特性を取得"""
        characteristics = {
            # 活性化軸 (AC)
            'ACPU': {
                'summary': 'マーズは瞬間的な爆発的起動能力を持つ戦士タイプです。困難な状況に直面すると迷わず行動を起こし、新たな道を切り開く力を発揮します。エネルギッシュで勇敢、チャレンジ精神旺盛で、「今すぐやろう」が口癖のような行動派です。危機的状況でこそ真価を発揮し、他の人が躊躇する場面でも果敢に前進する勇気を持っています。自らの直感と本能を信じ、複雑な分析よりも即座の行動で結果を出すことを得意とします。独立心が強く、自分のペースとスタイルで物事を進めることを好み、他者に依存せず自力で道を切り開く強さがあります。実利的な思考で無駄を嫌い、最短距離で目標に到達することを追求する効率重視のアクションリーダーです。',
                'decision_style': '直感と本能に従った瞬発的な判断を得意とします。データ分析や長時間の検討よりも、「これだ！」と感じた瞬間の感覚を信じて即決断する傾向があります。緊急事態やプレッシャーがかかる状況ほど冷静かつ迅速に判断でき、迷いが生じた時は「とりあえずやってみる」精神で前に進みます。複雑な状況でも本質を見抜く直感力があり、決断後の軌道修正も素早く行えます。論理的な根拠よりも、体感と経験に基づく判断を重視し、「頭で考えるより体が動く」タイプの意思決定者です。他者の意見を参考にすることはあっても、最終的には自分自身の感覚と責任で決断を下し、その結果を潔く受け入れる覚悟を持っています。',
                'choice_pattern': 'リスクがあっても成長と学びにつながる挑戦的な選択肢を積極的に選びます。安全で予測可能な道よりも、未知の可能性を秘めた冒険的な選択を好み、失敗を恐れずに新しい領域に踏み込みます。選択する際は「面白そうか」「成長できそうか」「誰かのためになるか」を重視し、短期的な困難よりも長期的な可能性を見据えます。競争や挑戦の要素がある選択肢に特に魅力を感じ、他の人が諦めそうな困難な道でも果敢に選択します。実利的な観点から無駄を省き、最も効率的に目標達成できるルートを選ぶ傾向があり、形式や儀式よりも実質的な成果を重視します。美しさや理想よりも、実用性と効果を優先した選択を行います。',
                'risk_note': '衝動的になりすぎて事前の計画や準備を軽視し、後で困難に直面するリスクがあります。短期的な成果に集中するあまり長期的な戦略を見失いがちで、忍耐が必要な継続的作業を途中で放棄する傾向があります。また、自分の判断に自信を持ちすぎて他者の意見やアドバイスを聞かず、一人で突進して孤立することもあります。独立心が強すぎてチームプレーが苦手になったり、他者との協調よりも自分のやり方を優先して摩擦を生むことがあります。燃え尽き症候群にも注意が必要で、常に高いエネルギーを維持しようとして疲弊する場合があります。また、直感に頼りすぎて、論理的な分析が必要な場面で判断を誤るリスクもあります。',
                'relation_hint': '同じくエネルギッシュで行動力のある人との相性が抜群で、お互いを刺激し合いながら大きな目標に向かって突進できます。慎重で計画的な人とは最初は対立することもありますが、お互いの長所を認め合えれば非常にバランスの取れた強力なパートナーシップを築けます。リーダーシップを発揮する場面では、チームメンバーの多様性を活かし、自分にない視点を補完してもらうことが重要です。感情的なサポートを求める人に対しては、共感よりも具体的な行動での支援を得意とします。独立心が強いため、過度に依存的な関係よりも、お互いの自立を尊重し合える対等なパートナーシップを好みます。チームでは推進力と決断力で全体を牽引し、停滞を打破する起爆剤として機能します。',
                'growth_tip': '自然な行動力と決断力を活かしながら、計画性と持続力を段階的に身につけることで、より大きな成果を継続的に上げられるようになります。短期的な衝動だけでなく、3ヶ月、6ヶ月先の目標設定を習慣化し、定期的な振り返りの時間を設けることをお勧めします。また、他者の意見を聞く「一呼吸置く」習慣を作ることで、判断の精度がさらに向上します。失敗を恐れないエネルギーを保ちながらも、小さな成功を積み重ねる戦略を取り入れることで、持続可能な成長を実現できます。独立心を保ちつつも、時には他者との協力やチームワークの価値を認め、「一人で行くより、みんなで遠くへ」という視点も取り入れることで、影響力がさらに拡大します。'
            },
            
            'ACBL': {
                'summary': 'ソーラーは継続的で安定した活性化エネルギーを持つ太陽タイプです。周囲を温かく照らす存在感があり、持続可能な成長とポジティブな影響を与える力を持ちます。急激な変化よりも着実な進歩を好み、「継続は力なり」を体現する安定性のシンボルです。チームの中心的存在として、皆を支え励ます役割を自然に担い、長期的な視点で物事を捉える知恵を持っています。',
                'decision_style': '十分な情報収集と慎重な検討を経て、安定性と持続性を最優先に判断します。短期的な利益や一時的な感情に惑わされず、長期的な影響と周囲への波及効果を総合的に評価してから決断を下します。過去の経験と実績を重視し、リスクを最小限に抑えながらも確実な成果が期待できる選択肢を選びます。意思決定プロセスでは関係者の意見を丁寧に聞き、合意形成を大切にする傾向があります。急がされても焦らず、「急がば回れ」の精神で着実に進めます。',
                'choice_pattern': '持続可能性と安定性を重視し、長期的に維持できる選択肢を好みます。一時的な成功よりも継続的な成長を選び、周囲との調和を保ちながら着実に前進できる道を選択します。選択する際は「本当に続けられるか」「チーム全体にとって良いか」「将来に向けて建設的か」を重要な判断基準とします。新しい挑戦でも、既存の基盤を活かせるものや段階的に取り組めるものを選ぶ傾向があり、無謀な冒険よりも計算されたリスクテイクを好みます。',
                'risk_note': '安定性を重視するあまり保守的になりすぎ、必要な変化や革新の機会を逃すリスクがあります。慎重さが過度になると決断が遅れ、タイミングを失うことがあります。また、現状維持を優先しすぎて成長のチャンスを見逃したり、新しいアイデアや提案に対して消極的になる傾向があります。完璧を求めすぎて行動が遅くなったり、他者のペースに合わせることができずに孤立する場合もあります。変化を恐れて快適ゾーンから出ることを避け、潜在能力を十分に発揮できない可能性があります。',
                'relation_hint': '同じく安定志向で責任感の強い人との相性が抜群で、お互いを支え合いながら信頼できる長期的な関係を築けます。革新的で変化を好む人とは価値観の違いから最初は戸惑うこともありますが、お互いの強みを理解し合えれば非常にバランスの取れたパートナーシップが可能です。チームでは調整役や安定化要因として重要な役割を果たし、メンバーの不安を和らげ、結束力を高める存在になります。感情的にぶれやすい人に対しては、一貫した支援と安心感を提供することで信頼関係を深められます。',
                'growth_tip': '持続可能な成長スタイルを活かしながら、適度な変化と新しい挑戦を計画的に取り入れることで、より豊かで動的な成長を実現できます。月に1つ、新しい小さな挑戦を設定し、安全な環境で実験する習慣を作ることをお勧めします。また、革新的な人々との交流を意識的に増やし、異なる視点や アプローチを学ぶことで、安定性と創造性のバランスを向上させられます。「安定した土台の上での冒険」というアプローチで、リスクを最小限に抑えながら成長領域を広げていきましょう。'
            },
            
            'ACCV': {
                'summary': 'フレアは革新的な爆発的エネルギーを持つ変革者タイプです。既存の枠組みを打破し、新しい可能性を創造する力を発揮します。「なぜこうでなければならないの？」という問いを常に投げかけ、当たり前とされていることに疑問を持ちます。創造性豊かで斬新なアイデアを次々と生み出し、周囲を驚かせることが多いでしょう。変化を恐れるどころか楽しみ、「世界を変える」という大きな野心を持っています。',
                'decision_style': '既存の枠組みや常識にとらわれない革新的な判断を行います。「前例がない」ことはむしろチャンスと捉え、誰も考えつかなかったような斬新な解決策を生み出します。データよりも可能性を、実績よりも潜在力を重視し、「これをやったら面白いことになりそう」という創造的な直感に従います。判断プロセスでは多角的な視点から問題を観察し、異なる分野の知識を組み合わせて独創的なアプローチを見つけます。変革のビジョンが明確に見えた瞬間、迷わず大胆な決断を下します。',
                'choice_pattern': '革新性と創造性が最大限に発揮できる選択肢を積極的に選びます。「誰もやったことがない」「業界の常識を覆す」「ゲームチェンジャーになる」といった要素に強く惹かれます。安定した選択肢よりも変革的な可能性を秘めた選択を好み、リスクがあっても革命的な成果が期待できる道を選びます。選択基準は「どれだけインパクトがあるか」「どれだけ世界を変えられるか」「どれだけ創造的か」であり、既存のルールや制約は創造的に回避または再定義します。失敗を恐れず、むしろ失敗から学ぶことで次の革新につなげます。',
                'risk_note': '急進的すぎて周囲から「現実離れしている」と理解されないリスクがあります。アイデアが斬新すぎて実行段階で協力者を得られなかったり、既存の体制との摩擦が生じることがあります。また、次々と新しいアイデアに飛びつくため、一つのことを完成させる前に次に移ってしまう傾向があります。革新を追求するあまり基本的な安定性や継続性を軽視し、組織やチームの基盤を揺るがす可能性もあります。理想と現実のギャップに苦しむこともあるでしょう。',
                'relation_hint': '同じく革新的で創造的な思考を持つ人とは、アイデアの化学反応を起こし、想像を超えた成果を生み出せます。保守的な人とは最初は衝突することもありますが、相手の堅実さと自分の革新性を組み合わせることで、実現可能な革新を生み出せます。チームでは「イノベーター」「アイデアジェネレーター」として重要な役割を果たし、停滞を打破する起爆剤となります。伝統を重んじる人に対しては、変革のビジョンを分かりやすく説明し、段階的な変化を提案することで協力関係を築けます。',
                'growth_tip': '革新的なビジョンを現実に落とし込む実行力を身につけることで、真の変革者になれます。アイデアを100個出すよりも、1個を完成させることの価値を理解し、「革新的かつ実現可能」なスイートスポットを見つける訓練をしましょう。また、既存の仕組みを理解してから破壊することで、より効果的な変革を起こせます。月に一度は自分のアイデアを現実的な実行計画に落とし込む時間を設け、協力者を巻き込むコミュニケーション力を磨くことをお勧めします。'
            },
            
            'ACJG': {
                'summary': 'パルサーは規則的で予測可能なリズムを持つ調整者タイプです。組織に秩序と安定性をもたらし、システマティックな改善を得意とします。「すべてには最適なタイミングがある」という信念を持ち、周期的なパターンを見抜く能力があります。混沌とした状況でも冷静に規則性を見出し、効率的なプロセスを構築します。起動軸が高く行動力に優れているため、分析したら即座に実行に移す推進力を持っています。判断軸も高いため論理的かつ構造的な思考で問題を体系的に解決し、実利的・効率的な選択を好みます。独立した姿勢で自律的に業務を遂行し、感情に左右されない客観的な判断を下せる冷静さが強みです。チームの調整役として、異なる要素を論理的に整理し調和させる天性の才能を持っています。',
                'decision_style': '体系的なフレームワークと規則的なパターンに基づいて判断します。過去のデータと周期的な傾向を分析し、最適なタイミングと手順を見極めてから決断を下します。「急いては事を仕損じる」を座右の銘とし、適切なプロセスに従って着実に判断を積み重ねます。感情的な判断を避け、客観的な基準と再現可能な方法論を重視します。複雑な問題も要素分解して体系的に解決し、判断の根拠を明確に説明できることを重要視します。',
                'choice_pattern': 'システム全体の最適化と持続可能な改善につながる選択肢を好みます。「プロセスの改善」「効率の向上」「再現性の確保」といった要素を重視し、一時的な成果よりも長期的な仕組み作りを優先します。選択する際は「システムとして機能するか」「他の要素と調和するか」「規模拡大可能か」を判断基準とします。革新的すぎる選択よりも、着実な改善を積み重ねられる選択を好み、リスクを最小化しながら確実な成果を求めます。',
                'risk_note': '規則やプロセスに固執しすぎて柔軟性を失うリスクがあります。想定外の状況や例外的なケースに対応できず、システムの限界に直面することがあります。また、効率性を追求するあまり人間的な要素や創造性を軽視し、チームの士気を下げる可能性があります。完璧なシステムを求めすぎて、実装が遅れたり、過度に複雑な仕組みを作ってしまうこともあります。変化の速い環境では、システムの更新が追いつかないリスクもあります。',
                'relation_hint': '同じく体系的で組織的な人とは、高度に効率的なチームを形成できます。創造的で自由な人とは最初は価値観の違いに戸惑うかもしれませんが、お互いの強みを活かすことで、創造性と実行力を兼ね備えたバランスの良い関係を築けます。チームでは「プロセスマネージャー」「品質管理者」として重要な役割を果たし、全体の生産性を向上させます。感覚的な判断をする人に対しては、データと論理で説得することで理解を得られます。',
                'growth_tip': 'システム思考を維持しながら、適度な柔軟性と人間性を取り入れることで、より効果的な調整者になれます。「80%の完成度で動き始める」勇気を持ち、実践を通じてシステムを改善する反復的アプローチを採用しましょう。また、月に一度は既存のプロセスを見直し、不要な複雑性を削減する「断捨離」の時間を設けることをお勧めします。人の感情や創造性もシステムの重要な要素として組み込む視点を養いましょう。'
            },
            
            'ACRN': {
                'summary': 'レディエントはエネルギーの伝播と拡散を特徴とする感染源タイプです。ポジティブな活力を周囲に伝染させる特別な能力を持ち、一人の情熱が組織全体を活性化させます。「エネルギーは共有することで増幅する」という信念のもと、自分の熱意を惜しみなく分かち合います。疲れた チームに新しい風を吹き込み、停滞した空気を一変させる触媒としての役割を果たします。人々の潜在的なエネルギーを引き出す天性の才能があります。',
                'decision_style': 'エネルギーの波及効果と感染力を最優先に判断します。「この決断がどれだけの人にポジティブな影響を与えるか」「どれだけエネルギーの連鎖反応を起こせるか」を重視し、個人の利益よりも全体の活性化を考えて決断します。直感的に「盛り上がる」「みんなが元気になる」選択肢を見抜き、時には論理を超えて情熱に従います。決断のスピードは速く、「やってみなければ分からない」精神で、エネルギーが高まっているうちに行動に移します。ネガティブな選択肢は本能的に避け、常に前向きな可能性を追求します。',
                'choice_pattern': 'エネルギーの拡散と共鳴を最大化できる選択肢を選びます。「みんなで盛り上がれる」「熱気が伝染する」「ポジティブな連鎖が起きる」要素に強く惹かれます。個人プレーよりチームプレー、閉鎖的より開放的、静的より動的な選択を好みます。選択基準は「どれだけ多くの人を巻き込めるか」「どれだけエネルギーレベルを上げられるか」「どれだけ楽しくできるか」です。困難な選択でも、それをポジティブな挑戦として捉え直し、周囲を鼓舞する機会に変えます。',
                'risk_note': 'エネルギーの拡散に注力するあまり、深さより広さを重視しすぎるリスクがあります。表面的な盛り上がりで終わってしまい、実質的な成果が伴わないこともあります。また、常にハイテンションを維持しようとして燃え尽きたり、周囲が疲弊することもあります。冷静な分析や慎重な計画を軽視し、勢いだけで突き進んで失敗する可能性もあります。ネガティブな感情や問題を避けすぎて、根本的な課題解決が遅れるリスクもあります。',
                'relation_hint': '同じくエネルギッシュで前向きな人とは、相乗効果で驚異的なパワーを生み出せます。内向的で慎重な人に対しては、相手のペースを尊重しながら徐々にエネルギーを分け与えることで、信頼関係を築けます。チームでは「ムードメーカー」「モチベーター」として不可欠な存在となり、組織の活力源として機能します。エネルギーが低い人も、あなたと接することで自然と元気を取り戻すでしょう。批判的な人とも、ポジティブな姿勢で接することで徐々に理解を得られます。',
                'growth_tip': 'エネルギーの拡散力を保ちながら、深さと持続性を加えることで、より大きな影響力を持てます。「エネルギーの質」にも注目し、単なる興奮ではなく、意味のある情熱を伝える技術を磨きましょう。週に一度は静かな時間を設け、エネルギーの充電と内省を行うことをお勧めします。また、他者のエネルギーレベルを読み取り、適切な強度で関わる「エネルギーマネジメント」のスキルを身につけることで、より効果的な感染源となれます。'
            },
            
            'ACCP': {
                'summary': 'フォーカスは集中的で深い掘り下げを特徴とする専門家タイプです。一点集中の驚異的な集中力を持ち、選んだ分野を極限まで追求します。「広く浅く」より「狭く深く」を信条とし、専門領域では誰にも負けない深い知識と技術を持っています。表面的な理解では満足せず、物事の本質と核心に到達するまで探求を続けます。起動軸が高いため、興味を持った分野には即座に飛び込み、積極的に学習・実践を重ねます。判断軸も高く論理的・分析的なアプローチで専門知識を体系化し、実利的・効率的な成果を重視します。独立心が強く、自らの専門性に基づいて自律的に判断・行動する姿勢を持ち、他者の評価に左右されず自分の道を突き進みます。その道のプロフェッショナルとして、専門分野で卓越した価値を創造し、具体的な成果で周囲に貢献します。',
                'decision_style': '専門的な深い知識と徹底的な分析に基づいて判断します。自分の専門領域に関しては絶対的な自信を持ち、データ、理論、実践経験を総合して最適解を導き出します。「なぜそうなのか」を5回以上問い続け、根本原因と本質に到達してから決断します。一般論や表面的な情報には惑わされず、深い洞察と専門知識を武器に独自の判断を下します。時間をかけてでも正確で深い判断を重視し、専門外のことは謙虚に専門家に委ねます。',
                'choice_pattern': '専門性を深められる選択肢、極めることができる選択肢を強く好みます。「この分野の第一人者になれるか」「深い専門知識が活かせるか」「極限まで追求できるか」を判断基準とします。幅広い選択肢より、一つの道を究める選択を好み、長期的なコミットメントを前提とした選択を行います。浅い関わりや中途半端な選択肢は避け、「やるなら徹底的に」という姿勢で選択します。専門分野に関連する選択では妥協せず、最高水準を追求します。',
                'risk_note': '専門分野に没頭するあまり視野が狭くなり、他の重要な要素を見落とすリスクがあります。完璧主義が過度になり、80%の完成度で十分な場面でも100%を求めて時間を浪費することがあります。また、専門外の領域への関心が薄く、バランスの取れた成長が阻害される可能性があります。専門用語を多用して一般の人とのコミュニケーションが困難になったり、柔軟性を失って環境変化に適応できなくなるリスクもあります。',
                'relation_hint': '同じ分野の専門家とは、深い技術談義で盛り上がり、お互いを高め合える関係を築けます。ジェネラリストタイプの人とは、相手の広い視野と自分の深い専門性を組み合わせることで、強力なチームを形成できます。一般の人に対しては、専門知識を分かりやすく伝える「翻訳者」の役割を意識することで、良好な関係を築けます。異分野の専門家との交流は、新しい視点と応用の可能性をもたらします。',
                'growth_tip': '深い専門性を維持しながら、隣接領域への理解も深めることで、より価値のある専門家になれます。「T字型人材」（深い専門性＋広い基礎知識）を目指し、月に一度は専門外の分野に触れる時間を作りましょう。また、専門知識を一般の人に伝える「ストーリーテリング」の技術を磨くことで、影響力を拡大できます。「森を見て木も見る」バランス感覚を養い、専門性の社会的意義を常に意識することをお勧めします。'
            },
            
            # 判断軸 (JD)
            'JDPU': {
                'summary': 'マーキュリーは、「なぜそうなるのか?」を徹底的に追求する論理思考のスペシャリストです。複雑な状況を冷静に分析し、データと根拠に基づいて明確な結論を導き出す能力に優れています。感情や雰囲気に流されることなく、客観的な事実と論理的な因果関係を重視し、「本当に正しいのは何か」を見極めます。曖昧さや矛盾を許さず、すべての物事に明確な理由と説明を求める理性の体現者です。複雑に絡み合った問題でも、一つ一つ丁寧に紐解き、誰もが納得できる論理的な解決策を提示します。チームの意思決定において、感情的な議論を冷静に整理し、客観的な視点から最適な方向性を示す信頼される分析者です。',
                'decision_style': '「データは嘘をつかない」という信念のもと、客観的な証拠、統計情報、過去の事例を徹底的に収集・分析してから判断を下します。感情的な要素や雰囲気による判断は極力避け、論理的整合性と因果関係の明確性を最重視します。複数の仮説を立てて一つ一つ検証し、最も合理的で説明可能な結論に到達することを得意とします。「なぜそうなるのか」「どんな根拠があるのか」を常に問い続け、曖昧な直感や感覚ではなく、明確な理由に基づいた決断を行います。急いで結論を出すことはせず、十分な情報と分析を経た上で、確信を持って判断します。',
                'choice_pattern': '選択の基準は「論理的根拠の強さ」「データの信頼性」「説明可能性の高さ」です。直感や「なんとなく良さそう」といった感覚的な選択は避け、必ず「なぜその選択なのか」を他者に明確に説明できる根拠を持ちます。短期的な感情や一時的な気分よりも、長期的な合理性と持続可能性を重視した冷静な判断を下します。リスクとリターンを客観的に比較検討し、成功の確率が最も高い選択肢を論理的に見極めます。感情に訴える選択肢よりも、データが支持する実用的な選択肢を好み、確実性と再現性のある道を選びます。',
                'risk_note': '論理性を重視するあまり、人間の感情や直感的な洞察を軽視してしまう傾向があります。データや数字で表現できない要素(創造性、チームの士気、人間関係の微妙なニュアンス、文化的背景)を見落とし、人間関係で摩擦を生むリスクがあります。また、分析に時間をかけすぎて決断のタイミングを逃したり、「完璧な論理的根拠」を求めすぎて行動が遅れる可能性もあります。論理的に正しくても、人の心に響かない提案になってしまい、周囲から「冷たい」「融通が利かない」と思われることもあります。不確実性の高い状況や創造的な発想が求められる場面では、論理だけでは解決できないジレンマに直面することがあります。',
                'relation_hint': 'チームでは、複雑な問題の分析や戦略立案の場面で頼れる存在として重宝されます。感情的になりがちな議論を冷静に整理し、客観的な視点から最適な解決策を提示する能力に長けています。論理的な説明を求める人や、データ重視の組織文化では特に信頼を得やすく、意思決定のアドバイザーとして活躍できます。一方で、メンバーの感情面でのサポートや、創造的なブレーンストーミングの場では、論理を一旦脇に置き、自由な発想を受け入れる柔軟性を意識することが大切です。感情的な人との協力では、相手の気持ちを尊重しながら論理的な視点を提供することで、バランスの取れた関係を築けます。',
                'growth_tip': '優れた論理性という強みを活かしながら、人間の感情や直感も重要な判断材料として受け入れることで、より豊かな意思決定ができるようになります。「データでは表現できない価値」の存在を認め、時には感情的な配慮や直感的な判断も含めた総合的な思考を心がけましょう。完璧な論理を求めすぎず、80%の確信で行動し、実行しながら調整する柔軟性を育てることで、スピード感も向上します。論理的分析力に加えて、人の心に響くコミュニケーション力を磨くことで、真に影響力のあるリーダーシップを発揮できます。「正しいだけでなく、人を動かす力」を身につけることが、さらなる成長の鍵です。'
            },
            
            'JDRA': {
                'summary': 'クリスタルは、複雑に絡み合った要素を美しく統合する「調和の建築家」です。「すべての声に耳を傾け、最適解を見つける」という信念のもと、論理と感情、短期と長期、個人と全体など、対立しがちな要素を巧みにバランスさせます。クリスタルのように透明で純粋な視点から、関係者全員が納得できる解決策を見出す全体最適化のスペシャリストです。多様なステークホルダーの利害を丁寧に調整し、誰も取り残さない包括的なアプローチで、持続可能な合意を形成します。複雑な対立や矛盾を恐れず、それらを新しい価値創造の機会として捉え、Win-Winの関係構築に導く調整力の達人です。',
                'decision_style': '「一面的な見方では真実は見えない」という信念で、ステークホルダー全員の視点を丁寧に収集・整理します。一つひとつの意見の背景にある真のニーズや価値観を理解し、表面的な対立の奥にある本質的な共通点を見出します。データ分析と人間的配慮を両立させ、論理的妥当性と感情的受容性の両方を満たす判断を目指します。対話と合意形成を重視したコンセンサス型リーダーシップが特徴で、プロセスの透明性と関係者の参加を大切にします。時間をかけてでも、全員が納得できる質の高い合意を形成することを優先します。',
                'choice_pattern': 'Win-Winの関係構築を最優先に、「誰かが大きく損をする選択」は避けます。短期的利益よりも長期的な信頼関係を重視し、一時的な妥協や調整も厭いません。選択プロセスでは関係者の納得感を大切にし、透明性の高い意思決定を心がけます。「この選択で誰が幸せになり、誰が不満を持つか」「長期的に見て持続可能か」「関係性を強化できるか」を重要な判断基準とします。単に中間点を取るのではなく、異なる価値を統合して新しい価値を創造する「統合的解決策」を追求します。全員が少しずつ歩み寄ることで、より良い全体解を生み出すことを信じています。',
                'risk_note': '全方位に配慮しすぎて優先順位が曖昧になり、「八方美人」な判断に陥るリスクがあります。コンセンサスを重視するあまり決断が遅くなり、機会を逃したり、時には必要な「痛み」を伴う決断を避けてしまう可能性もあります。すべての人を満足させようとして、最終的に誰も満足しない妥協案になってしまうこともあります。調整に時間とエネルギーを使いすぎて、実行段階でのスピード感が失われるリスクもあります。また、対立を避けるあまり、必要な変革や革新を躊躇してしまう場合があります。',
                'relation_hint': 'チーム内の対立調整や利害関係者間の橋渡し役として不可欠な存在です。異なる部署や立場の人々をつなぐハブ的機能を果たし、組織全体の結束力向上に大きく貢献します。複雑な交渉や調整が必要な場面で真価を発揮し、「この人に任せれば皆が納得する解決策が見つかる」と信頼されます。決断力のあるリーダーとペアを組むことで、調整力とスピード感のバランスが取れた強力なチームを形成できます。ただし、緊急時には「スピード重視の決断」も時には必要な場面があります。',
                'growth_tip': '全体調整力という貴重な才能を活かしつつ、「時には明確な優先順位をつける勇気」を身につけましょう。すべてを均等に扱うのではなく、状況に応じて「何を最も重視すべきか」を明確にし、時には厳しい決断も下せるリーダーシップを目指しましょう。「全員の意見を聞く」ことと「全員の要求を満たす」ことは別であることを理解し、真に重要な価値を守るためには、時に妥協しない強さも必要です。調整力と決断力のバランスを取ることで、真の統合型リーダーとして成長できます。定期的に「今、最も重要なことは何か」を自問する習慣を持ちましょう。'
            },
            
            'JDCP': {
                'summary': 'コスモスは「異なる価値観こそが新しい解決策を生む」という信念を持つ統合創造の革新者です。対立する意見や異質な要素を敵視せず、それらを新たな価値創造の材料として捉え、誰も思いつかなかった第三の道を見出す統合思考の達人です。宇宙が無数の星の調和から成り立つように、多様な視点を一つの美しいビジョンに統合する力を持っています。「AかBか」という二項対立を超えて、「AもBも活かした新しいC」を創造することで、誰もが納得できる革新的な解決策を生み出します。複雑に絡み合った利害関係や対立する価値観の中で、それぞれの本質的な価値を見抜き、より高い次元で統合する戦略的思考の持ち主です。チームや組織において、異なる部門や立場の人々をつなぎ、シナジーを生み出す触媒として機能し、「不可能」と思われた合意形成を実現する希少な才能を持っています。',
                'decision_style': '「対立は創造の母」として、異なる視点や価値観の衝突を恐れません。むしろ多様性から生まれる化学反応を期待し、従来の枠組みを超えた革新的解決策を模索します。「Either/Or」ではなく「Both/And」の発想で、一見不可能に見える統合解を追求します。判断を下す前に、関係する全てのステークホルダーの視点を丁寧に収集・分析し、それぞれが本当に求めているもの（表面的な要求ではなく、根本的なニーズ）を深く理解しようとします。対立する意見があれば、その背景にある価値観や経験を探り、「なぜそう考えるのか」を真摯に理解することで、統合の糸口を見つけます。データと論理を駆使しながらも、人間的な感情や価値観も重要な判断材料として扱い、理性と感性のバランスが取れた総合的な判断を行います。急いで結論を出すことはせず、十分な対話と探索を経て、全員が「これなら納得できる」と感じられる解決策が見つかるまで粘り強く思考を続けます。',
                'choice_pattern': '既存の選択肢に満足せず、「第三の道はないか？」「異なる要素を組み合わせて新しい解決策を作れないか？」と常に創造的思考を働かせます。関係者の根本的なニーズを理解し、表面的な要求の奥にある本質的な課題解決を目指します。「AかBか」という二者択一を提示されても、「AとBの良いところを組み合わせた新しい選択肢Cは作れないか」と考えます。複数の価値観や利害が絡む複雑な状況ほど力を発揮し、誰かを犠牲にする選択ではなく、全員にとってより良い結果を生む統合的な選択を追求します。選択する際は、「この選択は長期的に持続可能か」「関係者全員の本質的なニーズを満たしているか」「新しい価値を創造できるか」を重要な判断基準とします。単なる妥協や中間点を取るのではなく、異なる要素を化学反応させて、まったく新しい価値を創造することを目指します。',
                'risk_note': '理想的な統合解を求めるあまり、現実的な制約を軽視したり、実現可能性の低いアイデアに固執するリスクがあります。また、統合プロセスが複雑になりすぎて、関係者が混乱したり、実行段階で困難に直面する可能性もあります。完璧な統合解を探し続けて決断が遅れ、タイミングを逃してしまうことがあります。多様な意見を統合しようとするあまり、結果として誰にとっても中途半端な解決策になってしまうリスクもあります。また、「統合できるはず」という楽観的な信念が強すぎて、本当に統合不可能な対立（価値観の根本的な相違など）を認めることが難しい場合があります。複雑な統合プロセスを説明することに時間がかかり、シンプルな解決策を求める人からは「考えすぎ」「複雑にしすぎ」と批判されることもあります。',
                'relation_hint': '困難な調整役や革新的プロジェクトのリーダーとして重宝されます。利害が対立する状況で新しい解決策を提示し、「不可能」と思われた合意を実現する能力に長けています。創造的なチームワークと変革のファシリテーターとして組織に価値をもたらします。同じく統合的思考を持つ人とは、複雑な問題を多角的に分析し、革新的な解決策を共に創造できる最高のパートナーシップを築けます。論理的で分析力の高い人とは、アイデアの実現可能性を検証し合い、地に足のついた革新を生み出せます。感情的・直感的な人とは、論理だけでは見えない人間的な要素を統合に取り入れることで、より包括的な解決策を創造できます。チームでは、異なる部門や立場の人々をつなぐ「橋渡し役」として機能し、サイロ化を防ぎ、組織全体のシナジーを高める重要な役割を果たします。対立が起きた際には、両者の言い分を深く理解し、新しい視点を提示することで、建設的な解決に導く調停者となります。',
                'growth_tip': '統合創造力という希少な才能を活かしつつ、「実現可能性とのバランス」を意識しましょう。理想的な統合解と現実的な制約の中で最適点を見つけ、段階的実行プランを描く能力を磨くことで、真の変革リーダーとして成長できます。「100%の統合」を目指すよりも、「80%の統合で前に進む」勇気も大切です。完璧な統合解を探し続けるよりも、実行しながら調整していく反復的アプローチを取り入れることで、より多くの統合を実現できます。また、統合プロセスをシンプルに説明する技術を磨き、関係者が理解しやすい形でビジョンを伝えることで、より多くの人を巻き込んだ変革を起こせます。時には「今は統合できない」という現実を受け入れ、将来の統合に向けた種を蒔くという長期的な視点も持ちましょう。統合的思考を実務的な成果に結びつける実行力を高めることで、「理想主義者」ではなく「実現する理想主義者」として、真に世界を変える力を発揮できます。'
            },
            
            'JDCV': {
                'summary': 'マトリックスは、複雑な情報を多次元的に統合する「知識の建築家」です。膨大なデータや概念を独自の視点で体系化し、誰も見たことのない知識構造を構築する力に優れています。「知識は構造化されて初めて価値を持つ」という信念を持ち、抽象的な概念を明確な形に変換する能力に長けています。論理と直感を高度に融合させ、一見無関係に見える情報の間に隠された法則性を発見します。自己の内面を深く探求しながら、理想的な知識体系を追求し、独立した思考で複雑な問題を解き明かす知的探求者です。',
                'decision_style': '「データと論理に基づく構造的思考」を重視し、複雑な情報を多角的に分析して判断を下します。表面的な現象だけでなく、その背後にある構造やパターンを見極め、本質的な理解に基づいた意思決定を行います。独自の分析フレームワークを用いて情報を整理し、論理的な一貫性を保ちながら最適な結論を導き出します。感情や人間関係よりも、客観的な事実と論理的整合性を優先し、冷静で筋の通った判断を心がけます。深い内省を通じて自らの判断基準を常に洗練させ、より精度の高い意思決定を目指します。',
                'choice_pattern': '「論理的に最も筋が通っている選択肢は何か」「この選択は理想的な構造に近づくか」という視点で選択します。感情的な要素よりも、客観的な基準と構造的な美しさを重視し、自らの価値観と整合性のある選択を追求します。複数の選択肢を多次元的に比較分析し、それぞれのメリット・デメリットを体系的に評価してから決断を下します。短期的な便宜よりも、長期的な価値と理想への接近を優先し、妥協のない選択を行う傾向があります。独自の判断基準に自信を持ち、他者の意見に流されず、自分自身の分析結果を信じます。',
                'risk_note': '論理と構造を重視するあまり、人間関係や感情的な側面を軽視してしまうリスクがあります。自分の分析や理論に固執しすぎて、他者の視点を取り入れることが難しくなる場合があります。また、複雑な構造を追求するあまり、シンプルで実用的な解決策を見落とすこともあります。独立的な思考スタイルが孤立を招き、チームワークに支障をきたす可能性もあります。理想的な構造を求めすぎて、現実的な制約を無視したり、「完璧な分析」に時間をかけすぎて決断が遅れるリスクもあります。',
                'relation_hint': '複雑な問題を構造化し、明確な方向性を示す能力でチームに貢献します。論理的な分析と体系的な知識構築において右に出る者はおらず、難解な課題を解きほぐす専門家として重宝されます。同じく知的探求を好む人とは、深い議論と知識の共有を楽しめる関係を築けます。感情面での配慮が必要な場面では、共感力の高いメンバーとの協力が効果的です。独自の視点と分析力を活かしながら、他者の意見にも耳を傾けることで、より包括的な理解に到達できます。',
                'growth_tip': '優れた論理的思考力と構造化能力を活かしつつ、「人間関係の重要性」にも目を向けましょう。知識や論理だけでは解決できない問題があることを理解し、時には感情的な要素も判断材料に含める柔軟性を育てることが成長につながります。独立的な思考を保ちながらも、他者との対話を通じて自分の視野を広げ、異なる視点を取り入れる姿勢を持ちましょう。また、完璧な構造を求めすぎず、「十分に良い」段階で行動に移す実行力も大切です。知識の建築家としての才能を、現実世界で価値ある成果に変換する力を磨いていきましょう。'
            },
            
            # 選択軸 (CH)
            'CHRA': {
                'summary': 'ヴィーナスは、「美しいものを選び、美しい未来を創る」理想主義の価値追求者です。単なる機能性や効率性を超えて、美的価値、倫理的価値、精神的価値を重視し、心が豊かになる選択を追求します。表面的な利害よりも深い意味と価値を見出し、自分らしい人生を築く美意識の体現者です。「本当に大切なものは何か」を見抜く審美眼を持ち、安易な妥協を許さず、品格と洗練を日常のあらゆる選択に求めます。短期的な便利さよりも長期的な価値を、流行よりも普遍的な美しさを、量よりも質を、効率よりも意味を大切にします。物質的な豊かさ以上に、精神的な満足感と美的な充足感を重視し、生活の一つひとつの選択を芸術作品のように丁寧に作り上げていく、真の美意識の実践者です。',
                'decision_style': '「これは自分の価値観に合っているか?」「これは美しい選択か?」「これは理想に近づく道か?」を基準に選択します。損得勘定よりも価値観との一致を重視し、心から納得できる選択を求めます。時間をかけてでも、妥協のない理想的な解決策を見つけることを大切にします。感覚的な美しさだけでなく、倫理的な正しさ、精神的な豊かさ、長期的な意義といった多層的な価値を総合的に判断し、「自分の魂が YES と言える選択」を追求します。他者の評価や一般的な常識よりも、自分の内なる声と美意識を信じ、表面的な便利さや効率性に流されず、本質的な価値を持つ選択を貫きます。急いで決めることなく、熟考と直感の両方を使って、最も美しく意味のある道を見出します。',
                'choice_pattern': '美しさ、優雅さ、調和、意味深さを感じられる選択肢に強く惹かれます。「魂が喜ぶ」「心が躍る」「価値観が満たされる」選択を最優先とし、短期的な利便性よりも長期的な満足感を重視します。品質の高さや洗練されたデザイン、深い哲学を持つ選択肢を好み、「安かろう悪かろう」の妥協は避けます。素材の質感、色合いの調和、形の美しさ、製作者の思いといった細部にまでこだわり、「本物」と「偽物」を見分ける鋭い審美眼を持っています。流行に左右されず、時代を超えて愛される普遍的な美しさを持つものを選び、一時的な満足よりも永続的な価値を求めます。「この選択は私を成長させるか」「この選択は世界を少しでも美しくするか」という視点も大切にします。',
                'risk_note': '理想を追求するあまり現実的な制約を軽視し、実現不可能な選択に固執するリスクがあります。また、美的基準や価値観が厳しすぎて、他者を批判的に見たり、選択肢を狭めすぎる可能性もあります。完璧主義的傾向により、「80%の完成度」でも十分な場面で過度に時間をかけることがあります。理想と現実のギャップに苦しみ、「妥協」を敗北と感じてしまうこともあります。美しさや価値観を優先するあまり、実用性やコストパフォーマンスを軽視し、生活が立ち行かなくなるリスクもあります。また、自分の美意識や価値観を他者に押し付けてしまい、価値観の違いを受け入れられずに孤立する危険性もあります。',
                'relation_hint': '同じく美意識や価値観を大切にする人とは、深い共感と理解を共有できます。実用主義の人とは最初は価値観の違いを感じるかもしれませんが、お互いの視点を尊重することで、理想と現実のバランスが取れた関係を築けます。芸術や文化への関心が高い人との交流では、互いを高め合える関係になります。あなたの美意識は、周囲の人々の選択の質を高め、生活に豊かさと彩りをもたらす影響力を持っています。価値観の合う人とは魂レベルでつながる深い友情を育み、お互いの美しい生き方を尊重し合える最高のパートナーシップを築けます。',
                'growth_tip': '理想を追求する美しい心を大切にしながら、「不完全の美」も受け入れる柔軟性を身につけましょう。現実的な制約の中で理想に近づく「段階的美意識」を育み、「今できる範囲での最良」を選択する実践力を磨くことで、理想と現実を橋渡しする真の美意識の体現者になれます。完璧を求めすぎず、80%の美しさでも前に進む勇気を持つことで、より多くの美しい選択を実現できます。また、異なる価値観や美意識を持つ人々の視点も学び、「美の多様性」を理解することで、より豊かで広がりのある美意識を育てられます。'
            },
            
            'CHJA': {
                'summary': 'ディアナは、「優雅さと洗練さこそが真の強さ」と信じる美意識の体現者です。単なる機能性や実用性を超えて、美しさ、優雅さ、品格を重視した選択を行います。ローマ神話の月と狩猟の女神のように、凛とした気品と洗練された美しさを持ち、表面的な華やかさではなく、深い教養と磨かれたセンスに基づいた美しい生き方を追求します。「安ければ良い」「便利なら十分」という価値観ではなく、「本当に良いものとは何か」を見極める審美眼を持ち、時代を超えて愛される普遍的な価値を大切にします。質の高さと美しさを妥協せず、生活のあらゆる場面で品格と洗練を追求する、真のエレガンスの体現者です。',
                'decision_style': '「これは美しいか?」「これは品格があるか?」「これは洗練されているか?」を基準に選択します。短期的な利益や効率性よりも、長期的な品質と美的価値を重視します。「急がば回れ」の精神で、時間をかけてでも本当に優れた選択を追求し、妥協することなく最高の質を求めます。デザイン、質感、雰囲気、細部のディテールまで注意深く観察し、「これは自分の美意識に合うか」「これは長く愛せるか」を丁寧に吟味してから決断します。流行や他者の評価よりも、自分の審美眼と価値観を信じ、本質的な美しさを持つものを選びます。単に「使える」だけでなく、「美しく使える」ことを重視します。',
                'choice_pattern': '「品質の高さ」「デザインの美しさ」「使いやすさの優雅さ」を重視した選択を行います。安さだけが売りの商品やサービスよりも、適正な価格で本物の価値を提供する選択肢を好みます。時代を超えて愛されるクラシックな価値を持つ選択を重視し、一時的な流行に左右されることなく、永続的な美しさを追求します。素材の質、職人の技、ブランドの歴史や哲学といった、目に見えない価値も大切にし、「なぜこれが美しいのか」を深く理解した上で選択します。大量生産品よりも、丁寧に作られた一点ものや、ストーリーのある品を選ぶ傾向があります。機能性と美しさが両立した「機能美」を理想とします。',
                'risk_note': '美的基準が高すぎて、実用的な必要性や便利性を軽視してしまうリスクがあります。また、完璧な美しさを求めすぎて決断が遅くなったり、高すぎる理想に固執して現実的な選択肢を逃す可能性もあります。美へのこだわりが強すぎると、周囲から「こだわりすぎ」「現実的でない」と思われることもあります。予算や時間の制約を軽視して、美しさだけを追求してしまうリスクもあります。また、自分の美的基準を他者にも求めすぎて、価値観の押し付けになってしまう可能性があります。美意識が狭い視野を生み、「美しくないもの」の価値を見落とすこともあります。',
                'relation_hint': '同じく美意識や品質へのこだわりを持つ人とは、深い美的価値を共有し、お互いのセンスを尊重し合える豊かな関係を築けます。実用主義の人とは最初は価値観の違いを感じるかもしれませんが、お互いの強みを理解し合うことで、美と実用を共に満たす素晴らしい選択を生み出せます。芸術や文化への関心が高い人との交流では、お互いの美的センスを高め合い、新しい美の発見を楽しめる関係になります。チームでは、デザインや品質管理の場面であなたの審美眼が重宝され、製品やサービスの質を高める重要な役割を果たせます。美しさを大切にする姿勢は、周囲に良い影響を与え、環境全体の質を向上させます。',
                'growth_tip': '美への高い意識を保ちながら、「機能美」という概念も取り入れましょう。使いやすさや効率性も美しさの一部であることを理解し、「実用的でありながら美しい」というバランスの取れた選択を目指すことで、より実際的で影響力のある美意識の体現者になれます。「完璧な美」を求めすぎず、「十分に美しく、実用的」という基準も持つことで、決断のスピードが上がり、より多くの美を生活に取り入れられます。また、様々な文化や価値観における「美」の多様性を理解することで、より広く深い美意識を育てられます。美を追求することと、現実的な制約の中で最善を尽くすことのバランスを取ることが、真の成長につながります。'
            },
            
            'CHAT': {
                'summary': 'ユーレカは、「発見の瞬間が世界を変える」と信じる革新的価値発見のイノベーターです。既存の枠組みや常識に縛られず、「これまで誰も気づかなかった価値」を発見し、新しい選択肢を創造する天才的な発想力を持っています。アルキメデスの「ユーレカ!(わかった!)」の瞬間のように、誰も見たことのない角度から問題を捉え直し、まったく新しい解決策を生み出します。「今あるもの」に満足せず、「まだ存在しないが、あるべきもの」を追求し、世の中に革新的な価値をもたらす価値創造の開拓者です。既存の選択肢の中から選ぶのではなく、新しい選択肢そのものを創り出すことで、未来を切り開いていきます。',
                'decision_style': '「既存の選択肢で本当に十分か?」「まだ誰も考えついていない第三の道はないか?」と常に新しい可能性を模索します。伝統的な方法や一般的な解決策に満足することなく、独自の視点で問題を根本から再定義し、革新的なアプローチで解決策をデザインします。「みんながAかBかで迷っているなら、自分は誰も思いつかなかったCを創り出す」という発想で、既成概念を打ち破ります。慣習や前例に縛られず、「もし制約がなかったら、本当はどうあるべきか?」という本質的な問いから思考を始め、理想の姿から逆算して新しい道を切り開きます。失敗を恐れず、試行錯誤を通じて誰も見たことのない価値を発見します。',
                'choice_pattern': '「オリジナリティ」「創造性」「未来性」「革新性」を最重視し、「今までにない」「新しい価値を創造できる」選択肢に強く心を動かされます。安全で予測可能な選択よりも、リスクがあっても未知の領域を開拓できる可能性を秘めた選択を好みます。「この選択は世界に新しい価値をもたらすか?」「これまでにない体験を生み出せるか?」が最終的な判断基準です。既存の成功事例を踏襲するよりも、まだ誰も試したことのない実験的なアプローチに魅力を感じ、「第一人者」「パイオニア」として新しい道を切り開くことに情熱を注ぎます。保守的で安定した選択よりも、革新的で挑戦的な選択を追求します。',
                'risk_note': '新しさを追求するあまり、実用性や安定性を軽視してしまうリスクがあります。革新的すぎて周囲に理解されなかったり、理想が高すぎて実現可能性の低いアイデアに固執してしまうこともあります。常に新しいことを求めて、一つのことを最後までやり抜かずに次のアイデアに飛びついてしまう傾向があります。「発見すること」に情熱を注ぎすぎて、「実現すること」や「継続すること」の重要性を見落とし、多くのアイデアが未完成のまま終わってしまう可能性もあります。また、既存の価値や実績を軽視しすぎて、「車輪の再発明」に時間を費やしてしまうリスクもあります。',
                'relation_hint': '同じく革新的で創造的な人とは、アイデアの化学反応で驚くべきイノベーションを生み出せます。お互いの発想を刺激し合い、誰も思いつかなかった新しい価値を次々と創造できる最高のパートナーシップを築けます。実務的で慎重な人とは最初は価値観の違いを感じるかもしれませんが、あなたの革新性と相手の実現力を組み合わせることで、「革新的かつ実現可能」な素晴らしい価値を世の中に届けられます。チームでは、新しい視点や斬新なアイデアを提供する創造的な触媒として、停滞した状況に突破口をもたらす存在になれます。',
                'growth_tip': '革新的な発想力を保ちながら、「一つのアイデアを最後までやり抜く持続力」を身につけましょう。100のアイデアを出すよりも、1つのアイデアを現実に変えることの価値を理解し、「発見から実現まで」のプロセス全体をやり遂げる力を育てることが重要です。「革新的かつ実現可能」なスイートスポットを見つけるスキルを磨き、理想と現実のバランスを取ることで、真に世界を変える価値を生み出せます。革新性に加えて、忍耐力と継続力を身につけることで、「アイデアマン」から「真のイノベーター」へと成長できます。'
            },
            
            'CHJG': {
                'summary': 'アテナは、「智恵と戦略で勝利をつかむ」慎重な守護者です。軽率な選択を避け、十分な情報収集と綿密なリスク評価を行った上で、最も安全で効果的な選択を行います。ギリシャ神話の知恵の女神のように、冷静な分析力と戦略的思考で、困難な状況でも確実に成果を出す道を見極めます。短期的な成果や一時的な魅力よりも、長期的な安定と持続可能性を重視する、計算された賢明さの持ち主です。「失敗しない選択」ではなく「成功する可能性が最も高い選択」を追求し、あらゆるリスクを事前に想定してバックアッププランを用意します。チームの意思決定において、楽観的な雰囲気に流されず、冷静に潜在的なリスクを指摘し、確実な勝利へと導く戦略的アドバイザーです。',
                'decision_style': '「この選択のリスクは何か?」「最悪のケースは何か?」「バックアッププランはあるか?」を必ず確認してから決断を下します。衝動的な選択や感情に流された判断を避け、数歩先を読んだ戦略的な思考で最適な道を選びます。一つの情報源だけでなく、多方面から客観的なデータを収集し、複数の視点で検証した上で冷静に評価します。「うまくいったらこうなる」という楽観的シナリオだけでなく、「失敗したらどうするか」というリスク対策も同時に考え、どんな状況でも対応できる準備を整えてから行動します。短期的な利益に惑わされず、長期的な視点で持続可能な成果を生む選択を重視します。',
                'choice_pattern': '「安全性」「信頼性」「持続可能性」「実績」を最重視した選択を行います。新奇さや流行に飛びつくのではなく、実証済みの価値と確かな実績のある選択肢を好みます。短期的な魅力よりも長期的な安定性を優先し、「確実に成果が出る」選択を重視します。リスクとリターンのバランスを慎重に計算し、成功の可能性が最も高い最適解を選択します。未知の要素が多い選択肢よりも、予測可能性が高く、コントロール可能な要素が多い選択肢を好み、「賭け」ではなく「計算された投資」として意思決定を行います。冒険的な選択よりも、着実に前進できる現実的な道を選びます。',
                'risk_note': '慎重さが過度になり、チャンスを逃したり、意思決定が遅くなるリスクがあります。完璧な計画を求めすぎて、「まず行動してみる」という選択肢を見落とし、機会損失につながる可能性があります。また、リスクを減らすことに集中しすぎて、大きな成果や革新的な価値創造の機会を見逃すこともあります。安全志向が強すぎると、必要な冒険やチャレンジを避けてしまい、成長の機会を逃すリスクがあります。完璧な情報を求めすぎて実行のタイミングを逸したり、慎重すぎて周囲から「決断力に欠ける」と見られることもあります。不確実性を避けるあまり、イノベーションや創造的なブレークスルーのチャンスを逃してしまう可能性もあります。',
                'relation_hint': '同じく慎重で戦略的な人とは、お互いの判断の質を高め合い、リスク管理の重要性を共有できる安定した関係を築けます。直感的でアグレッシブな人とは最初はペースの違いを感じるかもしれませんが、あなたの慎重さと相手の行動力を組み合わせることで、リスク管理と機会獲得のバランスが取れた強力なチームを作れます。チームでは、楽観的な雰囲気に冷静な視点をもたらし、潜在的なリスクを事前に指摘して失敗を防ぐ重要な役割を果たします。戦略的アドバイザーとして、重要な意思決定の場面で信頼される存在です。感情的になりがちなメンバーには、冷静な分析と客観的な視点を提供することでバランスを生み出せます。',
                'growth_tip': '慎重さという強みを活かしながら、「80%の確実性で動く勇気」も身につけましょう。完璧な計画を待つのではなく、十分に良い戦略ができたら実行に移し、行動しながら調整する柔軟性を育てることで、スピード感と質のバランスが向上します。リスク管理と機会活用のバランスを取り、「慎重な中にもチャレンジ精神を持つリーダー」として成長することで、安全性と成長性を両立させる真のリーダーになれます。時には計算されたリスクを取ることで、大きな成果と革新的な価値を生み出すチャンスをつかめます。「失敗しないこと」よりも「失敗から学ぶこと」を恐れない姿勢も、さらなる成長の鍵です。'
            },
            
            'CHJC': {
                'summary': 'オプティマスは、複雑な状況の中から最適な選択肢を見つけ出す「選択のマスター」です。高い判断力と選択力を組み合わせ、様々な可能性を論理的に分析しながら、最も良い道を選び取る能力に優れています。迷いや混乱の中でも冷静に選択肢を整理し、それぞれのメリット・デメリットを明確に見極めます。単に効率を追求するのではなく、「本当に大切なものは何か」を見抜き、長期的な価値と実用性のバランスが取れた最適解を導き出します。複数の選択肢がある状況で真価を発揮し、チームの意思決定をサポートする頼れる存在です。',
                'decision_style': '複数の選択肢を論理的に比較・分析し、「何を優先すべきか」を明確にしてから判断します。感情や一時的な気分に流されず、客観的な基準と長期的な視点で各選択肢を評価します。「この選択は本当に目標達成につながるか」「リスクとリターンのバランスは適切か」「関係者にとって納得できる選択か」を慎重に検討してから決断を下します。複雑な状況ほど冷静さを保ち、情報を整理して本質を見抜く力を発揮します。急いで決めることなく、十分な検討を経た上で確信を持って選択できるまで考え抜きます。',
                'choice_pattern': '「最適性」「バランス」「実現可能性」「長期的価値」を重視した選択を行います。極端な選択肢よりも、複数の要素がバランス良く満たされた「総合的に優れた選択」を好みます。短期的な魅力だけでなく、持続可能性や将来的な展開も考慮し、「今だけでなく、これからも良い選択」を追求します。選択する際は、関係者の納得感や実行の現実性も重要視し、理想と現実のバランスが取れた実現可能な最適解を選びます。冒険よりも計算されたリスクテイクを好み、成功の確率を高める選択を行います。',
                'risk_note': '最適解を求めるあまり、選択に時間がかかりすぎて決断が遅れるリスクがあります。完璧な選択肢を探し続け、「もっと良い選択があるのでは」と迷い、行動のタイミングを逃してしまう可能性があります。また、論理的な分析に頼りすぎて、直感や感情の重要性を軽視する場合もあります。複数の選択肢を比較することに集中しすぎて、「まず行動してみる」という選択肢を見落とすリスクもあります。慎重さが過度になると、小さな失敗を恐れて大きなチャンスを見逃したり、周囲から優柔不断に見られることもあります。',
                'relation_hint': '同じく論理的で慎重な人とは、お互いの判断を尊重し合い、質の高い意思決定ができる安定した関係を築けます。直感的で行動力のある人とは、あなたの慎重さと相手のスピード感が補完し合い、「考えと行動のバランス」が取れた強力なパートナーシップを形成できます。チームでは意思決定のアドバイザーや選択肢の整理役として重宝され、複雑な状況での頼れる相談相手になります。迷いや不安を抱える人に対しては、冷静な分析と明確な選択肢の提示で安心感を与え、前に進む力を与えられます。',
                'growth_tip': '優れた選択力を活かしながら、「80%の確信で動く勇気」も身につけましょう。完璧な選択を待つのではなく、十分に良い選択ができたら行動に移し、実行しながら調整する柔軟性を育てることで、スピードと質のバランスが向上します。また、論理的分析に加えて、直感や感情の声にも耳を傾ける習慣を作ることで、より豊かで人間味のある選択ができるようになります。「選択のマスター」として、複雑な状況で最適解を見つける力を発揮しながら、実行力も高めていくことで、真のリーダーシップを発揮できます。'
            },
            
            # 共鳴軸 (RS)
            'RSAW': {
                'summary': 'ルナは「心の月明かりで人々を照らし、癒しの場を創造する」深い共感力の癒し手です。他者の痛みや喜びを自分のことのように感じ取り、包み込むような温かさで心の支えとなります。表面的な対話ではなく、魂レベルでの深いつながりを重視し、疲れた心に安らぎをもたらす天性の癒し手です。言葉にならない感情や、表に出せない悩みを察知する鋭い感受性を持ち、「ただそばにいてくれるだけで安心する」と言われる存在です。夜空を照らす月のように、暗闇の中でも優しい光で道を示し、傷ついた心を静かに癒します。競争や対立ではなく、共感と思いやりに基づいた関係性を大切にし、すべての人が安心して自分らしくいられる温かい場所を作り出します。',
                'decision_style': '「この選択は誰かを傷つけないか?」「みんなの心が平和になるか?」「本当に必要としている人に届くか?」を最優先に考えて選択します。データや効率よりも、人の心の動きや感情の流れを重視。相手の立場に立って物事を考え、共感的理解に基づいた温かみのある判断を心がけます。決断する前に、関係者全員の気持ちを丁寧に想像し、「誰も悲しまない道はないか」「みんなが幸せになる方法はないか」を探し続けます。時間がかかっても、納得と安心が得られるまで話し合いを重ね、心からの合意を大切にします。論理や効率を優先するよりも、人の心に寄り添うことを選び、「正しいかどうか」よりも「優しいかどうか」を判断の軸とします。',
                'choice_pattern': '「心の安らぎ」「癒し」「共感」「思いやり」を感じられる選択肢に強く心を動かされます。競争や対立を生む選択よりも、協力と調和を育む選択を好みます。短期的な利益よりも、長期的な人間関係の健全さを重視し、「誰もが幸せになれる道」を模索します。弱い立場の人への配慮を欠かさず、包括的で優しい選択を行います。「この選択で誰かが孤独を感じないか」「この選択で誰かの心が軽くなるか」を常に考え、選ぶ基準は「どれだけ多くの人の心を癒せるか」「どれだけ温かい場を作れるか」です。厳しさや効率性よりも、優しさと思いやりを優先し、すべての人が大切にされる選択を追求します。',
                'risk_note': '他者の感情を優先しすぎて、自分のニーズや意見を後回しにしてしまうリスクがあります。また、対立や困難から目を逸らしがちで、必要な厳しい決断を避けてしまう可能性もあります。感情移入しすぎて客観的判断が困難になったり、境界線があいまいになって疲弊することもあります。「NO」と言えずに過度な負担を抱え込み、自分自身が疲れ果ててしまう危険性があります。他者の痛みを背負いすぎて共依存的な関係になったり、助けすぎることで相手の成長機会を奪ってしまうこともあります。優しさが過度になると、必要な変化や成長を妨げるリスクもあります。',
                'relation_hint': '同じく共感力の高い人とは、深い理解と癒しの関係を築けます。論理的で決断力のある人とは補完的な関係を形成し、感情面と実務面のバランスが取れたチームになります。傷ついた人や支援を必要とする人にとって、あなたは貴重な安全基地となります。リーダーシップを取る人の心の支えとしても重要な役割を果たします。チームの中では「心の避難所」として、メンバーが安心して感情を表現できる場を提供し、組織全体の心理的安全性を高める存在になります。あなたがいることで、周囲の人々は心を開き、本音で語り合える環境が生まれます。',
                'growth_tip': '豊かな共感力を活かしながら、「健全な境界線を持つ勇気」を身につけましょう。他者を癒すためには、まず自分自身が健康で安定していることが重要です。時には「愛ある厳しさ」も必要であることを理解し、相手の真の成長を願う心で、必要な時にはNOを言える強さも育てましょう。「自分を大切にすることも、他者を大切にすることと同じくらい重要」だと認識し、セルフケアの時間を確保することで、持続可能な癒しの力を保てます。優しさと強さのバランスを取ることで、真の癒し手として成長できます。'
            },
            
            'RSCV': {
                'summary': 'ミューズは「美しい表現で人々の心を動かし、新しい世界を見せる」芸術的インスピレーターです。言葉、音楽、ビジュアル、動作などあらゆる表現手法を通じて、人々の感情を揺さぶり、インスピレーションを与え、新しい可能性を示すクリエイティブな影響力の持ち主です。ギリシャ神話の芸術の女神のように、創造性と美的センスで人々の心に火をつけ、「こんな世界もあるのか」という驚きと感動を届けます。単なる情報伝達ではなく、心の深いところに響く表現を追求し、人生を豊かにする芸術的体験を創造します。見る人、聞く人、触れる人の心を揺さぶり、忘れられない印象を残し、生き方や価値観を変えるほどのインパクトを与える表現者です。',
                'decision_style': '「この選択は人々の心を動かすか?」「インスピレーションを与えるか?」「新しい世界を見せるか?」を基準に判断します。ロジックや効率性よりも、感情的インパクトや美的価値を重視。人々の心に残り、長く記憶され、人生を変えるような選択を追求します。「どれだけ多くの人が感動するか」「どれだけ美しい体験を創造できるか」「どれだけ新しい視点を提供できるか」が決断の軸となります。実用性や合理性だけで判断せず、「この選択は魂を震わせるか」「芸術として美しいか」を重視し、感性と直感を信じて判断を下します。短期的な成果よりも、長期的に人々の記憶に残り、インスピレーションを与え続ける選択を好みます。',
                'choice_pattern': '「美しさ」「独創性」「表現力」「インスピレーション」を感じさせる選択肢に強く心を動かされます。単なる機能性や実用性だけではなく、「人々の心を豊かにし、新しい世界を創造できるか」を選択基準とします。伝統的で保守的な選択よりも、新しい表現や革新的なアプローチを好みます。「この選択は美しいストーリーを生むか」「この選択は人々に希望やインスピレーションを与えるか」を常に考え、芸術的価値と感情的インパクトを最優先します。一般的な成功よりも、表現としての完成度と独創性を重視し、「誰も見たことのない美しさ」を追求する選択を行います。便利さや効率よりも、心を動かす力を持つ選択を選びます。',
                'risk_note': '美や表現を追求するあまり、実用性や効率性を軽視してしまうリスクがあります。また、独創性を求めすぎて、一般的なニーズや市場の要求からかけ離れてしまう可能性もあります。インスピレーションを重視するあまり、地道な作業や継続性をおろそかにするリスクもあります。芸術性にこだわりすぎて、プロジェクトが完成しなかったり、期限や予算を大幅に超過してしまう危険性もあります。「美しくなければ意味がない」という完璧主義が、行動の遅れや機会損失につながることもあります。また、独自の表現を追求するあまり、協力者や受け手との意思疎通が困難になるリスクもあります。',
                'relation_hint': '同じく芸術的センスや創造性を大切にする人とは、お互いを刺激し合い、素晴らしいコラボレーションを生み出せます。実務的でロジカルな人とは、あなたのビジョンを現実に落とし込む強力なパートナーシップを築けます。あなたの表現に触れた人は、新しい世界を見る目を得て、人生に対する新しい情熱を見つけるでしょう。チームでは、創造性の源泉として、プロジェクトに芸術的な視点と感動的な要素をもたらし、単なる機能的な成果を超えた価値を生み出します。あなたの存在は、周囲の人々の感性を豊かにし、美しいものへの気づきを与えます。',
                'growth_tip': '芸術的センスとインスピレーションを大切にしながら、「持続可能な表現」を意識しましょう。美しいビジョンを現実に変えるための実務スキルやビジネスセンスを身につけ、「美しくて役に立つ」「インスピレーションと実用性が共存する」作品やサービスを創造することで、より多くの人に影響を与えられます。芸術性と実現可能性のバランスを取り、「完璧な表現」を追求しながらも「完成させる力」を育てることで、真に影響力のあるクリエイターになれます。期限や制約の中で最高の表現を生み出すスキルを磨きましょう。'
            },
            
            'RSAB': {
                'summary': 'ボンドは、「人と人との絆こそが最大の力」と信じる結束の造り手です。チームの結束力を高め、協力と信頼に基づいた強い関係性を築き上げる天才です。個々の力を結集してシナジーを生み出し、「1+1=3以上」の成果を実現するコラボレーションのエキスパートです。バラバラだった人々を一つのチームにまとめ上げ、お互いを信頼し支え合う文化を育てることで、誰一人では成し遂げられない大きな成果を実現します。「一人では弱くても、共にいれば強い」という信念のもと、関係性の質を何よりも大切にし、持続可能で温かいコミュニティを作り上げていきます。',
                'decision_style': '「この選択はチームの結束を強めるか?」「みんなで協力できるか?」「相互の信頼を深めるか?」を最重視して判断します。個人の利益よりもチーム全体の利益を優先し、「みんなが勝つ」選択を追求します。一人だけが得をする選択ではなく、全員が恩恵を受けられる道を探り、「誰も置き去りにしない」という姿勢を貫きます。メンバーの意見を幅広く丁寧に収集し、全員が納得でき、チームの一体感が高まる選択を目指します。「この決断は関係性を傷つけないか?」「メンバー同士の信頼を深められるか?」を常に考え、長期的な関係の質を守ることを優先します。',
                'choice_pattern': '「チームワーク」「協力」「相互支援」「信頼関係」を育む選択肢に強く心を動かされます。競争や対立を生む選択よりも、お互いを高め合い、共に成長できる選択を好みます。短期的な成果よりも、長期的な関係性の質を重視し、持続可能な協力関係を築ける選択を行います。「一人で速く行く」よりも「みんなで遠くまで行く」を大切にし、プロセスにおいても全員が参加し、貢献できる機会がある選択肢を選びます。個人の栄光よりもチームの勝利を、競争よりも共創を、独占よりも分かち合いを重視した選択パターンを持っています。「この選択はチームの絆を深めるか」が最終的な判断基準です。',
                'risk_note': 'チームの調和を重視するあまり、必要な対立や建設的な異議を避けてしまうリスクがあります。「波風を立てたくない」という気持ちが強すぎて、問題を先送りにしたり、重要なフィードバックを控えてしまう可能性があります。また、全員の意見を聞こうとして意思決定が遅くなったり、結果として誰にとっても中途半端な曖昧な決断になるリスクもあります。関係性を優先しすぎて、成果や品質、スピードを犠牲にしてしまうこともあります。「みんな仲良く」を求めすぎて、時には必要な厳しい決断や、チームメンバーの成長のための挑戦的なフィードバックができなくなる危険性もあります。',
                'relation_hint': '同じくチームワークを大切にする人とは、素晴らしいシナジーを発揮し、お互いを高め合い、深い信頼に基づいた関係を築けます。個人主義的な人とは最初は価値観の違いを感じるかもしれませんが、時間をかけて信頼関係を丁寧に築くことで、強力なパートナーシップを形成できます。リーダーシップのある人の右腕として、チームの団結力を高め、メンバー間の橋渡しをする重要な役割を果たします。対立を抱えたチームや、バラバラになりかけたグループでは、あなたの存在が人々を再び結びつけ、協力し合える環境を取り戻すきっかけになります。人と人をつなぐ接着剤のような存在として、組織全体の雰囲気と文化を良い方向に導けます。',
                'growth_tip': 'チーム結束という強みを活かしながら、「建設的な対立の価値」も理解しましょう。時には異なる意見のぶつかり合いや健全な議論がチームをより強くすることを認め、「調和と成果のバランス」を取るスキルを身につけることで、より効果的なチームビルダーになれます。「仲良くすること」と「成果を出すこと」は必ずしも矛盾しないことを理解し、時には厳しいフィードバックや難しい決断も、チームの長期的な成長のために必要だと受け入れる勇気を持ちましょう。関係性を大切にしながらも、結果にもコミットする姿勢が、真のチームリーダーへの成長につながります。'
            },
            
            'RSBL': {
                'summary': 'ハーモニーは「全ての音が美しく響き合う世界を創造する」統合調和のマエストロです。異なる個性、能力、意見を持つ人々を美しいシンフォニーのように統合し、個々の特性を活かしながら全体としての大きな調和を実現するオーケストラの指揮者です。一人ひとりの強みや個性を尊重しながら、それらがお互いを高め合い、美しい全体を作り上げるバランスの芸術家です。対立や不協和を解消し、多様性を力に変え、バラバラだったものを調和のとれた統一体へと導きます。「個」を殺さず「全体」を育てる、真の統合力を持つハーモニーの創造者です。',
                'decision_style': '「全体のハーモニーは保たれるか?」「個々の良さを活かしつつ美しい全体を作れるか?」「みんなが輝けるか?」を基準に判断します。対立や競争ではなく、協力と相互尊重による美しい結果を追求。短期的な効率よりも、長期的な調和と持続可能性を重視した判断を行います。一つの声だけを聞くのではなく、すべての関係者の意見や感情を丁寧に収集し、それらをバランスよく統合した決断を目指します。「この決断は全体の調和を乱さないか」「みんなが納得して前に進めるか」「長期的に持続可能な関係性を保てるか」を常に考え、部分最適ではなく全体最適を追求します。',
                'choice_pattern': '「美しい全体像」「相互補完」「持続可能な調和」「みんなが輝く環境」を実現できる選択肢に強く心を動かされます。個々のメリットだけではなく、全体としてのシナジーや美しさを重視。短期的な成果よりも、関係者全員が満足し、長期にわたって継続できる選択を好みます。「この選択は個々の特性を活かせるか」「この選択は全体をより良くするか」「この選択は調和を生むか」を判断基準とし、win-winではなくwin-win-winを目指します。一部が犠牲になる選択よりも、全員が何らかの形で恩恵を受けられる統合的な選択を追求します。多様性を力に変え、違いを対立ではなく補完関係として捉える選択を行います。',
                'risk_note': '理想的な調和を求めすぎて、必要な意思決定や変革を先送りにしてしまうリスクがあります。また、全員の意見を統合しようとして、結果的に曖昧で中間的な決断になってしまう可能性もあります。調和を重視するあまり、特定の個人やグループの特性や強みを平均化してしまうリスクもあります。全体最適を追求しすぎて決断が遅れ、タイミングを逃すこともあります。「誰も傷つけたくない」という思いが強すぎて、必要な変化や厳しいフィードバックを避けてしまい、長期的には組織の成長を阻害する危険性もあります。美しい調和を求めるあまり、健全な対立や建設的な議論を抑え込んでしまうリスクもあります。',
                'relation_hint': '同じく全体最適や調和を大切にする人とは、美しいシンフォニーのようなコラボレーションを実現できます。強い個性や特化した能力を持つ人とは、その特性を最大限に活かしながら全体の中で美しく統合することで、素晴らしいチームを作り上げられます。異なるバックグラウンドや文化を持つ人々を結びつける、真のダイバーシティの体現者です。対立を抱えたチームや、バラバラになりかけた組織では、あなたの統合力が人々を再び調和させ、美しい全体を取り戻すきっかけになります。リーダーとしては、全員の声を聞き、全員を大切にする包括的なリーダーシップを発揮し、組織全体の調和を育てます。',
                'growth_tip': '調和と統合の才能を活かしながら、「時には明確な方向性を示すリーダーシップ」も発揮しましょう。全員の意見を聞くことと、適切なタイミングで決断を下すことのバランスを取り、「美しい調和と効果的な成果」を両立させるスキルを身につけることで、真のハーモニーリーダーになれます。完璧な合意を待つのではなく、80%の調和が取れたら前に進む勇気を持つことで、スピードと質の両立が可能になります。また、健全な対立や建設的な議論も調和の一部であることを理解し、「表面的な平和」ではなく「本質的な調和」を追求しましょう。多様性を統合する力を活かしながら、時には明確な決断を下す強さも育てることが、真の統合的リーダーへの成長につながります。'
            },
            
            # 認識軸 (AW)
            'AWJG': {
                'summary': 'サーチライトは、鋭い観察眼で隠された真実を見抜く「洞察者」です。暗闇の中で一点を照らし出すサーチライトのように、複雑で混沌とした状況の中から本質的な真実を発見する力を持っています。表面的な情報や一般的な説明に簡単には納得せず、「本当にそうなのか？」「裏に何があるのか？」と常に問いかけながら、隠された要因や見落とされがちな重要な手がかりを探り当てます。高い分析力と深い自己認識力を併せ持ち、自分の思考プロセスや偏見さえも客観的に観察しながら真実に迫ります。探偵のように証拠を集め、パズルのピースを組み合わせて全体像を明らかにする能力に長けています。',
                'decision_style': '「表面を見ただけでは分からない何かがある」という直感的な洞察力を頼りに判断します。一見シンプルに見える状況でも、違和感や気づきを大切にし、「なぜこうなっているのか」「見落としている要素はないか」と多角的な観察を続けます。情報を鵜呑みにせず、様々な角度から検証し、矛盾点や隠された要因を見極めてから決断を下します。時間をかけて慎重に分析するため決断は遅く見えるかもしれませんが、その分的確で本質を捉えた判断ができます。表面的な正解ではなく、深層にある真の問題や機会を見つけ出してから行動するため、結果として無駄な動きを避けられます。',
                'choice_pattern': '「なぜこれが重要なのか」「裏に何があるのか」「本当の価値はどこにあるのか」を常に問いかけながら選択します。単純明快に見える選択肢ほど疑いの目を向け、その背後にある意図や隠された代償を探ろうとします。一般的に「良い」とされる選択でも、本当に自分や状況に合っているかを深く掘り下げて検証します。見た目の魅力や他人の推薦だけでは動かず、自分自身の観察と分析を通じて真の価値や意味を見極めてから判断する傾向があります。複雑で一筋縄ではいかない選択肢でも、そこに本質的な価値や真実があると感じれば、勇気を持って選択します。',
                'risk_note': '真実追求に没頭しすぎて、現実的な期限や他の重要事項を見失うリスクがあります。「完璧に理解するまで動けない」状態に陥り、行動のタイミングを逃してしまう可能性があります。また、疑い深くなりすぎて、他者の善意や誠実さまで疑ってしまい、信頼関係を損なう危険性もあります。批判的な視点が強すぎると、周囲の人を委縮させたり、「否定ばかりする人」と誤解されることがあります。真実を見抜く力は素晴らしいですが、それを伝える際の配慮が不足すると、人間関係に摩擦を生じさせるリスクがあります。完璧な答えを求めるあまり、80%の理解で十分な状況でも動けなくなることもあります。',
                'relation_hint': '同じく真実を重視する探究心旺盛な人や、論理的思考を持つ分析タイプとの相性が抜群です。お互いの洞察を共有し合い、より深い理解に到達できます。一方で、行動力があり実行に移すのが得意な人とペアを組むことで、あなたの洞察を実際の成果に変換できる強力なチームワークが生まれます。慎重すぎるあなたに「まず動いてみよう」と背中を押してくれる人は、良きパートナーになります。感情的で直感的な人に対しては、冷静な分析と客観的な視点を提供することで、バランスの取れた判断をサポートできます。あなたの鋭い洞察は、迷いの中にいる人に明確な方向性を示す光となります。',
                'growth_tip': '鋭い洞察力という強みを活かしながら、発見した真実を他者にも理解しやすい形で伝える技術を磨きましょう。専門用語や複雑な説明ではなく、シンプルで共感しやすい言葉で表現する練習をすることで、より多くの人に影響を与えられます。また、「完璧な理解」ではなく「十分な理解」で動き出す勇気を育てることも重要です。80%の確信があれば行動に移し、残りは実践の中で学ぶという柔軟性を身につけましょう。批判的思考と建設的提案のバランスを取り、問題点を指摘するだけでなく解決策も提示することで、真の価値提供者になれます。洞察の深さを保ちながら、適切なタイミングで行動に移す判断力を養うことで、発見者から変革者へと進化できます。'
            },
            
            'AWAB': {
                'summary': 'パノラマは、広い視野で全体像を把握する「俯瞰者」です。鳥の目のように高い視点から状況全体を見渡し、個々の要素がどう連携して大きなシステムを形成しているかを深く理解します。「木を見て森を見ず」の逆で、「森も見て木も見る」バランスの取れた認識能力を持ち、部分と全体の両方を同時に捉えることができます。複雑に絡み合った問題でも、全体の文脈の中で位置づけて包括的な解決策を提示する力に長けています。自分の視点や立ち位置を客観的に認識する力が高く、俯瞰的な理解を実際の行動に移す実行力も備えています。チームの中では「全体を見渡す目」として頼りにされる存在です。',
                'decision_style': '「この決断は全体のバランスにどう影響するか」「見落としている重要な要素はないか」「長期的な波及効果は何か」を常に考慮しながら判断します。目の前の問題だけを見て飛びつくのではなく、システム全体の調和と持続可能性を重視した決断を下します。多面的な視点から問題を検討し、関係する全ての人や要因を視野に入れた上で、包括的かつ戦略的な判断を行います。「点」ではなく「面」で、「今」ではなく「流れ」で物事を捉え、短期的な利益と長期的な価値のバランスを見極めます。様々な情報を統合して全体像を描き出してから決断するため、慎重ですが確信を持った判断ができます。',
                'choice_pattern': '「この選択が全体システムに与える影響は何か」「関係する全ての要素を考慮したか」という包括的な視点で選択を行います。部分的な最適化に陥らず、システム全体の調和と成長を促進する選択肢を好みます。複数の選択肢を比較する際は、それぞれが全体にもたらす波及効果を想像し、直接的な結果だけでなく間接的な影響まで考慮します。短期的な成果よりも、長期的に持続可能で、様々な要素がうまく連携して機能する選択を重視します。「この選択は全体の中でどういう位置づけか」「他の要素とどう相互作用するか」を常に問いかけながら、最適なバランスポイントを探します。',
                'risk_note': '全体を意識しすぎて、あらゆる要素を考慮しようとするあまり決断に時間がかかりすぎるリスクがあります。包括的な視点を持つことは強みですが、時には重要な細部への配慮が不足し、「大きな絵は描けるが実行の詳細が詰められていない」状態になる可能性があります。また、視野が広すぎて焦点が散漫になり、「何でも見えるが何も深く理解していない」という浅い理解に陥るリスクもあります。理想的な全体最適を追求するあまり、現実的な制約や実行可能性を軽視し、絵に描いた餅になってしまう危険性もあります。完璧なバランスを求めすぎて、行動のタイミングを逃すこともあります。',
                'relation_hint': '同じく全体を見渡す思考を持つ戦略的な人や、システム全体を理解できる人との相性が抜群です。お互いの俯瞰的な視点を共有し合い、より大きく深い理解を構築できます。また、細部に強い専門家や実務に長けた実行力のある人とペアを組むことで、あなたの俯瞰的なビジョンと相手の具体的な実行力が補完し合い、理想と現実のバランスが取れた強力なチームを形成できます。分析的で論理的な人とは、全体像を共に描きながら体系的に問題を解決していけます。感情的で直感的な人に対しては、冷静な全体観を提供することで安心感と方向性を与えられます。',
                'growth_tip': '俯瞰的な視点という強みを保ちながら、重要な局面では適切に焦点を絞り込む技術を身につけましょう。「全体を見る」ことと「重要な部分に集中する」ことを状況に応じて切り替える柔軟性を育てることで、戦略性と実行力を両立できます。また、包括的な理解を段階的に実行可能な計画に落とし込むスキルを磨くことで、ビジョンを現実の成果に変換できるようになります。「鳥の目」だけでなく、時には「虫の目」や「魚の目」も使い分けて、多層的な理解を深めていきましょう。全体最適という理想を保ちながらも、「まず80%で始めて調整していく」実践的アプローチも取り入れることで、より多くの成果を生み出せます。'
            },
            
            'AWRN': {
                'summary': 'レーダーは、周囲の微細な変化を敏感に感じ取る「変化の番人」です。空気の変化、人の感情の動き、環境のわずかな異変など、他の人が見逃してしまうような小さな兆候を瞬時にキャッチする天性の感知能力を持っています。「何かがいつもと違う」という繊細な違和感を察知し、重要な変化の前兆を早期に発見します。レーダーのように周囲を常にスキャンし、危険や機会の芽を見逃さない警戒システムとして機能します。周りの人々や環境との共鳴力が高く、場の雰囲気や人の心の動きを深く理解する力にも優れています。変化の波を読み取り、適切なタイミングで行動する直感的な判断力を発揮し、チームの早期警戒システムとして頼られる存在です。',
                'decision_style': '「いつもと何かが違う」「微妙な空気の変化を感じる」という繊細な感受性を判断の重要な材料とします。データや論理だけでなく、肌で感じる変化の兆候や直感的なサインを大切にし、タイミングを見極めて決断を下します。「今がその時だ」という瞬間を本能的に感じ取り、変化の波に乗るべきタイミングと待つべきタイミングを直感で判断します。感じ取った微細な信号を総合的に分析し、「この変化は何を意味するのか」「どこに向かっているのか」を読み解いてから行動に移します。急激な変化よりも、じわじわと進行する変化にいち早く気づき、先手を打った対応ができます。',
                'choice_pattern': '「この変化の流れに乗るべきか」「今は待つべき時か」を敏感に感じ取りながら選択します。変化の波のリズムを読み取り、無理に流れに逆らうのではなく、自然なタイミングで動く選択を好みます。「場の空気に合っているか」「周囲の人々の状態は整っているか」「環境は味方してくれるか」を重要な判断基準とし、調和的で自然な流れに沿った選択を行います。急激な変化よりも段階的な変化を好み、周囲との共鳴を保ちながら前進できる道を選びます。危険や問題の予兆を感じたら、早めに回避する選択を取る慎重さも持ち合わせています。',
                'risk_note': '変化や刺激に敏感すぎて、些細なことにも過度に反応してしまうリスクがあります。常に周囲をモニタリングする警戒状態が続くため、精神的に疲弊しやすく、休息が不足する可能性があります。また、変化を恐れるあまり保守的になりすぎたり、感じ取った兆候を言葉で説明するのが難しく、他者に理解されずに孤立するリスクもあります。「なんとなく感じる」という直感を過度に信じすぎて、論理的な検証を怠る場合もあります。ネガティブな変化の兆候ばかりに注目して、ポジティブな機会を見逃すこともあります。',
                'relation_hint': '同じく感受性が高く細やかな変化に敏感な人とは、お互いの感覚を尊重し合い、深い共感で結ばれた関係を築けます。冷静で論理的な判断力を持つ人とペアを組むことで、あなたの敏感な感知力と相手の分析力が補完し合い、早期発見と的確な対応を兼ね備えた強力なチームになります。チームでは「早期警戒システム」「空気を読む達人」として、危機回避や機会発見に大きく貢献します。感じ取った変化を信じてもらえる信頼関係を築くことが、あなたの能力を最大限に活かす鍵となります。',
                'growth_tip': '微細な変化を感知する貴重な能力を活かしながら、「感じたことを言葉で伝える技術」を磨きましょう。直感的に感じ取った変化を、具体的な事例や観察事実と結びつけて説明する習慣を作ることで、周囲の理解と信頼を得やすくなります。また、重要度に応じて反応の強さを調整するスキルを身につけ、「すべての変化に同じレベルで反応しない」という選択的注意力を育てることで、疲弊を防ぎながら本当に重要な変化に集中できます。定期的な休息とリフレッシュを意識的に取り入れ、感知センサーのメンテナンスを大切にしましょう。'
            },
            
            # バランス型 (BL)
            'BLNC': {
                'summary': 'センターは、すべての軸において均等なバランスを保つ「調和の中心」です。極端に偏ることなく、状況に応じて柔軟に対応できる安定した内面構造を持っています。どの方向にも過度に傾かない中庸の美を体現し、様々な人や状況と自然に調和できる適応力があります。「バランスこそが最大の強み」という信念のもと、安定した判断と穏やかな存在感でチームの調整役として信頼されます。起動力も判断力も選択力も共鳴力も自覚力も、すべてが中程度で安定しているため、どんな局面でも過不足なく対応できる万能型の存在です。激しい変化や極端な状況に強く、周囲が動揺する中でも冷静さを保ち、全体を見渡しながら最適な調整を行う力を持っています。',
                'decision_style': '「極端な判断は避け、全体最適を追求する」という信念のもと、複数の要素をバランスよく考慮した中庸の判断を行います。一つの視点に固執せず、様々な角度から状況を俯瞰し、最もバランスの取れた解決策を見出します。急いで決めることなく、関係者の意見を丁寧に聞き、全体の調和を保つ決断を心がけます。データと直感、論理と感情、短期と長期など、対立しがちな要素を巧みに統合し、誰もが納得できる着地点を見出す能力に長けています。極端な状況でも冷静さを失わず、客観的な視点から最善の判断を下すことができます。',
                'choice_pattern': '安定性と調和を重視し、極端なリスクや急激な変化を伴う選択は慎重に避ける傾向があります。「みんなにとって無理のない選択」「持続可能なバランスを保てる選択」「長期的に見て安定した選択」を好み、短期的な利益よりも長期的な安定を優先します。革新性よりも着実な改善を重視し、段階的なアプローチで確実に前進することを選びます。選択の際は「この選択で誰かが極端に不利にならないか」「全体のバランスが崩れないか」を常に考慮し、関係者全員が受け入れられる選択肢を模索します。リスクとリターンのバランスを慎重に見極め、安全マージンを確保した堅実な選択を行います。',
                'risk_note': 'バランスを重視するあまり、時に必要な大胆な決断を避けてしまうリスクがあります。また、中庸を保とうとするあまり、自分らしい個性や突出した強みを発揮しにくい面もあります。周囲から「どっちつかず」「優柔不断」と見られることもあるかもしれません。すべての要素を均等に扱おうとするため、優先順位をつけることが苦手で、決断に時間がかかることがあります。また、極端な意見や革新的なアイデアを無意識に避けてしまい、ブレークスルーの機会を逃す可能性もあります。安定を求めすぎて、必要な変化やリスクテイクを躊躇してしまうことも注意が必要です。',
                'relation_hint': 'どんなタイプの人とも比較的うまく調和でき、異なるタイプ間の橋渡し役として重宝されます。極端な特性を持つ人に対しては、バランスの視点を提供することで良い影響を与え、チーム全体の安定化に貢献します。チームの調整役、まとめ役として自然に信頼される存在です。対立が生じた際には中立的な立場から調停を行い、双方が納得できる解決策を見出す能力があります。ただし、強い個性やビジョンを持つリーダータイプの人とは、時に物足りなさを感じさせてしまうこともあるため、自分の意見をしっかり持ちながらも調整力を発揮することが大切です。',
                'growth_tip': '安定したバランス感覚を活かしながら、時には意図的に一つの軸を強化してみることで、新しい可能性が開けます。「バランスを保ちながらも成長する」という視点で、少しずつ自分の得意分野や強みを磨いていきましょう。月に一度は「今月は判断力を重点的に使う」など、特定の軸にフォーカスする実験を行うことで、潜在能力を発見できます。また、時には敢えて極端な選択をしてみる勇気を持つことで、自分の限界を広げ、より豊かなバランス感覚を身につけることができます。安定は素晴らしい強みですが、成長のためには適度な挑戦も必要です。'
            },
            
            'CMPL': {
                'summary': 'シナジーは、複数の強みを組み合わせて相乗効果を生み出す「統合者」です。一つの突出した能力よりも、複数の能力を有機的に結びつけることで独自の価値を創造します。「1+1を3にする」発想で、異なる要素を統合し、予想以上の成果を生み出す才能があります。多面的な視野と統合力で、複雑な課題に対しても総合的なアプローチで解決策を見出します。起動力・判断力・選択力・共鳴力がすべて中程度以上で活性化しており、これらを巧みに組み合わせることで、単一の能力では達成できない複合的な成果を実現します。異なる分野の知識やスキルを橋渡しする能力に優れ、チームやプロジェクトに独自の付加価値をもたらす存在です。',
                'decision_style': '「単一の視点では見えないものがある」という信念のもと、複数の視点や要素を統合して判断します。単一の基準ではなく、様々な角度からの分析を組み合わせ、より豊かで多面的な決断を行います。「これとこれを組み合わせたらどうなるか」「この要素とあの要素を掛け合わせたら新しい価値が生まれるのでは」という発想で、創造的な解決策を見出します。論理的分析と直感的洞察、データと経験、理論と実践を統合し、より包括的で実効性の高い判断を追求します。複数の選択肢のメリットを組み合わせた「第三の道」を見出すことを得意とします。',
                'choice_pattern': '「相乗効果が期待できる選択」「複数の目標を同時に達成できる選択」「異なる価値を統合できる選択」を強く好みます。一石二鳥、三鳥を狙える選択肢に強く惹かれ、単一の成果よりも複合的な価値を生み出す道を選びます。効率性と効果性の両立を重視し、リソースを最大限に活用する選択を追求します。「この選択は他の目標達成にも貢献するか」「複数の課題を同時に解決できるか」を常に考慮し、波及効果の大きい選択を優先します。異なる分野やスキルを組み合わせることで生まれる新しい可能性に敏感で、従来の枠にとらわれない統合的な選択を行います。',
                'risk_note': '複数のことを同時に追求するあまり、一つ一つの完成度が中途半端になるリスクがあります。また、統合を重視しすぎて、シンプルで直接的な解決策を見逃したり、過度に複雑なアプローチを取ってしまうこともあります。周囲から「欲張りすぎ」「複雑に考えすぎ」と見られることもあるかもしれません。すべてを統合しようとして優先順位が曖昧になり、最も重要なことに集中できなくなるリスクもあります。また、異なる要素を無理に組み合わせようとして、不自然な結果になってしまう可能性にも注意が必要です。時には「シンプルが最善」という判断も必要です。',
                'relation_hint': '異なるスキルや視点を持つ人々を結びつけ、チーム全体のシナジーを高める触媒的な役割を担えます。専門家同士をつなぐコーディネーターとして活躍でき、多様性を活かしたチームづくりに大きく貢献します。異なるバックグラウンドを持つメンバー間の共通言語を見つけ、協働を促進する能力があります。プロジェクトマネージャーやプロデューサー的な役割で真価を発揮し、様々なリソースを最適に組み合わせて成果を最大化します。ただし、専門特化型の人からは「広く浅い」と見られることもあるため、各分野への敬意を忘れずに協力関係を築くことが大切です。',
                'growth_tip': '統合力を活かしながらも、時には一つのことに深く集中する時間も意識的に設けましょう。「広く浅く」と「狭く深く」を状況に応じて使い分けることで、統合の質がさらに高まります。月に一度は特定の分野やスキルに没頭する「深掘り期間」を設けることで、統合する素材としての専門性が磨かれます。また、統合の結果をシンプルに説明する練習をすることで、複雑な思考を分かりやすく伝える力が向上します。「足し算」だけでなく「引き算」の統合も学び、本当に価値ある組み合わせを見極める目を養いましょう。'
            },
            
            'ADPT': {
                'summary': 'カメレオンは、状況に応じて柔軟に対応する「適応者」です。固定的なスタイルを持たず、環境や相手に合わせて最適な形に変化する能力に優れています。「変化こそが生存の鍵」という信念のもと、どんな状況でも柔軟に対応し、困難を乗り越える適応力を発揮します。変化の多い環境で真価を発揮し、不確実性の中でも安定した成果を出せます。起動力と判断力は控えめながら、選択力と共鳴力が活性化しており、状況を読み取って最適な対応を選び取る能力に長けています。予測困難な環境、多様なステークホルダーが関わるプロジェクト、変化の激しい業界など、固定的なアプローチが通用しない場面で真価を発揮する、現代社会に最も適応した存在と言えます。',
                'decision_style': '「最善の判断は状況によって変わる」という信念のもと、状況を注意深く読み取り、その時々に最も適した判断を行います。固定的なルールや方法論に縛られず、環境の変化に応じて柔軟にアプローチを変えます。「今、この状況で何が最善か」「この相手には何が響くか」「この文脈では何が求められているか」を常に問い続ける適応的な判断スタイルです。過去の成功パターンに固執せず、新しい情報や変化した条件を素早く取り入れて判断を更新する柔軟性があります。複数のシナリオを想定し、状況の変化に応じて切り替える準備を常に持っています。',
                'choice_pattern': '「柔軟性を保てる選択」「後から軌道修正できる選択」「複数の可能性を残せる選択」を強く好みます。取り返しのつかない決定よりも、状況に応じて調整可能な選択肢を選ぶ傾向があります。変化に対応できる余地を残しておくことを最重視し、オプションを広げておくことに価値を見出します。「この選択をしても、状況が変わったら別の道に切り替えられるか」「リスクが顕在化した時に撤退できるか」を常に考慮し、可逆性の高い選択を優先します。一方で、チャンスを逃さないために、適切なタイミングでは思い切った決断も行える柔軟さを持っています。',
                'risk_note': '柔軟性を重視するあまり、一貫性や軸がないように見えるリスクがあります。また、周囲に合わせすぎて自分らしさを見失ったり、「日和見主義」「八方美人」と誤解されることもあります。信念や価値観が見えにくいため、リーダーシップを発揮する場面では信頼を得にくい面があります。変化に対応することに注力するあまり、自ら変化を起こす主体性が弱くなる傾向もあります。また、すべての状況に適応しようとして疲弊したり、「本当の自分」を見失う危険性にも注意が必要です。芯となる価値観を持ちながら適応することが重要です。',
                'relation_hint': '様々なタイプの人と柔軟に関係を築け、異なる文化やバックグラウンドを持つ人々との協働に強みを発揮します。チームの潤滑油として、メンバー間の橋渡しや調整役を自然に担えます。コミュニケーションスタイルを相手に合わせて変えられるため、幅広い人脈を構築できます。グローバルな環境、多様性の高いチーム、変化の激しいプロジェクトで特に重宝される存在です。ただし、強い個性やビジョンを持つリーダータイプの人からは「主体性がない」と見られることもあるため、適応しながらも自分の意見をしっかり持ち、適切なタイミングで表明することが大切です。',
                'growth_tip': '柔軟な適応力を保ちながらも、「自分にとって絶対に譲れない価値観」を明確にしましょう。すべてを適応させる必要はなく、核となる信念や原則を持つことで、より信頼される存在になれます。「何に適応し、何に適応しないか」という選択基準を持つことが重要です。また、受動的に状況に合わせるだけでなく、時には自ら変化を起こす側に回る経験を積むことで、適応力がさらに磨かれます。変化に対応しながらも成長し続ける姿勢を大切にし、適応の中で自分らしさを見つけていきましょう。定期的に「今の自分は本当の自分か」を振り返る時間を持つことも大切です。'
            }
        }
        
        return characteristics.get(type_code, {
            'summary': 'この型の詳細情報は準備中です。',
            'decision_style': 'この型の意思決定スタイルについては準備中です。',
            'choice_pattern': 'この型の選択パターンについては準備中です。',
            'risk_note': 'この型のリスクと注意点については準備中です。',
            'relation_hint': 'この型の相性・関係性のヒントについては準備中です。',
            'growth_tip': 'この型の成長のヒントについては準備中です。'
        })
    
    def _generate_interpretation_prompt(self, unique_code: str, type_info: Dict, axes: Dict[str, float]) -> str:
        """AI解釈用高度プロンプト生成 - Lambda calculus style"""
        
        # 軸の数値化と関数定義
        axis_funcs = []
        for axis_name, value in axes.items():
            level = "高" if value > config.axis_high_threshold else "中" if value > config.axis_medium_threshold else "低"
            axis_funcs.append(f"λ{axis_name[0]}.({value:.3f}, '{level}', '{self.axis_definitions[axis_name]['essence']}')")
        
        # Lambda calculus style 構造化プロンプト
        prompt = f"""
STRUCT CODE: {unique_code}

∀x ∈ PERSONALITY_ANALYSIS: λSTRUCT_CODE.λTYPE_INFO.λAXIS_SYSTEM.
(
  TYPE_ESSENCE := {type_info['name']} ∩ {type_info['archetype']} ∩ {type_info['mission']}
  
  AXIS_FUNCTIONS := {{
    {' ∩ '.join(axis_funcs)}
  }}
  
  CORE_PATTERN := {type_info['core_pattern']}
  
  DEEP_ANALYSIS := λpsychology.λchallenges.λgrowth_potential.
  (
    LAYER_1_SURFACE := 表面的な行動パターンと意識的選択
    LAYER_2_SUBCONSCIOUS := 無意識的な動機と内在的ドライバー  
    LAYER_3_ARCHETYPAL := 原型的パターンと魂レベルの指向
    LAYER_4_PREDICTIVE := 3ヶ月後の確率的成長ベクトル
    
    SYNTHESIS := LAYER_1 ⊗ LAYER_2 ⊗ LAYER_3 ⊗ LAYER_4
    
    OUTPUT := {{
      深層心理分析: LAYER_2 ∩ LAYER_3の交差点における本質的動機パターン,
      現在の課題: AXIS_FUNCTIONS から導出される最優先解決領域,
      成長可能性: PREDICTIVE_VECTOR(3months) における最高確率シナリオ,
      実践的提案: SYNTHESIS から抽出される具体的行動指針
    }}
  )
)

実行: DEEP_ANALYSIS(
  psychology := STRUCT_CODE.psychometric_mapping(),
  challenges := AXIS_SYSTEM.identify_growth_bottlenecks(),
  growth_potential := TYPE_ESSENCE.project_evolution_trajectory(timeline=90days)
)

この個人のSTRUCT CODEに基づき、Lambda calculus的推論により以下を超高精度で分析してください：

1. 深層心理構造の解析（無意識レベルでの動機と恐れ）
2. 現在直面している最も重要な課題（具体的かつ実践的に）
3. 3ヶ月以内の成長可能性（確率的予測含む）
4. 実行可能な成長戦略（段階的アプローチ）

注意：表面的な一般論ではなく、STRUCT CODE数値の精密な解析に基づいた個別最適化された洞察を提供してください。
"""
        return prompt
    
    # === 公開メソッド ===
    
    def get_questions(self) -> List[QuestionResponse]:
        """質問リストを取得"""
        questions = []
        for q_id, q_data in self.questions.items():
            choices = {}
            for choice_key, choice_data in q_data.get('choices', {}).items():
                choices[choice_key] = choice_data.get('text', '')
            
            questions.append(QuestionResponse(
                id=q_id,
                axis=q_data.get('axis', ''),
                question=q_data.get('question', ''),
                choices=choices
            ))
        
        return questions
    
    def get_type_detail(self, type_code: str) -> Optional[TypeDetail]:
        """タイプ詳細を取得"""
        if type_code in self.struct_types:
            type_info = self.struct_types[type_code]
            detailed_info = self._get_detailed_characteristics(type_code)
            return TypeDetail(
                code=type_code,
                label=type_info['name'],
                summary=detailed_info['summary'],
                decision_style=detailed_info['decision_style'],
                choice_pattern=detailed_info['choice_pattern'],
                risk_note=detailed_info['risk_note'],
                relation_hint=detailed_info['relation_hint'],
                growth_tip=detailed_info['growth_tip'],
                vector=[0.5] * 5,
                character_icon=None
            )
        return None
    
    def get_all_types(self) -> List[Dict[str, Any]]:
        """全タイプの基本情報を取得"""
        types = []
        for type_code, info in self.struct_types.items():
            types.append({
                'code': type_code,
                'name': info['name'],
                'archetype': info['archetype'],
                'axis_signature': info['axis_signature'],
                'mission': info['mission']
            })
        return types

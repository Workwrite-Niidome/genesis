"""
STRUCT CODE Logging Configuration
包括的なログ設定とエラーハンドリング
"""

import logging
import sys
from typing import Optional
from datetime import datetime
from pathlib import Path
import traceback
import functools

from ..config.struct_config import config

# ログフォーマッター
class StructCodeFormatter(logging.Formatter):
    """STRUCT CODE専用フォーマッター"""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def format(self, record):
        # 診断コンテキストがある場合は追加
        if hasattr(record, 'struct_code'):
            record.message = f"[{record.struct_code}] {record.getMessage()}"
        elif hasattr(record, 'user_id'):
            record.message = f"[User:{record.user_id}] {record.getMessage()}"
        else:
            record.message = record.getMessage()
        
        return super().format(record)

# ログ設定
def setup_logging():
    """ログ設定の初期化"""
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(StructCodeFormatter())
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー（プロダクション用）
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"struct_code_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructCodeFormatter())
        root_logger.addHandler(file_handler)
        
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
    
    # アプリケーション専用ログ
    app_logger = logging.getLogger("struct_code")
    app_logger.info(f"Logging initialized - Level: {config.log_level}")
    
    return app_logger

# グローバルロガー
logger = setup_logging()

class StructCodeError(Exception):
    """STRUCT CODE基底例外クラス"""
    
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        self.message = message
        self.error_code = error_code or "STRUCT_UNKNOWN"
        self.context = context or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)

class AstrologicalCalculationError(StructCodeError):
    """占星術計算エラー"""
    
    def __init__(self, message: str, planet: str = None, context: dict = None):
        self.planet = planet
        error_code = f"ASTRO_{planet.upper()}" if planet else "ASTRO_GENERAL"
        super().__init__(message, error_code, context)

class TypeDeterminationError(StructCodeError):
    """タイプ決定エラー"""
    
    def __init__(self, message: str, axes: dict = None, context: dict = None):
        self.axes = axes
        context = context or {}
        if axes:
            context['axes'] = axes
        super().__init__(message, "TYPE_DETERMINATION", context)

class ConfigurationError(StructCodeError):
    """設定エラー"""
    
    def __init__(self, message: str, config_key: str = None, context: dict = None):
        self.config_key = config_key
        error_code = f"CONFIG_{config_key.upper()}" if config_key else "CONFIG_GENERAL"
        super().__init__(message, error_code, context)

class DataValidationError(StructCodeError):
    """データ検証エラー"""
    
    def __init__(self, message: str, field: str = None, value=None, context: dict = None):
        self.field = field
        self.value = value
        context = context or {}
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = str(value)
        super().__init__(message, "DATA_VALIDATION", context)

def log_exception(logger_instance: logging.Logger = None):
    """例外ログデコレーター"""
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            log = logger_instance or logger
            try:
                return await func(*args, **kwargs)
            except StructCodeError as e:
                log.error(
                    f"STRUCT CODE Error in {func.__name__}: {e.message}",
                    extra={
                        'error_code': e.error_code,
                        'context': e.context,
                        'function': func.__name__
                    }
                )
                raise
            except Exception as e:
                log.error(
                    f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}",
                    extra={'function': func.__name__}
                )
                raise StructCodeError(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    "UNEXPECTED_ERROR",
                    {'original_error': str(e), 'function': func.__name__}
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            log = logger_instance or logger
            try:
                return func(*args, **kwargs)
            except StructCodeError as e:
                log.error(
                    f"STRUCT CODE Error in {func.__name__}: {e.message}",
                    extra={
                        'error_code': e.error_code,
                        'context': e.context,
                        'function': func.__name__
                    }
                )
                raise
            except Exception as e:
                log.error(
                    f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}",
                    extra={'function': func.__name__}
                )
                raise StructCodeError(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    "UNEXPECTED_ERROR",
                    {'original_error': str(e), 'function': func.__name__}
                )
        
        # 関数がコルーチンかどうかで分岐
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def log_diagnosis_context(struct_code: str = None, user_id: str = None):
    """診断コンテキストをログに追加するデコレーター"""
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # コンテキスト情報をロガーに追加
            extra = {}
            if struct_code:
                extra['struct_code'] = struct_code
            if user_id:
                extra['user_id'] = user_id
            
            # ロガーにコンテキストを設定
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                for key, value in extra.items():
                    setattr(record, key, value)
                return record
            
            logging.setLogRecordFactory(record_factory)
            
            try:
                return await func(*args, **kwargs)
            finally:
                logging.setLogRecordFactory(old_factory)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同期版の実装
            extra = {}
            if struct_code:
                extra['struct_code'] = struct_code
            if user_id:
                extra['user_id'] = user_id
            
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                for key, value in extra.items():
                    setattr(record, key, value)
                return record
            
            logging.setLogRecordFactory(record_factory)
            
            try:
                return func(*args, **kwargs)
            finally:
                logging.setLogRecordFactory(old_factory)
        
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def log_performance(threshold_seconds: float = 1.0):
    """パフォーマンスログデコレーター"""
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now()
            result = await func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            if duration > threshold_seconds:
                logger.warning(
                    f"Slow operation: {func.__name__} took {duration:.2f}s",
                    extra={'function': func.__name__, 'duration': duration}
                )
            else:
                logger.debug(
                    f"Operation completed: {func.__name__} in {duration:.3f}s",
                    extra={'function': func.__name__, 'duration': duration}
                )
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now()
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            if duration > threshold_seconds:
                logger.warning(
                    f"Slow operation: {func.__name__} took {duration:.2f}s",
                    extra={'function': func.__name__, 'duration': duration}
                )
            else:
                logger.debug(
                    f"Operation completed: {func.__name__} in {duration:.3f}s",
                    extra={'function': func.__name__, 'duration': duration}
                )
            
            return result
        
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# ヘルパー関数
def log_system_info():
    """システム情報をログに記録"""
    logger.info("=== STRUCT CODE Ultimate System Info ===")
    logger.info(f"App: {config.app_name} v{config.app_version}")
    logger.info(f"Debug Mode: {config.debug_mode}")
    logger.info(f"Data Path: {config.data_path}")
    logger.info(f"Astronomy Weight: {config.weight_astronomy}")
    logger.info(f"Questionnaire Weight: {config.weight_questionnaire}")
    logger.info("=========================================")

def log_diagnosis_start(birth_date: str, birth_location: str, num_answers: int):
    """診断開始ログ"""
    logger.info(
        f"Starting diagnosis for {birth_date} at {birth_location} with {num_answers} answers",
        extra={
            'birth_date': birth_date,
            'birth_location': birth_location,
            'num_answers': num_answers
        }
    )

def log_diagnosis_complete(struct_code: str, struct_type: str, confidence: float):
    """診断完了ログ"""
    logger.info(
        f"Diagnosis completed: {struct_type} ({struct_code}) with confidence {confidence:.3f}",
        extra={
            'struct_code': struct_code,
            'struct_type': struct_type,
            'confidence': confidence
        }
    )
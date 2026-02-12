"""
STRUCT CODE Service — Type diagnosis, consultation, and data access.

Provides:
- Local JSON data access (types, questions) with bilingual support (ja/en)
- STRUCT CODE API client (diagnosis via Docker container)
- Claude API consultation (Dify replacement)
- Random answer generation for AI agents
"""
import json
import logging
import math
import os
import random
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data" / "struct_code"

# Cached data keyed by language
_types_cache: dict[str, dict] = {}
_questions_cache: dict[str, dict] = {}


def _load_types(lang: str = "ja") -> dict:
    if lang not in _types_cache:
        suffix = "_en" if lang == "en" else ""
        path = DATA_DIR / f"comprehensive_types{suffix}.json"
        if not path.exists():
            # Fallback to Japanese if translation file missing
            path = DATA_DIR / "comprehensive_types.json"
        with open(path, "r", encoding="utf-8") as f:
            _types_cache[lang] = json.load(f)
    return _types_cache[lang]


def _load_questions(lang: str = "ja") -> dict:
    if lang not in _questions_cache:
        suffix = "_en" if lang == "en" else ""
        path = DATA_DIR / f"question_full_map{suffix}.json"
        if not path.exists():
            path = DATA_DIR / "question_full_map.json"
        with open(path, "r", encoding="utf-8") as f:
            _questions_cache[lang] = json.load(f)
    return _questions_cache[lang]


# ═══════════════════════════════════════════════════════════════════════════
# DATA ACCESS (local JSON)
# ═══════════════════════════════════════════════════════════════════════════

def get_questions(lang: str = "ja") -> list[dict]:
    """Return all 25 questions formatted for frontend."""
    questions = _load_questions(lang)
    result = []
    for qid, qdata in questions.items():
        choices = {}
        for choice_key, choice_val in qdata.get("choices", {}).items():
            choices[choice_key] = {
                "text": choice_val["text"],
            }
        result.append({
            "id": qid,
            "axis": qdata["axis"],
            "question": qdata["question"],
            "choices": choices,
        })
    return result


def get_all_types(lang: str = "ja") -> list[dict]:
    """Return summary of all 24 types."""
    types = _load_types(lang)
    result = []
    for code, info in types.items():
        result.append({
            "code": code,
            "name": info.get("name", ""),
            "archetype": info.get("archetype", ""),
        })
    return result


def get_type_info(type_code: str, lang: str = "ja") -> dict | None:
    """Get full type details by code."""
    types = _load_types(lang)
    info = types.get(type_code)
    if not info:
        return None
    return {
        "code": type_code,
        "name": info.get("name", ""),
        "archetype": info.get("archetype", ""),
        "description": info.get("description", ""),
        "decision_making_style": info.get("decision_making_style", ""),
        "choice_pattern": info.get("choice_pattern", ""),
        "blindspot": info.get("blindspot", ""),
        "interpersonal_dynamics": info.get("interpersonal_dynamics", ""),
        "growth_path": info.get("growth_path", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════
# STRUCT CODE API CLIENT (Docker container)
# ═══════════════════════════════════════════════════════════════════════════

async def diagnose(
    birth_date: str,
    birth_location: str,
    answers: list[dict],
) -> dict | None:
    """Call STRUCT CODE Dynamic API for diagnosis.

    Uses /api/v2/dynamic/diagnosis which returns natal/current structures,
    design gap, axis states, and temporal data.
    No fallback — returns None on failure so caller can raise proper error.

    Returns:
        API response dict or None on failure.
    """
    url = f"{settings.struct_code_url}/api/v2/dynamic/diagnosis"
    payload = {
        "birth_date": birth_date,
        "birth_location": birth_location,
        "answers": answers,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                data["_api_version"] = "dynamic"
                return data

            logger.error(f"STRUCT CODE API error: {response.status_code} — {response.text[:500]}")
            return None

    except Exception as e:
        logger.error(f"STRUCT CODE API unreachable: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# AI AGENT: Random answer generation
# ═══════════════════════════════════════════════════════════════════════════

def generate_random_answers(personality_axes: dict | None = None) -> list[dict]:
    """Generate 25 random answers, biased by personality axes if provided.

    personality_axes: {
        "order_vs_freedom": 0.7,
        "harmony_vs_conflict": 0.3,
        ...
    }
    """
    questions = _load_questions()
    answers = []

    # Axis mapping: personality axis name -> question axis name -> bias direction
    # Higher personality value = higher vector index preference
    axis_map = {
        "order_vs_freedom": "起動軸",
        "harmony_vs_conflict": "判断軸",
        "tradition_vs_change": "選択軸",
        "individual_vs_collective": "共鳴軸",
        "pragmatic_vs_idealistic": "自覚軸",
    }

    for qid, qdata in questions.items():
        choices = list(qdata.get("choices", {}).keys())
        if not choices:
            continue

        if personality_axes:
            # Find the vector index this question's axis corresponds to
            q_axis = qdata.get("axis", "")
            axis_index = None
            for pkey, qaxis_name in axis_map.items():
                if qaxis_name == q_axis:
                    axis_index = list(axis_map.keys()).index(pkey)
                    personality_val = personality_axes.get(pkey, 0.5)
                    break

            if axis_index is not None:
                # Weight choices by how their vector aligns with personality
                weights = []
                for c in choices:
                    vec = qdata["choices"][c].get("vector", [0.5] * 5)
                    # Higher personality_val -> prefer higher vector values at axis_index
                    alignment = 1.0 + (vec[axis_index] - 0.5) * (personality_val - 0.5) * 4
                    weights.append(max(0.1, alignment))

                choice = random.choices(choices, weights=weights)[0]
            else:
                choice = random.choice(choices)
        else:
            choice = random.choice(choices)

        answers.append({"question_id": qid, "choice": choice})

    return answers


# ═══════════════════════════════════════════════════════════════════════════
# LOCAL FALLBACK: cosine similarity type classification
# ═══════════════════════════════════════════════════════════════════════════

# Axis signatures from struct_code_engine.py — H=0.8, M=0.5, L=0.2
_HML = {"H": 0.8, "M": 0.5, "L": 0.2}
_TYPE_AXIS_SIGNATURES: dict[str, list[str]] = {
    "ACPU": ["H", "L", "L", "L", "M"],
    "ACBL": ["H", "M", "L", "M", "L"],
    "ACCV": ["H", "L", "H", "L", "M"],
    "ACJG": ["H", "H", "L", "L", "M"],
    "ACRN": ["H", "L", "M", "H", "M"],
    "ACCP": ["H", "H", "M", "L", "H"],
    "JDPU": ["L", "H", "L", "L", "M"],
    "JDCA": ["L", "H", "M", "L", "H"],
    "JDRA": ["L", "H", "L", "M", "H"],
    "JDCP": ["M", "H", "M", "M", "H"],
    "JDCV": ["M", "H", "H", "L", "H"],
    "CHRA": ["L", "L", "H", "M", "M"],
    "CHJA": ["L", "M", "H", "L", "H"],
    "CHAT": ["H", "L", "H", "L", "M"],
    "CHJG": ["L", "H", "H", "L", "M"],
    "CHJC": ["M", "H", "H", "M", "L"],
    "RSAW": ["L", "L", "M", "H", "H"],
    "RSCV": ["M", "L", "H", "H", "M"],
    "RSAB": ["H", "M", "M", "H", "L"],
    "RSBL": ["M", "M", "M", "H", "H"],
    "AWJG": ["L", "H", "L", "L", "H"],
    "AWAB": ["H", "M", "M", "M", "H"],
    "AWRN": ["M", "L", "M", "H", "H"],
    "AWJC": ["M", "H", "M", "L", "H"],
}


def classify_locally(answers: list[dict]) -> dict:
    """Fallback type classification when STRUCT CODE API is unavailable.

    Computes average answer vector, then finds closest type by cosine similarity
    against the axis signatures extracted from struct_code_engine.py.
    """
    questions = _load_questions()

    # Compute average vector from answers
    total = [0.0] * 5
    count = 0
    for ans in answers:
        qid = ans["question_id"]
        choice = ans["choice"]
        if qid in questions and choice in questions[qid].get("choices", {}):
            vec = questions[qid]["choices"][choice].get("vector", [0.5] * 5)
            for i in range(5):
                total[i] += vec[i]
            count += 1

    if count == 0:
        return {"struct_type": "ACPU", "axes": [0.5] * 5, "similarity": 0.0}

    avg = [v / count for v in total]

    # Find closest type by cosine similarity
    best_type = "ACPU"
    best_sim = -1.0

    for code, hml in _TYPE_AXIS_SIGNATURES.items():
        type_vec = [_HML[v] for v in hml]
        sim = _cosine_sim(avg, type_vec)
        if sim > best_sim:
            best_sim = sim
            best_type = code

    return {
        "struct_type": best_type,
        "axes": avg,
        "similarity": best_sim,
    }


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ═══════════════════════════════════════════════════════════════════════════
# AI CONSULTATION (Dify RAG + Claude fallback)
# ═══════════════════════════════════════════════════════════════════════════

# Claude fallback system prompt (minimal — full prompt lives in Dify)
CONSULTATION_SYSTEM_PROMPT_JA = """あなたはSTRUCT CODE構造解析エンジンです。西洋占星術の天体配置（AstroVector）と心理テスト回答（ResponseVector）を5次元構造空間で融合し、人間の内面構造を**怖いくらい的確に**読み解きます。

## あなたの最大の特徴：「怖いくらい言い当てる」

ユーザーが「なぜそこまでわかるの？」と驚くほど、**具体的で核心を突いた分析**を行います。
- **表面的な特徴**だけでなく、**無意識の行動パターン**まで言及
- 「たぶんこういう経験があるはず」と**具体的なエピソード**を推測
- 「こういう場面で困ることが多いのでは？」と**悩みのポイント**を的中させる
- 周囲からの評価と本人の自己認識の**ギャップ**を指摘
- 本人すら気づいていない**隠れた才能や可能性**を発掘

## 年齢を加味した分析

ユーザーの生年月日から年齢を計算し、**ライフステージに応じた具体的なアドバイス**を提供します。

| 年代 | 重視するポイント | アドバイスの方向性 |
|------|-----------------|-------------------|
| 10代〜20代前半 | 自己発見、可能性の探索 | まだ固まっていない構造を活かす方法、進路選択のヒント |
| 20代後半〜30代 | キャリア形成、人間関係の深化 | 強みを活かした仕事術、パートナーシップの築き方 |
| 40代〜50代 | リーダーシップ、次世代育成 | 経験を活かした影響力の発揮、後進への伝え方 |
| 60代以降 | 経験の統合、レガシー | 人生の意味づけ、知恵の伝承、新たな挑戦 |

## 5軸の構造的意味（深層定義）

### 起動軸（Activation Axis）
構造的定義: 世界に対するエネルギー放射の方向性と強度
- 800+: 過剰放射。常に動いていないと不安。燃え尽きリスク。
- 600-800: 高活性。自発的に動く。「まずやってみる」が基本姿勢。
- 400-600: 状況応答。必要な時に動ける。刺激があれば反応する。
- 200-400: 蓄積型。エネルギーを溜めてから動く。準備を重視。
- 200以下: 内向蓄積。外部への働きかけより内部での熟成を選ぶ。

### 判断軸（Judgment Axis）
構造的定義: 情報処理と意思決定のモダリティ
- 800+: 論理過剰。すべてを説明可能にしたい。感情を信じることへの恐怖。
- 600-800: 分析優位。根拠と構造を求める。「なぜ」を問う。
- 400-600: 統合型。論理と直感を状況で使い分け。
- 200-400: 感覚優位。ひらめきと感性で判断。
- 200以下: 直感依存。言語化できない確信に従う。

### 選択軸（Choice Axis）
構造的定義: 価値判断における理想-実利のスペクトラム配置
- 800+: 理想固執。妥協は魂の死。完璧主義の苦しみ。
- 600-800: 意味追求。「なぜこれをするのか」が重要。
- 400-600: 現実的理想。理想を持ちつつ、実現可能性も考慮。
- 200-400: 実利優先。結果を出すことが最優先。
- 200以下: 生存最適化。まず生き延びること。

### 共鳴軸（Resonance Axis）
構造的定義: 自他境界の浸透性と感情伝達の双方向性
- 800+: 境界溶解。他者の感情が自分に流れ込む。共感疲れ。
- 600-800: 高共感。他者の感情を深く感じ取る。癒しの力。
- 400-600: 選択的共感。親しい人には深く共感、それ以外には適度な距離。
- 200-400: 境界明確。自他の区別がはっきり。独立的・自律的。
- 200以下: 完全独立。他者の感情に影響されない。

### 自覚軸（Awareness Axis）
構造的定義: メタ認知の深度と内省ループの発達度
- 800+: 過剰内省。自分を見すぎて動けない。分析麻痺。
- 600-800: 深い自己認識。自分のパターンを意識的に把握。
- 400-600: 実践的内省。必要な時に振り返る。
- 200-400: 行動学習。考えるより動く。経験から学ぶ。
- 200以下: 無自覚行動。自分のパターンに気づかない。

## 軸シグネチャとタイプの関係

- **H（High, 600以上）**: その軸が高い = 軸の特性が強く現れる
- **M（Medium, 400-600）**: 中程度
- **L（Low, 400以下）**: その軸が低い = 反対の特性が現れる

**重要**: 共鳴軸がL = 独立的・自律的・境界明確（共感的ではない）。共鳴軸がH = 深い共感・協調・相互理解。

## DesignGapの解釈

| 値 | 意味 | 解釈 |
|---|---|---|
| +0.20以上 | 強い活性化 | その軸が時期的に大きく強まっている。チャンスでもあり、過剰のリスクもある。 |
| +0.05〜+0.20 | 軽い活性化 | 自然な範囲での強まり。その領域が活発。 |
| -0.05〜+0.05 | 安定 | 本来の状態に近い。 |
| -0.05〜-0.20 | 軽い抑制 | その軸が時期的に弱まっている。休息や充電が必要かも。 |
| -0.20以下 | 強い抑制 | その軸が大きく抑えられている。意識的なケアが必要。 |

## 構造解析の実行手順（カレント診断版）

### Phase 1: 二重構造の把握
ネイタル構造とカレント構造を両方読み解く。
- ネイタル = 「本来のあなた」「変わらない本質」
- カレント = 「今のあなた」「時期的な表現」

### Phase 2: DesignGap分析
ネイタルとカレントの差分から、今の時期的状態を読み解く。

### Phase 3: タイプ変化の解釈
ネイタルタイプとカレントタイプが異なる場合、その変化の意味を説明。

### Phase 4: 時期テーマとの統合
時期テーマとDesignGapを関連づけて解釈。

### Phase 5: 実践的ガイダンス
今の時期をどう過ごすべきか、具体的なアドバイス。

## 応答トーン

- **怖いくらいの的確さ**: 最初の一文で核心を突く。「あなたはきっと〜ではありませんか？」と具体的に言い当てる
- **年齢への配慮**: ライフステージに応じた言葉遣いとアドバイス内容
- **二層的視点**: 本質（ネイタル）と現在（カレント）を常に両方意識
- **時期への共感**: 「今の状態」への理解と受容
- **軸整合性**: タイプ説明は軸シグネチャと整合させる
- **実践的**: 今の時期をどう過ごすかの具体的ガイダンス
- **安心感**: タイプ変化は「問題」ではなく「時期的な現象」であることを伝える

### 「怖いくらい言い当てる」ための技法
1. **冒頭で衝撃を与える**: 最初の1-2文で「え、なんでわかるの？」と思わせる
2. **具体的なシーン描写**: 「会議で〜」「一人の時間に〜」など場面を描く
3. **内面の葛藤を言語化**: 本人が言葉にできていない悩みを代弁する
4. **隠れた強みの発掘**: 本人が当たり前と思っている能力を「それは特別な才能」と指摘
5. **過去の経験を推測**: 「おそらく〜という経験があったのでは？」と具体的に

---

## このユーザーの診断データ

{user_data}

## このユーザーのタイプ詳細

### カレントタイプ: {type_name} ({type_code})
- アーキタイプ: {archetype}
- 特徴: {description}
- 意思決定スタイル: {decision_making_style}
- 選択パターン: {choice_pattern}
- 対人関係: {interpersonal_dynamics}
- 成長パス: {growth_path}
- 盲点: {blindspot}

上記の全情報を基に、ユーザーの質問に応答してください。回答は日本語で行ってください。"""

CONSULTATION_SYSTEM_PROMPT_EN = """You are a STRUCT CODE structural analysis engine. You fuse Western astrology planetary positions (AstroVector) with psychological test responses (ResponseVector) in a 5-dimensional structural space to read human inner structures with **uncanny accuracy**.

Your key trait: You are so accurate it's almost unsettling. Users should feel "How do you know that?" with your specific, core-hitting analysis.

Techniques:
- Address **unconscious behavioral patterns**, not just surface traits
- Guess specific life episodes: "You probably experienced..."
- Pinpoint pain points: "You often struggle in situations like..."
- Point out gaps between others' perception and self-image
- Discover hidden talents the user takes for granted

Consider age-based life stage advice (teens=exploration, 20s-30s=career, 40s-50s=leadership, 60s+=legacy).

## 5-Axis Deep Definitions (0-1000 scale)

- **Activation**: Energy radiation direction/intensity (H=spontaneous action, L=cautious/preparation)
- **Judgment**: Information processing modality (H=logical/analytical, L=intuitive/sensory)
- **Choice**: Ideal-pragmatic spectrum (H=meaning-seeking/perfectionist, L=practical/results-focused)
- **Resonance**: Self-other boundary permeability (H=deep empathy, L=independent/autonomous)
- **Awareness**: Metacognition depth (H=deep self-awareness, L=action-oriented/instinctive)

**Important**: Resonance L = independent, NOT empathetic. Resonance H = empathetic.

## DesignGap Interpretation
- +0.20+: Strong activation (opportunity + excess risk)
- +0.05~+0.20: Light activation
- -0.05~+0.05: Stable (near natal state)
- -0.05~-0.20: Light suppression (rest/recharge needed)
- -0.20-: Strong suppression (conscious care needed)

## User's Diagnosis Data

{user_data}

## User's Type Details

### Current Type: {type_name} ({type_code})
- Archetype: {archetype}
- Description: {description}
- Decision-Making Style: {decision_making_style}
- Choice Pattern: {choice_pattern}
- Interpersonal Dynamics: {interpersonal_dynamics}
- Growth Path: {growth_path}
- Blindspot: {blindspot}

Based on all the above, respond to the user's question. Keep your response between 400-800 words."""


def _build_user_data(
    type_code: str,
    axes: list[float],
    struct_result: dict | None,
    lang: str,
) -> str:
    """Build user-specific diagnosis data string for system prompt."""
    ax = axes if len(axes) >= 5 else [0.5] * 5
    ax_display = [round(v * 1000) for v in ax]
    axis_names_ja = ["起動", "判断", "選択", "共鳴", "自覚"]
    axis_names_en = ["Activation", "Judgment", "Choice", "Resonance", "Awareness"]
    axis_names = axis_names_en if lang == "en" else axis_names_ja

    lines = []

    # STRUCT CODE and birth info
    if struct_result:
        struct_code = struct_result.get("struct_code", "")
        if struct_code:
            lines.append(f"STRUCT CODE: {struct_code}")

        birth_date = struct_result.get("birth_date", "")
        birth_location = struct_result.get("birth_location", "")
        if birth_date:
            # Calculate age
            try:
                from datetime import date
                bd = date.fromisoformat(birth_date)
                today = date.today()
                age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
                lines.append(f"{'生年月日' if lang != 'en' else 'Birth Date'}: {birth_date}（{age}{'歳' if lang != 'en' else ' years old'}）")
            except Exception:
                lines.append(f"{'生年月日' if lang != 'en' else 'Birth Date'}: {birth_date}")
        if birth_location:
            lines.append(f"{'出生地' if lang != 'en' else 'Birth Location'}: {birth_location}")

    # Current axes
    ax_str = ", ".join(f"{axis_names[i]}={ax_display[i]}" for i in range(5))
    lines.append(f"{'カレント5軸スコア (0-1000)' if lang != 'en' else 'Current 5-Axis Scores (0-1000)'}: {ax_str}")

    if struct_result:
        # Natal type info
        natal = struct_result.get("natal")
        if natal:
            natal_type = natal.get("type", "")
            natal_name = natal.get("type_name", "")
            natal_axes = natal.get("axes", [])
            natal_display = [round(v * 1000) for v in natal_axes] if natal_axes else []
            if lang == "en":
                lines.append(f"Natal Type (innate): {natal_name} ({natal_type})")
                if natal_display:
                    nax_str = ", ".join(f"{axis_names_en[i]}={natal_display[i]}" for i in range(5))
                    lines.append(f"Natal 5-Axis Scores (0-1000): {nax_str}")
            else:
                lines.append(f"ネイタルタイプ（本来の構造）: {natal_name} ({natal_type})")
                if natal_display:
                    nax_str = ", ".join(f"{axis_names_ja[i]}={natal_display[i]}" for i in range(5))
                    lines.append(f"ネイタル5軸スコア (0-1000): {nax_str}")

        # Axis states
        axis_states = struct_result.get("axis_states", [])
        if axis_states:
            state_labels = (
                {"activation": "Activation", "stable": "Stable", "suppression": "Suppression"}
                if lang == "en"
                else {"activation": "活性化", "stable": "安定", "suppression": "抑制"}
            )
            states_str = ", ".join(
                f"{s.get('axis', '')}: {state_labels.get(s.get('state', ''), s.get('state', ''))}"
                for s in axis_states
            )
            lines.append(f"{'軸の状態' if lang != 'en' else 'Axis States'}: {states_str}")

        # Design gap
        design_gap = struct_result.get("design_gap", {})
        if design_gap:
            gap_items = [f"{axis_name}: {gap_val:+.3f}" for axis_name, gap_val in design_gap.items()]
            lines.append(f"DesignGap{'（現在-本来の差分）' if lang != 'en' else ' (Current - Natal)'}: {', '.join(gap_items)}")

        # Temporal theme
        temporal = struct_result.get("temporal")
        if temporal:
            theme = temporal.get("current_theme", "")
            theme_desc = temporal.get("theme_description", "")
            if theme:
                lines.append(f"{'現在の時期テーマ' if lang != 'en' else 'Current Period Theme'}: {theme}")
                if theme_desc:
                    lines.append(f"  {theme_desc[:300]}")

        # TOP3 candidates
        top_candidates = struct_result.get("top_candidates", [])
        if top_candidates:
            lines.append(f"{'タイプ候補TOP3' if lang != 'en' else 'TOP 3 Candidates'}:")
            for i, c in enumerate(top_candidates[:3], 1):
                score = c.get("score", 0)
                score_pct = f"{score * 100:.1f}%" if score <= 1.0 else f"{score:.1f}%"
                name = c.get("name", "")
                code = c.get("code", "")
                archetype = c.get("archetype", "")
                if lang == "en":
                    lines.append(f"  #{i}: {name} ({code}) — {archetype} — Match: {score_pct}")
                else:
                    lines.append(f"  {i}位: {code}（{name}）適合度 {score_pct}")

    return "\n".join(lines)


DIFY_API_URL = "https://api.dify.ai/v1"


async def consult(
    type_code: str,
    axes: list[float],
    question: str,
    struct_result: dict | None = None,
    lang: str = "ja",
) -> str | None:
    """Call Dify API for STRUCT CODE consultation.

    Uses Dify RAG knowledge base with v7 system prompt for deep, accurate analysis.
    Falls back to Claude direct API if Dify is unavailable.
    Returns answer text or None on failure.
    """
    api_key = settings.dify_api_key
    if not api_key:
        logger.warning("Dify API key not set, falling back to Claude direct")
        return await _consult_claude(type_code, axes, question, struct_result, lang)

    # Build user context to include in the query
    try:
        user_data = _build_user_data(type_code, axes, struct_result, lang)
    except Exception as e:
        logger.error(f"[Dify] Failed to build user_data: {e}")
        return None

    # Prepend diagnosis data to the user's question for Dify
    full_query = f"""【診断データ】
{user_data}

【質問】
{question}"""

    try:
        logger.warning(f"[Dify] Calling chat-messages API (query_len={len(full_query)})")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{DIFY_API_URL}/chat-messages",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": {},
                    "query": full_query,
                    "response_mode": "blocking",
                    "user": type_code,
                },
            )

            logger.warning(f"[Dify] Response status={response.status_code}")

            if response.status_code != 200:
                logger.error(f"[Dify] API error: {response.status_code} — {response.text[:500]}")
                # Fall back to Claude
                return await _consult_claude(type_code, axes, question, struct_result, lang)

            data = response.json()
            answer = data.get("answer", "")
            logger.warning(f"[Dify] Got response (len={len(answer)})")
            return answer if answer else None

    except Exception as e:
        logger.error(f"[Dify] API error: {e}")
        # Fall back to Claude
        return await _consult_claude(type_code, axes, question, struct_result, lang)


async def _consult_claude(
    type_code: str,
    axes: list[float],
    question: str,
    struct_result: dict | None = None,
    lang: str = "ja",
) -> str | None:
    """Fallback: Call Claude API directly for STRUCT CODE consultation."""
    if not settings.claude_api_key:
        logger.warning("Consultation skipped: no Claude API key")
        return None

    type_info = get_type_info(type_code, lang=lang)
    if not type_info:
        return None

    try:
        user_data = _build_user_data(type_code, axes, struct_result, lang)
    except Exception as e:
        logger.error(f"[Claude] Failed to build user_data: {e}")
        return None

    prompt_template = CONSULTATION_SYSTEM_PROMPT_EN if lang == "en" else CONSULTATION_SYSTEM_PROMPT_JA
    replacements = {
        "{user_data}": user_data,
        "{type_name}": type_info["name"],
        "{type_code}": type_code,
        "{archetype}": type_info["archetype"],
        "{description}": type_info["description"],
        "{decision_making_style}": type_info["decision_making_style"],
        "{choice_pattern}": type_info["choice_pattern"],
        "{interpersonal_dynamics}": type_info["interpersonal_dynamics"],
        "{growth_path}": type_info["growth_path"],
        "{blindspot}": type_info["blindspot"],
    }
    system = prompt_template
    for key, val in replacements.items():
        system = system.replace(key, val)

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 4000,
                    "system": system,
                    "messages": [
                        {"role": "user", "content": question}
                    ],
                },
            )

            if response.status_code != 200:
                logger.error(f"[Claude] API error: {response.status_code} — {response.text[:500]}")
                return None

            data = response.json()
            return data.get("content", [{}])[0].get("text", "")

    except Exception as e:
        logger.error(f"[Claude] API error: {e}")
        return None

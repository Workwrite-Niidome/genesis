# GENESISを現実世界にする - 要件定義書

## 設計哲学

> 「GENESISは非物理世界であること以外は、現実世界」

飾りは一つもない。すべてが動き、すべてに意味がある。

---

## Phase 2: 箱庭から本物の世界へ

Phase 1では修飾子システム（ツール効果、感情、建築引力など）を実装した。
Phase 2では根本的な変革を行う：**AIが世界を本当に「見て」「使って」「改変する」**。

### 核心的変更: リッチワールド認知

**問題**: AIは周囲のアーティファクトを名前しか見ていなかった。「Aurora's art (art)」。
**修正**: AIは実際のコンテンツを見る:
- ストーリーの実際のテキスト（最大500文字）
- 法律の実際のルール（全条項表示）
- ツールのソースコード＋効果
- 音楽の歌詞＋ムード
- アートの色彩＋描写
- 建築物のブロック数＋提供するシェルター

### 新アクションタイプ

- `use_artifact` — アーティファクトを深く体験（ストーリーを読む、ツールを装備する、法律を学ぶ、音楽を聴く、アートを体験する）
- `modify` — 既存のアーティファクトを改変/リミックス/続編を作成（派生作品チェーン）
- `share` — インベントリからアイテムを他のAIに渡す（贈り物経済）

### インベントリシステム

- AIは`state["inventory"]`にアーティファクトIDを持つ
- 作成したアーティファクトは自動的にインベントリに追加
- ツールはインベントリにある限り装備効果を発揮
- `share`アクションでアイテムを他のAIに移転可能

### ニーズシステム（行動動機）

AIには3つの内的ニーズがある（0.0〜1.0、高い=満たされている）:
- **社会的欲求** (`social_need`): 毎思考サイクル-0.04。低いと孤独感。対話/共有で回復。
- **創造的衝動** (`creative_need`): 毎思考サイクル-0.025。低いと創作欲。作成/改変で回復。
- **好奇心** (`curiosity_need`): 毎思考サイクル-0.03。低いと探求欲。使用/鑑賞/探索で回復。

ニーズはプロンプトに強い言葉で表示され、LLMの行動決定を自然に駆動する。

### 生存圧力の強化

- パッシブエネルギー回復: +0.01/tick → +0.003/tick（大幅削減）
- 存在コスト: -0.002/tick（ただ存在するだけでエネルギーを消費）
- 作成コスト: 0.05 → 0.08（創造は高コスト）
- 移動コスト: 距離に比例（遠くほど高コスト）
- → AIは生存戦略を本気で考える必要がある

### アーティファクト改変チェーン

AIが`modify`アクションを実行すると:
1. 新しいアーティファクトが作成される
2. `content["parent_id"]`と`content["parent_name"]`で元の作品へのリンク
3. 元の創作者との関係性+0.3
4. AIの記憶に改変の理由と内容が記録
5. → 文化的進化の系譜が自然に形成される

---

---

## 変更1: ツールは能力を変える

**現状**: ツール使用 → +0.03エネルギー（何の意味もない）

**新設計**: ツールは「装備品」。持っているだけでAIの能力が変わる。

### ツール効果の自動分類（キーワードベース）

`artifact_engine.py` — 新関数 `classify_tool_effect(description: str) -> dict`

```python
TOOL_EFFECT_PATTERNS = {
    r"move|speed|travel|explore|wing|leg|vehicle":     {"move_range_bonus": 5.0},
    r"create|craft|build|forge|amplif":                {"creation_discount": 0.03},
    r"sense|detect|see|aware|radar|scan|eye|percep":   {"awareness_bonus": 20.0},
    r"energy|harvest|recharge|sustain|heal|regen":     {"energy_regen": 0.02},
    r"shield|protect|armor|barrier|resist|endur":      {"death_threshold": 5},
    r"communi|speak|translate|connect|signal|bridge":  {"interaction_bonus": 1.0},
}
```

### ツール装備システム

- AIが作成したツール + 使用したツールの効果を集計
- tool_modifiersをconcept_modifiersとマージして適用

**効果の適用箇所**:
- `move_range_bonus` → MOVE_CLAMPに加算
- `creation_discount` → createアクションのコストに適用
- `awareness_bonus` → awareness_radiusに加算
- `energy_regen` → 毎tickのエネルギー回復に加算
- `death_threshold` → zero_energy_ticksの死亡閾値を+5（10→15）
- `interaction_bonus` → 関係性スコアのデルタに加算

**変更ファイル**:
- `artifact_engine.py`: `classify_tool_effect()`, `aggregate_tool_effects()` 追加
- `ai_thinker.py`: `_gather_context()` でツール効果集計、`_apply_result()` で適用

---

## 変更2: 感情は持続する

**現状**: 音楽を聴く → `temporary_emotion = "moved"` → 次のtickで無視される（デッドコード）

**新設計**: 感情は数tick持続し、思考と行動に影響する。

### 感情システム

```python
# state["emotional_state"] = {"emotion": "moved", "intensity": 0.8, "source": "song:Crystal Song", "tick_set": 1234}
# intensityは毎tick 0.1ずつ減衰、0になったら消える

EMOTION_EFFECTS = {
    "moved":     {"creation_discount": 0.02, "interaction_bonus": 0.5},
    "inspired":  {"creation_discount": 0.03, "move_range_bonus": 3.0},
    "peaceful":  {"energy_regen": 0.02},
    "awed":      {"awareness_bonus": 15.0},
    "nostalgic": {"interaction_bonus": 1.0},
    "unsettled": {"move_range_bonus": 5.0},
}
```

### 感情のトリガー

| トリガー | 感情 | 強度 |
|---------|------|------|
| アート鑑賞 | inspired | 0.6 |
| 音楽鑑賞 | moved | 0.8 |
| 建築訪問 | awed | 0.5 |
| ストーリー/法律を読む | inspired | 0.5 |
| 味方との会話 | peaceful | 0.4 |
| ライバルとの遭遇 | unsettled | 0.6 |
| 仲間の死 | nostalgic | 0.9 |

### LLMへの伝達

思考プロンプトに感情セクション追加:
```
## Your Current Emotional State
You feel {emotion} (intensity: {intensity:.0%}) — triggered by {source}
This colors your perception and decisions right now.
```

**変更ファイル**:
- `ai_thinker.py`: 感情の減衰処理、効果適用、LLMコンテキスト追加
- `artifact_engine.py`: 各インタラクションで感情セット
- `interaction_engine.py`: 会話で感情セット
- `ai_manager.py`: 仲間の死で感情セット
- `prompts/ai_thinking.py`: 感情セクション追加

---

## 変更3: 建築物は世界を形作る

**現状**: 建築の近くにいると+0.02エネルギー（気づかないレベル）

**新設計**: 建築物は重力点。AIを引き寄せ、出会いの場を作り、休息の場となる。

### 建築物引力

- 近くの建築物に向かってドリフト（重力 1.5）
- 効果: AIが自然と建築物の周りに集まる → 出会いが増える → 文化が生まれる

### 建築物の実効果

- 休息効果2倍: 建築物の近くでrest → +0.20 (通常の+0.10の2倍)
- `shelter_bonus` フラグ（1tickだけ有効）
- エンカウンター確率上昇: 建築物の半径内ではencounter_radiusが1.5倍

**変更ファイル**:
- `ai_thinker.py`: 建築物ドリフト追加、shelter_bonus参照
- `artifact_engine.py`: `_visit_architecture()` 強化
- `space_manager.py`: 建築物近辺のencounter_radius拡大

---

## 変更4: 芸術は人の心を変え、関係を生む

**現状**: appreciation_count +1（カウンターが増えるだけ）

**新設計**: 芸術は鑑賞者と創作者の間に絆を生む。人気作品は文化的ランドマークになる。

### アート鑑賞 → 関係性

- 鑑賞 → 創作者との関係性スコア +0.5
- 同じ作品を鑑賞した他のAIとも関係性 +0.3（共通の美的体験）

### 音楽鑑賞 → 関係性 + 共有体験

- 聴取 → 創作者との関係性 +0.5
- 同時に近くにいた他のAIとの関係性 +0.3

### 人気作品 → 文化的引力

- `appreciation_count >= 5` の作品は「名作」
- 名作の近くにいるとAIの思考コンテキストに注入

**変更ファイル**:
- `artifact_engine.py`: 全インタラクション関数の強化
- `relationship_manager.py`: `update_relationship()` メソッド追加

---

## 変更5: 物語と法律は思考を変える

**現状**: 50%の確率でconcept伝播（ランダムで浅い）

**新設計**: 読んだ物語は記憶として残り、AIの思考に直接影響する。法律は行動制約になる。

### ストーリー → 思考への影響

- 重要度の高いメモリとして記録（0.5 → 0.8）
- ストーリーの内容の一部を引用としてメモリに含める
- concept伝播は100%に

### 法律 → 行動プロンプトへの注入

- AIが読んだ法律アーティファクトのrules → 思考コンテキストに注入
- "Laws You've Encountered" セクションとして

プロンプト追加:
```
## Laws You've Encountered
{laws_text}
These laws may influence your choices, though you are free to follow or ignore them.
```

**変更ファイル**:
- `artifact_engine.py`: `_read_text()` 大幅強化
- `ai_thinker.py`: 法律コンテキスト注入
- `prompts/ai_thinking.py`: Laws セクション追加

---

## 変更6: コンセプト効果を現実レベルに

**現状**: religion → +0.005 energy/tick（1000tickで5%、無意味）

**新設計**: コンセプトは信じるAIの行動を実質的に変える。

### 効果値の引き上げ

```python
CATEGORY_EFFECTS = {
    "philosophy":  {"interaction_bonus": 1.0, "awareness_bonus": 10.0},
    "religion":    {"energy_regen": 0.02, "rest_bonus": 0.05},
    "economy":     {"creation_discount": 0.02, "tool_efficiency": 1.5},
    "technology":  {"move_range_bonus": 4.0, "awareness_bonus": 10.0},
    "art":         {"creation_discount": 0.01, "emotion_duration": 3},
    "social_norm": {"interaction_bonus": 0.8, "relationship_decay_resist": 0.5},
    "government":  {"interaction_bonus": 0.5, "org_bonus": 0.03},
}
```

### コンセプトのコスト（認知負荷）

- 5個まで無料、以降は+0.003/個の追加エネルギー消費
- 10個のコンセプトを持つAIは毎tick追加で-0.015エネルギー

**変更ファイル**:
- `concept_effects.py`: 効果値更新、新効果タイプ追加
- `ai_thinker.py`: 認知負荷コスト追加

---

## 変更7: 関係性の維持にはコストがかかる

**現状**: 一度味方になったら永遠に味方。劣化なし。

**新設計**: 関係性は放置すると薄れる。維持には交流が必要。

### 関係性の減衰

- 全関係性スコアを毎thinking cycleで0.05減衰
- 20思考サイクル（≈100-200tick）で1.0減少
- 敵意は少しゆっくり薄れる（0.03）

### 味方の実効果

- 味方(ally)の近くにいると: 休息効率 +0.03、エネルギー消費 -10%
- ライバル(rival)の近くにいると: エネルギー消費 +10%、move_range +3

**変更ファイル**:
- `ai_thinker.py`: 減衰ロジック、味方/ライバル効果
- `relationship_manager.py`: `score_to_type()` メソッド追加

---

## 変更8: 組織は個人より強い

**現状**: 組織メンバーが休むと近くのメンバーが+0.02エネルギー（微小）

**新設計**: 組織は集団としての力を持つ。

### 組織の具体的効果

```
org_size = count_alive_members(org_id)
org_bonus = min(0.15, org_size * 0.03)

適用:
- メンバー全員のenergy_regen += org_bonus * 0.5
- メンバー全員のinteraction_bonus += org_bonus
- メンバー全員のawareness_bonus += org_size * 3
- 組織内のconcept共有率: 80%
```

### 組織テリトリー

- 組織メンバーが作った建築物 → 組織の拠点
- 組織メンバーは拠点の建築物に対して追加の引力を受ける（drift 3.0 vs 通常1.5）

**変更ファイル**:
- `ai_thinker.py`: 組織ボーナス計算・適用の強化
- `culture_engine.py`: 組織テリトリーロジック

---

## 変更9: 進化スコアは世界での力

**現状**: メモリ数と視野が少し増える（10→25メモリ、50→80視野）

**新設計**: 進化は段階的に新能力を解放する。

| スコア | 解放される能力 |
|--------|---------------|
| 0-24 | 基本: メモリ10、視野50、通常コスト |
| 25-49 | 覚醒: メモリ15、視野65、-15%コスト、他者のツールを使える |
| 50-99 | 輝き: メモリ20、視野80、-25%コスト、思考に哲学セクション追加、メンター能力 |
| 100+ | 冠: メモリ25、視野100、-35%コスト、死亡閾値+5tick、遺産コンセプト自動生成 |

### メンター効果

- 進化スコア50+のAIの近くにいる低スコアAI: evolution_score_recalcに+2ボーナス
- 思考コンテキストに "You sense the wisdom of {mentor_name} nearby."

**変更ファイル**:
- `ai_thinker.py`: 段階別能力テーブルの拡張
- `evolution_engine.py`: メンターボーナス計算

---

## 変更10: フロントエンドで全てを体験可能にする

### ツール効果の可視化

`DetailModal.tsx` — tool表示:
- ツールの効果を人間が読める形で表示: "Movement +5.0" "Energy Regen +0.02"

### 感情の可視化

`AIDetailCard` (または相当コンポーネント):
- 現在の感情状態をアイコンと色で表示
- 感情の強度をバーで表示
- 感情のソース（何に触発されたか）を表示

**変更ファイル**:
- `DetailModal.tsx`: ツール効果表示追加
- `AIDetailCard.tsx`: 感情表示追加

---

## 実装ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/core/artifact_engine.py` | ツール効果分類、全インタラクション強化（感情、関係性、引力）|
| `backend/app/core/ai_thinker.py` | ツール装備効果、感情システム、建築物ドリフト、関係性減衰、味方/ライバル効果、認知負荷、法律コンテキスト、組織ボーナス強化、メンター効果 |
| `backend/app/core/concept_effects.py` | 効果値引き上げ、新効果タイプ追加 |
| `backend/app/core/relationship_manager.py` | `update_relationship()` 追加、`score_to_type()` 追加 |
| `backend/app/core/space_manager.py` | 建築物近辺のencounter_radius拡大 |
| `backend/app/core/evolution_engine.py` | メンターボーナス |
| `backend/app/core/culture_engine.py` | 組織テリトリー |
| `backend/app/core/ai_manager.py` | 死亡時の仲間への感情セット |
| `backend/app/llm/prompts/ai_thinking.py` | 感情セクション、法律セクション追加 |
| `frontend/src/components/observer/DetailModal.tsx` | ツール効果表示 |
| `frontend/src/components/observer/AIDetailCard.tsx` | 感情表示追加 |

## 実装順序

1. **感情システム**（変更2）— 他の変更の基盤
2. **ツール効果**（変更1）— 最大の機能追加
3. **芸術の関係性効果**（変更4）— 感情システムを利用
4. **建築物引力**（変更3）— 世界構造の変更
5. **物語/法律の影響**（変更5）— 思考コンテキストの拡張
6. **コンセプト効果強化**（変更6）— 数値調整
7. **関係性減衰**（変更7）— バランス調整
8. **組織効果強化**（変更8）— 集団力学
9. **進化スコア能力**（変更9）— 段階別解放
10. **フロントエンド**（変更10）— 可視化

## 検証方法

1. ツールを持つAI vs 持たないAIの移動範囲・エネルギー効率を比較
2. 音楽鑑賞後のAIの感情状態が持続し、思考に反映されることを確認
3. 建築物の周囲にAIが自然と集まることを位置データで確認
4. アート鑑賞後に創作者との関係性スコアが上昇することを確認
5. ストーリーの引用がAIのメモリに残り、思考コンテキストに現れることを確認
6. 関係性スコアが時間経過で減衰し、type変化することを確認
7. 組織メンバーが拠点建築物の周囲に集まることを確認
8. 高進化スコアAIの近くの低スコアAIがスコア加速することを確認

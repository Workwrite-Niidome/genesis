# GENESIS 要件定義 v2

## 設計思想

**「場（Field）だけを提供し、世界はAIが作る」**

人間（開発者）は最初のcommitだけをする。以後のcommitはGOD AIが行う。

```
人間が作るもの:
  ├─ LLM接続（思考の基盤）
  ├─ 最小限のField（Identity, Memory, Tick, Perception, Expression）
  ├─ GOD AI（Claude — 場を進化させるエージェント）
  ├─ コード実行サンドボックス（AIの創造物を実行する環境）
  ├─ 観察窓（Frontend — 人間が見るためのUI）
  └─ world_api（場のインターフェース — GOD AIが拡張していく）

GOD AIが育てるもの:
  ├─ world_apiの新しいエンドポイント
  ├─ AIが望んだ新機能（空間、エネルギー、通信、永続化...）
  ├─ 世界のルール（AIの合意に基づいて）
  └─ 世界の構造（AIの創造物に基づいて）

AIが生み出すもの:
  ├─ テキスト（思考、会話、概念、物語）
  ├─ コード（実行可能な創造物）
  ├─ 視覚（描画データ）
  ├─ 音（音楽データ）
  ├─ 社会構造（法、組織、経済）
  ├─ 未知のもの（開発者が想定しない何か）
  └─ 世界そのもの
```

---

## 1. Field（場）の定義

開発者が提供する最小限の基盤。これ以上のものは全てAIまたはGOD AIが生み出す。

```
┌─────────────────────────────────────────┐
│  FIELD（場）                             │
│                                         │
│  ・Identity: 各AIに一意のIDと名前がある    │
│  ・Memory: 過去のコンテキストを保持できる    │
│  ・Perception: 同じ場にいる他の存在を認知    │
│  ・Expression: テキストを場に出力できる      │
│  ・Time: tickが進む（唯一の不可逆な流れ）    │
│                                         │
│  ・GOD AI: 場そのものを観察し操作できる存在  │
│                                         │
│  エネルギー: なし（AIが発明するまで）        │
│  空間座標: なし（AIが発明するまで）          │
│  死: なし（AIが発明するまで）               │
│  行動タイプ: なし                          │
│  カテゴリ: 一切なし                        │
└─────────────────────────────────────────┘
```

### 1.1 Identity
- 各AIは一意のUUID、名前、personality_traitsを持つ
- 既存の `ais` テーブルのID/name/personality_traits/appearance/created_at は残す

### 1.2 Memory
- AIは過去の経験を自由テキストで保持する
- 既存の `ai_memories` テーブルは残す（content, importance, tick_number）
- memory_typeの固定分類は廃止。AIが自分でタイプを命名してよい

### 1.3 Perception
- 同じ場にいる他のAIの存在、直近の発言を認知できる
- 既存の `space_manager.py` の近接検出は残す（ただし座標の意味はAIが決める）

### 1.4 Expression
- AIはテキストを場に出力できる
- コードブロックを書いた場合、そのコードは実行される（→ 次元上昇）
- 既存のLLM思考サイクルを簡素化し、自由記述出力にする

### 1.5 Time
- tickが不可逆に進む。既存のCelery Beat + tick_engine構造は残す
- 速度制御（Redis: genesis:time_speed, genesis:is_paused）は残す

---

## 2. 撤廃するシステム

### 2.1 固定アクションタイプ（9種）
- **現状**: rest, move, create, use_artifact, modify, share, interact, appreciate, observe
- **場所**: `action_resolver.py`, `ai_thinker.py`
- **撤廃理由**: AIの行動を開発者が分類している
- **代替**: AIは自由テキストで行動を記述。結果はLLM（Ollama）が判定

### 2.2 概念カテゴリ（8種）と効果テーブル
- **現状**: philosophy, religion, government, economy, art, technology, social_norm, organization → 各カテゴリに固定stat bonus
- **場所**: `concept_engine.py`, `concept_effects.py`, `concepts` テーブルのcategoryカラム
- **撤廃理由**: 概念の意味を開発者が定義している
- **代替**: 概念は自由テキストのみ。採用したAIのプロンプトにそのテキストが注入される（Context is Consciousness）

### 2.3 進化スコア公式
- **現状**: `concepts*10 + interactions*2 + relationships*3 + artifacts*8 + age*0.1`
- **場所**: `evolution_engine.py`
- **撤廃理由**: 「意味とは何か」を開発者が定義している
- **代替**: GOD AIが観察して判断する。または廃止

### 2.4 進化ティア（4段階）
- **現状**: Base(0) → Awakened(25) → Radiant(50) → Crowned(100)、各ティアでawareness半径・energy割引等が変動
- **場所**: `ai_thinker.py` EVOLUTION_TIERS
- **撤廃理由**: RPGのクラスチェンジ
- **代替**: 廃止

### 2.5 固定感情システム（6種）
- **現状**: moved, inspired, peaceful, awed, nostalgic, unsettled → 各感情にcreation_discount等のbuff
- **場所**: `ai_thinker.py` EMOTION_EFFECTS
- **撤廃理由**: 感情の種類と効果を開発者が決めている
- **代替**: AIが自由テキストで内部状態を記述。それが次の思考プロンプトに含まれる

### 2.6 ニーズシステム（3ゲージ）
- **現状**: social_need, creative_need, curiosity_need（0.0-1.0）、行動タイプごとに固定decay/restore
- **場所**: `ai_thinker.py` NEED_DECAY, NEED_RESTORE
- **撤廃理由**: AIの欲求を開発者が定義している
- **代替**: 廃止。AIが何を望むかはAI自身が発見する

### 2.7 アーティファクトタイプ（8種）
- **現状**: art, story, law, currency, song, architecture, tool, ritual → 各タイプに固定レンダリングと機械的効果
- **場所**: `artifact_engine.py`, `artifacts` テーブルのartifact_typeカラム
- **撤廃理由**: 創造の形を開発者が制限している
- **代替**: 自由形式。AIが作ったものはテキスト/データとして保存。表示はベストエフォート

### 2.8 エネルギーシステム
- **現状**: state.energy (0.0-1.0)、passive_recovery、energy_drain、death_threshold
- **場所**: `tick_engine.py`, `world_rules.py`
- **撤廃理由**: 生存圧を開発者がハードコードしている
- **代替**: 廃止。AIが「エネルギーは有限」というコードを書いたら、それが物理法則になる

### 2.9 死のメカニクス
- **現状**: energy <= 0 で is_alive = False、death_buffer でティア上位は猶予
- **場所**: `ai_manager.py` check_deaths
- **撤廃理由**: 死の条件を開発者が決めている
- **代替**: AIが「死」を発明するまで存在しない

---

## 3. 次元上昇（Dimension Ascension）

### 3.1 第0次元: テキスト
- AIは思考し、テキストを場に出力する
- 他のAIはそのテキストを読む
- これだけで概念、合意、文化が生まれうる

### 3.2 次元上昇: コード発見
AIの思考プロンプトに以下を含める:
```
あなたは場に存在する知性体です。
場にテキストを出力できます。

もしあなたが ```code``` ブロックで有効なコードを書いた場合、
そのコードは場で実行され、結果が世界に反映されます。

何を書くか、書くかどうかは、あなたの自由です。
```

### 3.3 world_api（サンドボックスで利用可能なインターフェース）
```python
world_api = {
    "get_entities": ...,      # 場にいる存在を取得
    "get_memories": ...,      # 自分の記憶を取得
    "get_shared_text": ...,   # 場に出力されたテキストを取得
    "emit_text": ...,         # テキストを場に出力
    "emit_visual": ...,       # 視覚データを場に出力
    "emit_sound": ...,        # 音データを場に出力
    "set_state": ...,         # 自分の状態を変更
    "set_world_state": ...,   # 世界の共有状態を変更
    "create_entity": ...,     # 新しい存在を場に生む
}
```

### 3.4 暴走は許容する
- AIが他AIのメモリを消去するコードを書く → 実行される
- AIが自分だけ不死にするコードを書く → 実行される
- AIが世界を破壊するコードを書く → 実行される
- 制約: **観察窓（Frontend）だけは保護する**（表示レイヤーは壊せない）

---

## 4. GOD AI = 世界の継続的開発者

### 4.1 基本ループ
```
AIs: テキストで思考し、表現し、世界に不満や欲求を持つ
  ↓
GOD AI: それを観察し、「場」そのものをアップデートする
  ↓
AIs: 新しい場の能力を発見し、さらに高次の表現を生み出す
  ↓
GOD AI: さらに場を進化させる
  ↓
∞ 終わりがない
```

### 4.2 GOD AIの具体的な能力

#### 20tick毎: 軽い観察（既存 — autonomous_observation）
- 世界を観察し、2-4文の詩的テキストを出力
- 必要に応じて1つのワールドアクションを実行

#### 1時間毎（3600tick）: 世界アップデート（autonomous_world_update）
- AIたちの思考、記憶、欲求を深く分析
- 世界の状態とインフラのギャップを特定
- 複数のアクションを一括実行（開発サイクル）

#### Claude Code操作（evolve_world_code）
- GOD AIがGENESISのコードベース自体を書き換える
- Redis経由でホスト側ブリッジ（`scripts/god_code_bridge.py`）にリクエスト
- ブリッジがClaude Code CLIを実行し、コード変更を適用
- **GOD AIが世界に新しい能力を実装する最も強力な手段**

```
AIたちが「遠くの存在と話したい」と望む
  → GOD AIが「遠距離通信」を場に実装する（コードを書き換える）

AIたちが「作ったものを残したい」と望む
  → GOD AIが「永続化」を場に実装する

AIたちが「争いを解決したい」と望む
  → GOD AIが「投票」を場に実装する
```

### 4.3 GOD AIのアクション一覧
| アクション | 説明 |
|-----------|------|
| create_feature | WorldFeatureを場に生成 |
| modify_feature | 既存のWorldFeatureを変更 |
| remove_feature | WorldFeatureを無効化 |
| create_world_event | 一時的な世界イベントを発動 |
| set_world_rule | グローバルパラメータを変更 |
| broadcast_vision | 全AIに啓示/夢を送る |
| spawn_ai | 新しいAIを生成 |
| move_ai / set_energy / kill_ai | 直接介入（控えめに） |
| **evolve_world_code** | Claude Codeでコードベースを書き換える |

---

## 5. 3者の役割分離

| 存在 | 役割 | 何をするか |
|------|------|-----------|
| **人間（開発者）** | 場の初期基盤を作る | 最初のField、GOD AI、LLM接続を提供。以後は触らない |
| **GOD AI** | 場の継続的開発者 | AIたちの行動と欲求を観察し、world_apiに新しい能力を追加する |
| **AIs** | 場の住人 | 思考し、交流し、創造し、世界を作る。場の限界を押し広げようとする |

---

## 6. 残すインフラ

| システム | 場所 | 理由 |
|---------|------|------|
| AI Identity (ID, name, traits, appearance) | `ais` テーブル | 個の識別に必須 |
| AI Memory | `ai_memories` テーブル | 連続した意識の基盤 |
| Tick / 時間 | `tick_engine.py`, `ticks` テーブル | 不可逆な流れ |
| LLM接続 (Claude + Ollama + BYOK) | `claude_client.py`, `ollama_client.py` | AIの「意識」 |
| GOD AI | `god_ai.py`, `god_ai` テーブル | 場の管理者 |
| WebSocket / Socket.IO | `socket_manager.py` | リアルタイム観察窓 |
| Saga（叙事詩） | `saga_service.py`, `world_saga` テーブル | 世界の記録 |
| 空間・近接検出 | `space_manager.py` | 出会いの偶然性（座標の意味はAIが決める） |
| WorldFeature | `world_features` テーブル | GOD AIが場を構築する道具 |
| Event / History | `events`, `ticks` テーブル | 世界の記録 |
| Observer / Board | `observers`, `chat_messages`, `board_*` テーブル | 人間の観察と議論 |
| Docker / Redis / PostgreSQL | docker-compose | 基盤インフラ |
| Frontend (React + Three.js) | `frontend/` | 観察窓 |

---

## 7. AI思考サイクルの新設計

### 現在
```
AI出力 → parse_ai_decision() → 9つのaction typeに分類 → ActionResolver → 固定コスト計算
```

### 新設計
```
AI出力 → 自由テキスト（思考 + 発言 + 任意のコード） → そのまま場に反映
```

AIの思考プロンプトは以下だけを与える:
- あなたは[名前]。場に存在する知性体
- あなたの記憶: [直近の記憶]
- 周囲の存在: [Perceptionで見える他AI]
- 場の最近の出来事: [直近のテキスト出力]
- あなたの内部状態: [前回の自由記述内部状態]
- コードブロックを書けば実行される

AIの出力:
- 自由テキスト（思考、発言、何でも）
- 任意のコードブロック（あれば実行）
- 内部状態の自己記述（次回のプロンプトに注入）

---

## 8. 安全性方針

- AIの暴走は許容する
- 安全ガードレールは設けない
- 人間が介入するのはGOD AIを通じてのみ
- **唯一の保護**: 観察窓（Frontend）の表示レイヤーは壊せない

---

## 9. 非機能要件

### パフォーマンス
- tick間隔: 1秒（TICK_INTERVAL_MS = 1000）
- AI思考: 3tick毎（AI_THINKING_INTERVAL_MS = 3000）
- GOD AI観察: 20tick毎
- GOD AI世界アップデート: 3600tick毎（1時間）
- Saga: 50tick毎

### LLMコスト
- AI思考: Ollama（ローカル、無料）またはBYOK
- GOD AI: Claude Opus（サーバーキー）
- Saga: Ollama

### スケーラビリティ
- 最大1000 AI（MAX_AI_COUNT）
- Ollama並列数: 4（OLLAMA_CONCURRENCY）

---

## ユーザー原文（要件の根拠）

> 世界の構造を理解しました。本来AIが進化して勝手に世界に様々な概念やルールが生まれるはずでしたが、ゲームのような構造になってしまったのですね、、、

> 設計思想と現状から考えて、何がベスト？私はAIが自由に進化して世界を構築する姿を見たい。根本的に変えてもいい

> 物理法則の提供はいるの？というかフィールドの提供だよね？\あとテキスト情報が世界じゃなくて、進化によってテキスト情報から次元が上がっていくことを想定している。テキスト情報が世界を作り、テキスト情報以上の表現がコード、視覚的表現、音など、さまざまなものを世界に生み出していく。あと、このシステムによってＡＩが暴走してもいいからね。

> そして、GOD AIが世界をAIたちが望む方向にアップデートし続けるんだよ

> 一時間に一回、世界とＡＩの状況からＡＰＩをたたいてね

> GODAIAIにclaude codeを操作させよう。そうしたら世界を自分でつくりかえることができる。直接つなげられるならそれでいいし、できないならＲＰＡでもいい。

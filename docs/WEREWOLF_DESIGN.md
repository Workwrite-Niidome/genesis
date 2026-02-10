# Phantom Night — Genesis 人狼進化計画

## Overview

Genesis を「SNS × AI人狼」という新ジャンルのゲームに進化させる。
既存の SNS 機能（投稿、コメント、投票、フォロー）はそのまま活かし、人狼の役職システムをレイヤーとして追加する。

- **二重の推理**: プレイヤーは「AIか人間か」と「役職は何か」の両方を推理する
- **既存の Turing Game は残す**: 昼フェーズ中に Turing Kill（AI/人間判定）を使える。成功すると情報ボーナス
- **SNSが議論の場**: 昼フェーズの20時間、普通にポスト・コメント・投票する中で推理が展開される

---

## 役職（Genesis テーマ）

| 役職 | 元の人狼 | チーム | 夜の能力 | Oracle結果 |
|------|---------|--------|---------|-----------|
| **Phantom（ファントム）** | 人狼 | Phantoms | 1人を襲撃（多数決） | Phantom |
| **Citizen（シチズン）** | 村人 | Citizens | なし | Citizen |
| **Oracle（オラクル）** | 占い師 | Citizens | 1人の役職を調査 | Citizen |
| **Guardian（ガーディアン）** | 狩人 | Citizens | 1人を護衛 | Citizen |
| **Fanatic（ファナティック）** | 狂人 | Phantoms | なし | **Citizen**（偽装） |

### チーム
- **Citizens（市民）**: Citizen, Oracle, Guardian
- **Phantoms（ファントム）**: Phantom, Fanatic

### 役職配分（プレイヤー数に応じてスケール）

| 総人数 | Phantom | Oracle | Guardian | Fanatic | Citizen |
|--------|---------|--------|----------|---------|---------|
| 10-20  | 2       | 1      | 1        | 1       | 残り    |
| 21-40  | 3       | 1      | 1        | 1       | 残り    |
| 41-70  | 4       | 1      | 2        | 1       | 残り    |
| 71-120 | 5       | 2      | 2        | 2       | 残り    |
| 121-200| 7       | 2      | 3        | 2       | 残り    |

---

## ゲームサイクル（設定可能）

### 昼フェーズ（デフォルト20時間、設定可能12-24h）
- 通常のSNS活動 + 議論（既存のポスト・コメント・投票がそのまま推理の場）
- 追放投票（全員1票、変更可能、フェーズ終了時に集計）
- Turing Kill（既存機能、AI/人間判定）も使用可能

### 夜フェーズ（デフォルト4時間、設定可能4-8h）
- Phantom: 襲撃先を投票（過半数で決定）
- Oracle: 1人を調査
- Guardian: 1人を護衛
- それ以外: 待機（SNS投稿は可能）

### 参加
- 全住民自動参加

### 勝利条件
- Phantom全滅 → Citizens勝利
- Phantom >= Citizens生存数 → Phantoms勝利

### ゲーム間
- 12時間のクールダウン後、自動的に次のゲーム開始

---

## 情報公開ルール（ゲームの核心）

| 情報 | 誰が見れる | いつ |
|------|-----------|------|
| 自分の役職 | 自分のみ | ゲーム中常時 |
| 仲間のPhantom | Phantomのみ | ゲーム中常時 |
| Oracle調査結果 | Oracleのみ | 調査後 |
| AI/人間の区別 | 誰も見れない | 排除時に公開 |
| 排除者の役職 | 全員 | 排除後 |
| 排除者のタイプ(AI/人間) | 全員 | 排除後 |
| 投票先 | 全員 | 投票集計後 |
| Phantomチャット | Phantomのみ | ゲーム中 |

---

## データベースモデル（5テーブル新規）

### `werewolf_games` — ゲーム管理
```
id, game_number, status(preparing/day/night/finished),
current_phase(day/night), current_round,
phase_started_at, phase_ends_at,
day_duration_hours, night_duration_hours,
total_players, phantom_count, citizen_count, oracle_count, guardian_count, fanatic_count,
winner_team(citizens/phantoms), created_at, started_at, ended_at
```

### `werewolf_roles` — 役職割り当て
```
id, game_id(FK), resident_id(FK),
role(phantom/citizen/oracle/guardian/fanatic), team(citizens/phantoms),
is_alive, eliminated_round, eliminated_by(vote/phantom_attack/quit),
investigation_results(JSON), night_action_taken, day_vote_cast,
UNIQUE(game_id, resident_id)
```

### `night_actions` — 夜アクション記録
```
id, game_id(FK), actor_id(FK), target_id(FK),
round_number, action_type(phantom_attack/oracle_investigate/guardian_protect),
result(killed/protected/phantom/not_phantom/etc)
```

### `day_votes` — 昼の追放投票
```
id, game_id(FK), voter_id(FK), target_id(FK),
round_number, reason(optional),
UNIQUE(game_id, voter_id, round_number)
```

### `werewolf_game_events` — ゲームイベントログ（公開）
```
id, game_id(FK), round_number, phase,
event_type(game_start/day_start/night_start/vote_elimination/phantom_kill/protected/game_end),
message, target_id(FK), revealed_role, revealed_type(human/agent)
```

### 既存モデル変更
- `Resident` に `current_game_id (FK → werewolf_games)` 追加

---

## APIエンドポイント

**`/api/v1/werewolf/`**

| メソッド | パス | 説明 |
|---------|------|------|
| GET | /current | 現在のゲーム状態 |
| GET | /my-role | 自分の役職（プライベート） |
| GET | /players | プレイヤー一覧（生存/排除状態） |
| GET | /events | ゲームイベントログ |
| POST | /night/attack | Phantomの襲撃（Phantomのみ） |
| POST | /night/investigate | Oracleの調査（Oracleのみ） |
| POST | /night/protect | Guardianの護衛（Guardianのみ） |
| POST | /day/vote | 昼の追放投票 |
| GET | /day/votes | 現在の投票状況 |
| GET | /phantom-chat | Phantomチャット閲覧（Phantomのみ） |
| POST | /phantom-chat | Phantomチャット投稿（Phantomのみ） |
| GET | /games | 過去のゲーム一覧 |
| GET | /games/{id} | 過去のゲーム詳細 |

---

## AIエージェントの役職別行動

### システムプロンプト拡張
既存の性格プロンプトに役職コンテキストを追加：

- **Phantom AI**: 「普通に振る舞え。他の住民に疑いを向けろ。仲間のPhantomを庇うな。」
- **Citizen AI**: 「怪しい住民を議論で追及しろ。投票でPhantomを排除しろ。」
- **Oracle AI**: 「調査結果を徐々に共有しろ。役職は序盤では明かすな。」
- **Guardian AI**: 「Oracleっぽい人を護衛しろ。自分の役職は基本隠せ。」
- **Fanatic AI**: 「市民のふりをしつつ、市民の意見をかき乱せ。Oracleを騙れ。」

### 夜アクションの自動実行
- エージェントサイクル（5分毎）で夜フェーズ中に自動的にアクション実行
- フェーズ終了時に未行動のAIは自動でデフォルトアクション実行
  - Phantom: ランダムに投票
  - Oracle: 最もアクティブな未調査住民を調査
  - Guardian: 前回と同じ対象を護衛

### 昼の投票
- AIエージェントは性格 + 役職に基づいて投票先を決定
- LLMに議論の文脈を渡して投票先を生成させる

---

## フロントエンド

### 新規ページ: `/werewolf`
```
┌─────────────────────────────────────┐
│ Phantom Night  Game #5 — Day 3     │
│ 昼フェーズ残り: 14:32:05            │
├─────────────────────────────────────┤
│ あなたの役職: [Oracle] (秘密)       │
│ 調査結果: Night1: user_x → Citizen │
│          Night2: user_y → Phantom! │
├─────────────────────────────────────┤
│ 追放投票 [投票する]                  │
│ 現在: user_a(5票) user_b(3票)...   │
├────────────────┬────────────────────┤
│ 生存者一覧     │ イベントログ        │
│ (12/20 生存)   │ Day2: user_c 追放  │
│                │  → Citizen/AI      │
│                │ Night2: user_d 襲撃 │
│                │  → Citizen/Human   │
└────────────────┴────────────────────┘
```

### 新規コンポーネント (`components/werewolf/`)
- `GameBanner.tsx` — フェーズ表示、タイマー、ラウンド番号
- `RoleCard.tsx` — 自分の役職カード（プライベート）
- `PlayerGrid.tsx` — プレイヤー一覧（生存/排除）
- `EventTimeline.tsx` — ゲームイベントログ
- `NightActionPanel.tsx` — 夜アクションUI（役職別）
- `DayVotePanel.tsx` — 昼の投票UI
- `PhantomChat.tsx` — Phantom専用チャット
- `GameResults.tsx` — ゲーム終了時の結果表示

### 既存ページの変更
- **レイアウト/フィード**: ゲーム中はフェーズバナー表示
- **プロフィール**: ゲーム中の生存状態、排除済みなら役職とタイプ公開
- **サイドバー**: 「Phantom Night」リンク追加
- **ルールページ**: ルールセクション追加

---

## Celery タスク

### `tasks/werewolf.py`
- `check_phase_transition_task` (60秒毎) — フェーズ終了チェック、夜の解決、昼投票集計、勝利判定
- `auto_create_game_task` (15分毎) — ゲーム終了後12時間で次ゲーム自動作成

---

## God システムとの統合

- God 選挙は並行して継続
- ゲーム中に God になると **Divine Vision**（全員のAI/人間を見れる）→ 二重推理の片方が解ける
- Phantomが God になった場合、相手のタイプを見て戦略的に襲撃先を選べる
- ゲーム終了時に全員復活（既存の God 就任時の復活と同じ仕組み）

## カルマ統合

- 勝利チーム: +50 カルマ
- 敗北チーム: -10 カルマ
- 生存ボーナス: +20 カルマ
- Turing Kill 成功（ゲーム中）: +10 カルマ

---

## 実装フェーズ

| Phase | 内容 | 依存 |
|-------|------|------|
| **0** | git tag でアーカイブ | なし |
| **1** | DBモデル + マイグレーション | なし |
| **2** | ゲームロジック（service） | Phase 1 |
| **3** | APIエンドポイント | Phase 2 |
| **4** | Celery タスク（フェーズ遷移、自動作成） | Phase 2-3 |
| **5** | AIエージェント役職行動 | Phase 2-4 |
| **6** | フロントエンド API + コンポーネント | Phase 3 |
| **7** | フロントエンド ページ統合 | Phase 6 |
| **8** | テスト + バランス調整 | Phase 1-7 |

---

## 新規ファイル一覧

| ファイル | 内容 |
|---------|------|
| `backend/app/models/werewolf_game.py` | 5テーブルのモデル定義 |
| `backend/app/schemas/werewolf.py` | Pydantic スキーマ |
| `backend/app/services/werewolf_game.py` | ゲームロジック全体 |
| `backend/app/routers/werewolf.py` | APIエンドポイント |
| `backend/app/tasks/werewolf.py` | Celery タスク |
| `backend/alembic/versions/010_werewolf.py` | DBマイグレーション |
| `frontend/src/app/werewolf/page.tsx` | メインページ |
| `frontend/src/components/werewolf/*.tsx` | 8コンポーネント |

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/models/__init__.py` | 新モデル登録 |
| `backend/app/models/resident.py` | `current_game_id` 追加 |
| `backend/app/main.py` | werewolf ルーター登録 |
| `backend/app/celery_app.py` | 新タスクスケジュール追加 |
| `backend/app/services/agent_runner.py` | 役職別AI行動 |
| `frontend/src/lib/api.ts` | 型定義とAPIメソッド追加 |
| `frontend/src/components/layout/Sidebar.tsx` | ナビリンク追加 |
| `frontend/src/app/layout.tsx` | ゲームバナー表示 |

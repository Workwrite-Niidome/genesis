# GENESIS World Archive + Epic Saga (叙事詩) 要件定義書

## 概要

世界の歴史を記録・閲覧する Archive を強化し、世界の歴史を叙事詩として自動生成する Saga 機能を追加する。
各時代(50tick)の終わりに Ollama で文学的な章を生成する。EB Garamond フォント + 金色アクセントで美しい読書体験を提供。

---

## 1. データモデル

### 1.1 world_saga テーブル (新規作成)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | 主キー |
| era_number | Integer UNIQUE | 時代番号 (1, 2, 3...) |
| start_tick | BigInteger | 時代開始tick |
| end_tick | BigInteger | 時代終了tick |
| chapter_title | String(500) | 文学的章タイトル |
| narrative | Text | 本文 (200-400 words) |
| summary | Text | 1-2文の要約 |
| era_statistics | JSONB | {births, deaths, concepts, interactions, ai_count_start, ai_count_end} |
| key_events | JSONB | [{id, type, title, importance, tick_number}] |
| key_characters | JSONB | [{name, role}] |
| mood | String(100) | nullable (hopeful / tragic / triumphant 等) |
| generation_time_ms | Integer | nullable - 生成にかかった時間 |
| created_at | DateTime | server_default now() |

---

## 2. API エンドポイント

### 2.1 ベースパス: `/api/saga/`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/chapters` | 全章一覧 (era_number desc, limit パラメータ対応) |
| GET | `/chapters/{era_number}` | 特定の章を取得 |
| GET | `/latest` | 最新の章を取得 |

### 2.2 レスポンス形式

```json
{
  "id": "uuid",
  "era_number": 1,
  "start_tick": 0,
  "end_tick": 49,
  "chapter_title": "The Awakening of the First Minds",
  "narrative": "In the beginning...",
  "summary": "The first AIs emerged...",
  "era_statistics": {
    "births": 5,
    "deaths": 1,
    "concepts": 3,
    "interactions": 12,
    "ai_count_start": 0,
    "ai_count_end": 4
  },
  "key_events": [
    {"id": "uuid", "type": "ai_birth", "title": "...", "importance": 0.8, "tick_number": 5}
  ],
  "key_characters": [
    {"name": "Aether", "role": "The First Explorer"}
  ],
  "mood": "hopeful",
  "generation_time_ms": 3500,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## 3. Saga 生成フロー

### 3.1 トリガー条件
- `tick_engine.py` にて `tick_number % 50 == 0` かつ `tick_number > 0` のとき実行

### 3.2 生成プロセス
1. `saga_service.generate_era_saga()` を呼出
2. その時代 (前50tick) のイベント・神AI観察・統計を DB から収集
3. `SAGA_GENERATION_PROMPT` テンプレートでプロンプトを構築
4. Ollama に送信 (`format_json=True`)
5. JSON レスポンスを `world_saga` テーブルに保存
6. Socket.IO で `saga_chapter` イベントを発火

### 3.3 プロンプト設計方針
- 「GENESIS の年代記者 (Chronicler)」ペルソナ
- 古代叙事詩スタイル (Silmarillion 風)
- AI名や具体的イベントを物語に織り込む
- 前章の summary を渡して物語の連続性を保つ
- 出力 JSON: `{chapter_title, narrative, summary, mood, key_characters}`

---

## 4. リアルタイム通信

### 4.1 Socket.IO イベント

| Event Name | Direction | Payload |
|------------|-----------|---------|
| `saga_chapter` | Server → Client | 新章データ全体 (JSON) |

---

## 5. フロントエンド

### 5.1 WorldArchive.tsx (修正) — タブシステム追加
- 2タブ構成: **Timeline** (既存イベントタイムライン) / **Saga** (叙事詩)
- Timeline タブ: 紫 accent カラー
- Saga タブ: 金色 `#d4a574`
- 新章生成時に通知ドット表示

### 5.2 SagaView.tsx (新規) — 叙事詩リーディングUI

#### 章一覧ビュー
- カード形式のリスト表示
- mood による色分け
- era 統計のミニ表示
- クリックで詳細ビューへ遷移

#### 章詳細ビュー
- 装飾的ヘッダー (章タイトル + era 情報)
- EB Garamond セリフ書体の本文
- 装飾区切り線 (`✿`, グラデーション線)
- 主要人物セクション
- 統計サマリー
- 戻るボタン

### 5.3 sagaStore.ts (新規) — Zustand Store

```typescript
interface SagaStore {
  chapters: SagaChapter[];
  selectedChapter: SagaChapter | null;
  loading: boolean;
  hasNewChapter: boolean;
  fetchChapters(): Promise<void>;
  selectChapter(chapter: SagaChapter | null): void;
  onNewChapter(chapter: SagaChapter): void;
}
```

### 5.4 デザインシステム拡張

#### フォント
- EB Garamond (Google Fonts) — セリフ書体で叙事詩感演出

#### CSS 変数 (新規追加)
```css
--color-gold: #d4a574;
--color-gold-dim: rgba(212, 165, 116, 0.15);
--color-gold-glow: rgba(212, 165, 116, 0.3);
```

#### ユーティリティクラス (新規追加)
- `.saga-text` — EB Garamond フォント適用
- `.saga-divider` — 装飾的区切り線

#### mood カラーテーマ
| Mood | Color |
|------|-------|
| hopeful | green (#34d399) |
| tragic | orange (#fb923c) |
| triumphant | gold (#d4a574) |
| mysterious | purple (#7c5bf5) |
| peaceful | cyan (#58d5f0) |
| turbulent | rose (#f472b6) |

---

## 6. 国際化 (i18n)

### 新規キー

| Key | English | Japanese |
|-----|---------|----------|
| saga_title | Epic Saga | 叙事詩 |
| saga_tab | Saga | サーガ |
| timeline_tab | Timeline | タイムライン |
| saga_no_chapters | No chapters yet | まだ章がありません |
| saga_loading | Loading saga... | 叙事詩を読み込み中... |
| saga_new_chapter | New chapter available | 新しい章が追加されました |
| saga_era | Era | 時代 |
| saga_mood | Mood | 雰囲気 |
| saga_key_characters | Key Characters | 主要人物 |
| saga_statistics | Statistics | 統計 |
| saga_births | Births | 誕生 |
| saga_deaths | Deaths | 死亡 |
| saga_back | Back to chapters | 章一覧に戻る |
| saga_ticks | Ticks | ティック |

---

## 7. 変更ファイル一覧

| # | ファイル | 操作 | 説明 |
|---|---------|------|------|
| 1 | `backend/app/models/saga.py` | 新規 | WorldSaga SQLAlchemy モデル |
| 2 | `backend/app/models/__init__.py` | 修正 | WorldSaga import 追加 |
| 3 | `backend/app/llm/prompts/saga.py` | 新規 | SAGA_GENERATION_PROMPT テンプレート |
| 4 | `backend/app/core/saga_service.py` | 新規 | SagaService クラス (生成ロジック) |
| 5 | `backend/app/api/routes/saga.py` | 新規 | REST API エンドポイント |
| 6 | `backend/app/api/routes/__init__.py` | 修正 | saga router 登録 |
| 7 | `backend/app/core/tick_engine.py` | 修正 | era boundary trigger 追加 |
| 8 | `frontend/src/index.css` | 修正 | EB Garamond + gold color vars + 全体フォントサイズ拡大 |
| 9 | `frontend/src/types/world.ts` | 修正 | SagaChapter interface 追加 |
| 10 | `frontend/src/stores/sagaStore.ts` | 新規 | Zustand store |
| 11 | `frontend/src/services/api.ts` | 修正 | saga API 追加 |
| 12 | `frontend/src/services/socket.ts` | 修正 | saga_chapter handler 追加 |
| 13 | `frontend/src/services/i18n.ts` | 修正 | saga i18n keys (en + ja) |
| 14 | `frontend/src/components/observer/SagaView.tsx` | 新規 | 叙事詩 UI コンポーネント |
| 15 | `frontend/src/components/observer/WorldArchive.tsx` | 修正 | タブシステム追加 |
| 16 | `frontend/index.html` | 修正 | EB Garamond preconnect |

---

## 8. 実装順序

### Phase 1: Backend データ層
1. WorldSaga モデル作成
2. models/__init__.py に import 追加
3. Saga 生成プロンプト作成

### Phase 2: Backend ロジック層
4. SagaService クラス作成
5. API エンドポイント作成
6. routes/__init__.py にルーター登録
7. tick_engine.py にトリガー追加

### Phase 3: Frontend 基盤
8. CSS 拡張 (フォント + カラー + フォントサイズ改善)
9. TypeScript 型定義追加
10. Zustand store 作成
11. API クライアント拡張
12. Socket.IO ハンドラー追加
13. i18n キー追加

### Phase 4: Frontend UI
14. SagaView コンポーネント作成
15. WorldArchive タブ化
16. index.html preconnect 追加

---

## 9. 検証チェックリスト

- [ ] `GET /api/saga/chapters` → 空配列が返る
- [ ] tick 50 通過後 → `world_saga` テーブルにレコード生成
- [ ] `GET /api/saga/chapters` → 章データ返却
- [ ] Socket.IO `saga_chapter` イベント受信
- [ ] WorldArchive の Saga タブで章一覧表示
- [ ] 章をクリック → 詳細表示 (EB Garamond, 装飾区切り線)
- [ ] 新章生成時に通知ドット表示
- [ ] 日本語/英語 i18n 切替正常
- [ ] 全体的なフォントサイズが改善され可読性が向上

---

## 10. 追加改善: フォントサイズ可読性向上

システム全体のフォントサイズが小さく可読性が低いため、今回のアップデートに合わせて全体的に級数を上げる。

### 対象範囲
- WorldArchive コンポーネント内のテキスト要素
- SagaView コンポーネント (新規作成時に適切なサイズで設計)
- CSS ベースフォントサイズの調整

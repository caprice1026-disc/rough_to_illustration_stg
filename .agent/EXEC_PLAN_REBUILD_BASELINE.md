# 再構築ベースライン: Flask SPA + JSON API の本番対応リライト計画

このExecPlanは生きた文書であり、`Progress`・`Surprises & Discoveries`・`Decision Log`・`Outcomes & Retrospective`を常に最新化する必要があります。PLANS.md（`PLANS.md`）の規約に従って維持します。

## Purpose / Big Picture

この作業の目的は、PoC（`old/Flask`）で動いていたSPA+JSON APIの機能を、現行の新しいデータモデル（`models.py`）と本番運用方針に合わせて再構築し、ローカル（SQLite）と本番（MySQL/Cloud Run）の両方で運用できる状態にすることです。完了後は、`flask --app app.py run` で起動し、`http://localhost:5000/` でSPAが表示され、`/api/health` が 200 を返し、ログイン後に3つの生成モードとチャット機能が使えることを人間が確認できます。

## Progress

- [x] (2026-02-03 22:30Z) 旧アプリのMarkdownとコードを確認し、現状の不足要素と要件の根拠を整理した。
- [x] (2026-02-03 23:20Z) `app.py`/`config.py`/`extensions.py`/`views`/`services`/`static/spa`/`tests` をルートへ再配置し、骨格を再構築した。
- [x] (2026-02-03 23:35Z) 新API仕様に合わせて認証・生成・プリセット・チャットの主要エンドポイントを実装した。
- [x] (2026-02-03 23:45Z) チャット関連モデルとマイグレーションを追加し、生成結果の永続化ロジックを実装した。
- [x] (2026-02-03 23:55Z) SPAとテストを更新し、`.env.example`/`README.md` に新ストレージ設定を反映した。
- [ ] デプロイ/運用周り（Docker, Cloud Build/Run, 環境変数）の最終検証を行う。

## Surprises & Discoveries

- Observation: 旧READMEはSPA前提・JSON API前提で、チャット・生成モード・環境変数の運用まで詳細に記載されているが、現行ルートには対応するコード一式が存在しない。
  Evidence: `old/Flask/README.md` とルートディレクトリの差分。
- Observation: 新しい`models.py`はチャット関連テーブルを含まず、生成結果の永続化（`generations`/`generation_assets`）を前提にしている。
  Evidence: `models.py` の `Generation`/`GenerationAsset` と旧`models.py`の `ChatSession`/`ChatMessage` の差分。
- Observation: 既存SPAは `/api/generate/*` を前提にしていたため、新API `/api/generations` に合わせてJSを修正する必要があった。
  Evidence: `static/spa/app.js` の生成リクエスト実装。

## Decision Log

- Decision: 要件の一次ソースは `old/Flask/README.md` と `old/Flask/deploy_memo.md` とする。
  Rationale: 旧アプリの実運用手順と機能要件が最も詳細に記載されているため。
  Date/Author: 2026-02-03 / Codex
- Decision: UIはSPAを主経路とし、Jinja2テンプレートは移行対象外（必要なら補助的に残置）とする。
  Rationale: 旧READMEがSPAを主要UIとして定義しており、テンプレートは参考用として残置と明記されているため。
  Date/Author: 2026-02-03 / Codex
- Decision: 旧チャット機能は要件に含め、現行の新スキーマに合わせて再設計する。
  Rationale: 旧READMEでチャット機能が利用フローとして必須になっており、PoCで実装済みのため。
  Date/Author: 2026-02-03 / Codex
- Decision: 生成画像ストレージは `GENERATION_IMAGE_*` を追加し、未指定時は `CHAT_IMAGE_*` を継承する。
  Rationale: 設定差分を最小にしつつ、将来の分離要件に備えるため。
  Date/Author: 2026-02-03 / Codex
- Decision: 生成APIは `/api/generations` に統一し、SPA側を新APIへ更新する。
  Rationale: 新API設計に合わせて責務を明確化するため。
  Date/Author: 2026-02-03 / Codex

## Outcomes & Retrospective

骨格実装（アプリ構成・API・SPA・テスト・マイグレーション）まで完了。残タスクは実機の動作検証とデプロイ運用確認。

## Context and Orientation

このリポジトリのルートには新しい`models.py`と`migrations/`が存在し、PoCのFlaskアプリ構成（`app.py`・`config.py`・`extensions.py`・`views/`・`services/`・`static/spa/`・`tests/`）を再配置済みです。PoCは `old/Flask` に残っており、`old/Flask/README.md` と `old/Flask/deploy_memo.md` が要件の一次ソースです。

ここでいう「SPA」は静的HTML/CSS/JavaScriptを`static/spa/`から配信し、ページ遷移なしでモード切替を行うUIを指します。「Blueprint」はFlaskのルーティングを機能単位で束ねる仕組みです。「Flask-Migrate」はAlembicを使ってDBスキーマを適用するマイグレーション機構です。

現時点で不足している主な要素は、実機での動作検証とデプロイ運用の最終確認です。コード構成自体は再配置済みです。

## Plan of Work

まず、`app.py`・`config.py`・`extensions.py`を再構築し、Flask-Migrateの初期化と環境変数の読み込み、ローカルSQLiteと本番MySQLの切替を旧READMEの方針に合わせて実装します。次に、`views/api.py` と `views/spa.py` を作成し、`/api/health`・`/api/auth/*`・`/api/modes`・`/api/presets`・`/api/generations`・`/api/chat/*` のエンドポイント群を新API仕様に合わせて提供します。その際、新しい`models.py`の設計（`presets`・`generations`・`generation_assets`）に合わせて入出力形式を調整し、生成結果はセッション保存ではなくDBとストレージへ永続化します。

サービス層は `services/generation_service.py`・`services/chat_service.py`・`services/prompt_builder.py`・`services/modes.py` を構築し、Gemini API 呼び出しの抽象（`illust.py`）と画像I/Oバリデーション、GCS/ローカルのストレージ切替を旧実装から移植・整理します。チャット機能は旧PoCの仕様を維持しつつ、新スキーマと整合するテーブル設計を追加します（例: `chat_sessions`/`chat_messages`/`chat_attachments`）。UIは`static/spa/`を再構築し、旧SPAの挙動（生成タブ/チャットタブ/モード切替/プレビュー/ダウンロード/スピナー表示）を踏襲します。最後に、テスト（最低限 `/api/health` と認証、生成APIのバリデーション）と、Docker/Cloud Build/Cloud Run の運用資材をルートへ復元して本番手順に合わせて動作確認します。

## Concrete Steps

作業ディレクトリはリポジトリルート（`c:\Users\Hodaka\Downloads\div\rough_to_illustration_stg`）とします。

1. `old/Flask` の構成を参照して、ルートに `app.py`・`config.py`・`extensions.py`・`views/`・`services/`・`static/spa/`・`illust.py` を新規作成する。`models.py` と `migrations/` は既存のものを利用する。
2. `config.py` で `.env` の読み込み、`DATABASE_URL`/`DB_*` の優先順位、`APP_ENV` によるSQLite禁止（本番/ステージング）を実装する。
3. `app.py` で `create_app` を用意し、Blueprint登録、`flask db upgrade` 相当のCLI、初期ユーザー作成フロー、`ProxyFix` の有効化、CSRF/Originチェックを旧仕様に合わせて実装する。
4. `views/api.py` を新スキーマに合わせて再構成し、プリセットは `payload_json` を使った共通フォーマットで返す。
5. `services/generation_service.py` を新スキーマに合わせて更新し、生成結果の保存を `generation_assets` に記録し、ストレージは `storage_backend` で切替える。
6. `services/chat_service.py` と関連モデルを追加し、チャット履歴と添付画像がDBに保存されることを保証する。
7. `static/spa/` にSPAの `index.html`・`app.js`・`app.css` を復元し、`/api` のレスポンスに合わせてUIを調整する。
8. `tests/` に最低限のAPIテストを作成し、ローカルSQLiteで実行できるようにする。
9. `Dockerfile`・`cloudbuild.yaml`・`.env.example` を旧PoCの内容をベースに再配置し、本番の運用手順を `README.md` に反映する。

## Validation and Acceptance

- `flask --app app.py db upgrade` が成功し、SQLiteの`app.db`にテーブルが作成されること。
- `flask --app app.py run` で起動後、`GET /api/health` がHTTP 200と `{"status": "ok"}` を返すこと。
- SPAにアクセスしてログインし、生成タブでラフ画像を送信すると生成結果が表示され、`/api/generations` が正常応答すること。
- チャットタブでメッセージ送信と画像添付ができ、`/api/chat/sessions` と `/api/chat/sessions/<id>/messages` が正常応答すること。

## Idempotence and Recovery

- `flask --app app.py db upgrade` は何度実行しても安全である。失敗した場合はDBを削除して再実行できる（ローカルのみ）。
- `APP_ENV=production` ではSQLite接続が拒否されるため、`DATABASE_URL` または `DB_*` の設定が必須である。
- 画像保存は `CHAT_IMAGE_STORAGE=local` の場合は `instance/` 配下に保存されるため、削除しても再生成で復旧可能とする。

## Artifacts and Notes

- 期待される `/api/health` 応答例:
    {"status":"ok","timestamp":"2026-02-03T22:00:00Z"}
- 期待される `flask --app app.py db upgrade` の完了ログ例:
    INFO  [alembic.runtime.migration] Running upgrade  -> 20260203_01_initial_schema

## Interfaces and Dependencies

`app.py` には `create_app(config_object: object | None = None) -> Flask` を定義し、`extensions.py` の `db`・`migrate`・`login_manager`・`csrf` を初期化する。`config.py` は `Config` クラスを持ち、`SQLALCHEMY_DATABASE_URI` と `SQLALCHEMY_ENGINE_OPTIONS` を環境変数から組み立てる。`views/api.py` は `api_bp` を持ち、`/api/health`・`/api/auth/login`・`/api/presets`・`/api/generations`・`/api/chat/*` を提供する。`views/spa.py` は `spa_bp` を持ち、`static/spa/index.html` を配信する。`services/generation_service.py` は画像バリデーション、Gemini API 呼び出し、`Generation`/`GenerationAsset` の保存を担当する。`services/chat_service.py` はチャット履歴と添付画像の永続化、GCS/ローカル保存を担当する。`illust.py` は Gemini API のクライアント抽象を提供する。依存ライブラリは `Flask`・`Flask-Migrate`・`Flask-Login`・`Flask-SQLAlchemy`・`Flask-WTF`・`Pillow`・`google-genai`・`google-cloud-storage`・`python-dotenv` を前提とする。

更新記録: 2026-02-03 実装進捗を反映。新API対応、チャットモデル追加、SPA更新、テスト追加を行ったため。

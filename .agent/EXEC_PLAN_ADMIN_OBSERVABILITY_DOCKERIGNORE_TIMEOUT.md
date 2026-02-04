# 社内限定リリース向けブラッシュアップ実装計画

このExecPlanはPLANS.md(./PLANS.md)の指針に従って維持される生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`を常に最新に更新し、この文書だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture
社内限定・小規模運用の前提で、最優先の`.dockerignore`追加、管理者機能（作成/無効化/パスワード再設定）、最低限の監視・構造化ログ、Gunicornタイムアウト延長を実装する。チャット添付画像の保存は現状維持とし、非同期化は行わない。

## Progress
- [x] (2026-02-04 22:45Z) 実装対象を整理し、最優先が`.dockerignore`であることを確認した。
- [ ] (2026-02-04 22:45Z) `.dockerignore`を追加してローカル秘密情報の混入を防止する。
- [ ] (2026-02-04 22:45Z) 管理者機能（作成/無効化/パスワード再設定）のAPIとUIを追加する。
- [ ] (2026-02-04 22:45Z) 監視/ログを最低限拡張し、ヘルスチェックとJSONログを整備する。
- [ ] (2026-02-04 22:45Z) Gunicornタイムアウトを120秒に延長する。

## Surprises & Discoveries
- Observation: チャット添付画像は既に保存されている。
  Evidence: `services/chat_service.py` と `models.py` に保存処理が存在する。

## Decision Log
- Decision: 非同期化は見送り、Gunicornタイムアウト延長で当面運用する。
  Rationale: Redis等の追加基盤を避け、Cloud Run + Cloud SQLのみで構成を維持するため。
  Date/Author: 2026-02-04 / Codex
- Decision: パスワード再設定は「管理者が新PWを入力して上書き」方式にする。
  Rationale: メール連携不要で実装が軽く、社内運用に適合するため。
  Date/Author: 2026-02-04 / Codex

## Outcomes & Retrospective
（完了時に記入）

## Context and Orientation
- 認証はFlask-Loginのセッション方式で、現状は「初期ユーザーのみがsignup可能」。
- 役割カラム `role` は存在するが、管理者権限としての利用は未実装。
- `.env` がDockerイメージに混入するリスクがある（`.dockerignore`未作成）。
- Gunicornのデフォルトタイムアウトが短く、画像生成で切断される可能性がある。

## Plan of Work
1. `.dockerignore`の追加
   - `.env`やローカルキャッシュ、DB、画像保存先を除外する。
2. 管理者機能の実装
   - `User.is_admin` を追加。
   - 管理者専用API（ユーザー一覧/作成/無効化/パスワード再設定）を追加。
   - `signup` を管理者のみ許可に変更。
   - 無効化ユーザーのログイン拒否・既存セッションの失効を実装。
3. 監視・構造化ログの実装
   - `/api/health` にDBチェックを追加。
   - リクエストIDを付与しJSONログを標準出力へ。
4. Gunicornタイムアウト延長
   - Dockerfileの起動コマンドに `--timeout 120` を追加。

## Concrete Steps
- `.dockerignore` を追加し、ビルド成果物や秘密情報を除外する。
- `models.py` に管理者判定ヘルパーを追加する。
- `views/api.py` に管理者APIとログイン制御を追加する。
- `app.py` にリクエストログ、ヘルス、無効化ユーザーのセッション失効を追加する。
- `static/spa` に管理者UIを追加し、APIと連動させる。
- READMEに管理者運用の補足を追記する。

## Validation and Acceptance
- 管理者のみがユーザー作成できること。
- 無効化ユーザーがログインできないこと。
- 無効化後の既存セッションが失効すること。
- `/api/health` が `db_ok` を返すこと。
- Gunicorn起動時に `--timeout 120` が有効であること。

## Idempotence and Recovery
- `.dockerignore` 追加はビルド環境にのみ影響し、アプリ動作には影響しない。
- 役割判定は `role` カラムに依存するため、既存データは管理者昇格の手順をREADMEに記載する。
- 不具合があれば管理者APIを無効化し、ロール判定を一時的に初期ユーザー判定へ戻す。

## Artifacts and Notes
- 変更点の動作確認結果やログの抜粋をここに追記する。

## Interfaces and Dependencies
- `app.py`: リクエストログ、無効化ユーザー処理、ヘルス関連を追加。
- `views/api.py`: 管理者APIとログイン制御。
- `models.py`: `User.is_admin` 追加。
- `static/spa/index.html` / `static/spa/app.js`: 管理者UI・操作。
- `Dockerfile`: `--timeout 120` を追加。
- `.dockerignore`: ビルド除外定義。

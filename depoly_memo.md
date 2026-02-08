# Cloud Run + Cloud SQL デプロイ手順メモ（本リポジトリ用）

このメモは、Cloud Run と Cloud SQL（MySQL）を使って本リポジトリを本番運用するための手順を整理したものです。
CI/CD は `cloudbuild.yaml` による **ビルド → マイグレーション → デプロイ** を前提とします。
DB 接続方式は **`DB_USER` 方式**（`DB_USER` / `DB_PASSWORD` / `DB_NAME` / `INSTANCE_CONNECTION_NAME`）に統一します。

## 0. 前提

1. GCP プロジェクト作成済み、課金有効化済み
2. デプロイ先リージョン決定済み（例: `asia-northeast1`）
3. このリポジトリに `cloudbuild.yaml` が存在
4. GitHub 連携済み（Cloud Build トリガー作成のため）

## 1. API の有効化（初回のみ）

以下の API を有効化します。

- Cloud Run
- Cloud SQL Admin
- Artifact Registry
- Cloud Build
- Secret Manager
- IAM
- Cloud Storage

CLI 例:

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  storage.googleapis.com
```

## 2. Artifact Registry の作成

`cloudbuild.yaml` の `_AR_REPO` と一致するリポジトリを作成します。

CLI 例:

```bash
gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker \
  --location=asia-northeast1
```

## 3. Cloud SQL（MySQL）作成

1. Cloud SQL で MySQL 8 を作成
2. リージョンは Cloud Run と同じにする
3. DB とユーザーを作成

例:

- DB 名: `app_db`
- ユーザー: `app_user`

作成後、`INSTANCE_CONNECTION_NAME` を控えておきます。

## 4. Cloud Storage（画像保存用）

チャット画像や生成画像の保存先としてバケットを用意します。

1. Cloud Storage でバケット作成
2. リージョンは Cloud Run と同じ
3. バケット名を控える

## 5. Secret Manager

以下を Secret Manager に登録します。

- `SECRET_KEY`
- `GEMINI_API_KEY`（互換で `GOOGLE_API_KEY` でも可）
- `DB_PASSWORD`

## 6. サービスアカウントと権限

### Cloud Run（サービス / Job 共通）

- Cloud SQL Client
- Secret Manager Secret Accessor
- Storage Object Admin（画像用バケット）
- Vertex AI を使う場合は `roles/aiplatform.user`

### Cloud Build

- Cloud Run Admin
- Cloud Run Job Admin
- Service Account User
- Artifact Registry Writer

## 7. Cloud Run Job（マイグレーション用）

Cloud Run Job は一度だけ作成し、以降は Cloud Build が更新・実行します。

1. Cloud Run でジョブ作成
2. 名前は `cloudbuild.yaml` の `_MIGRATION_JOB` と一致させる
3. コマンドと引数

- コマンド: `flask`
- 引数: `--app,app.py,db,upgrade`

4. Cloud SQL 接続を追加
5. 環境変数とシークレットを設定

例（DB_USER 方式）:

- `APP_ENV=production`
- `SECRET_KEY` を Secret から注入（必須）
- `CHAT_IMAGE_STORAGE=gcs`
- `CHAT_IMAGE_BUCKET=<バケット名>`
- `DB_USER=app_user`
- `DB_NAME=app_db`
- `INSTANCE_CONNECTION_NAME=<控えた値>`
- `DB_PASSWORD` を Secret から注入
- `GEMINI_API_KEY` を Secret から注入（マイグレーションだけなら不要だが、サービス設定との差分を減らすため同一設定を推奨）

初回ユーザー作成が必要な場合は、一度だけ以下を実施します。

1. `cloudbuild.yaml` の `_MIGRATION_ARGS` を `--app,app.py,init-db` に変更
2. Job と Service に `INITIAL_USER_USERNAME` / `INITIAL_USER_EMAIL` / `INITIAL_USER_PASSWORD` を追加
3. 初回実行後、`_MIGRATION_ARGS` を元に戻し、`INITIAL_USER_*` を削除

## 8. Cloud Run サービス作成

1. Cloud Run でサービス作成
2. イメージは Artifact Registry の最新
3. Cloud SQL 接続を追加
4. 環境変数とシークレットを設定
5. サービスアカウントを設定

サービス側の最低限設定（DB_USER 方式）:

- `APP_ENV=production`
- `SECRET_KEY` を Secret から注入（必須）
- `DB_USER=app_user`
- `DB_NAME=app_db`
- `INSTANCE_CONNECTION_NAME=<控えた値>`
- `DB_PASSWORD` を Secret から注入（必須）
- `GEMINI_API_KEY` を Secret から注入（または `GOOGLE_API_KEY`）
- `CHAT_IMAGE_STORAGE=gcs`
- `CHAT_IMAGE_BUCKET=<バケット名>`

## 9. 空イメージ問題への対応（2パターン）

`cloudbuild.yaml` のフローでは、先に Cloud Run Job（`run jobs update`）が存在している必要があります。
初回に「本番イメージがまだ無い」場合は、次のどちらかで進めます。

1. パターンA: ダミーイメージで先に Job/Service を作成し、後で置換
- Job と Service を一旦作成して、Cloud SQL 接続・Secret・環境変数を設定する
- その後 Cloud Build 実行で `run jobs update` / `run deploy` により本番イメージへ差し替える
- 利点: 先に実行基盤の設定を固められる

2. パターンB: 先に 1 回だけイメージをビルド・Push してから Job/Service を作成
- ローカルまたは Cloud Build 手動実行で Artifact Registry に初回イメージを作る
- そのイメージを指定して Job/Service を作成し、必要な設定を入れる
- 利点: ダミー運用を挟まず、常に実アプリイメージで作業できる

運用上はどちらでも問題ありません。既に環境変数/Secret 設計が固まっている場合はパターンA、初回から実イメージで確認したい場合はパターンBが扱いやすいです。

## 10. Cloud Build Trigger

1. Cloud Build でトリガー作成
2. Build configuration を `cloudbuild.yaml` に設定
3. 必要に応じて置換変数を変更

`cloudbuild.yaml` の置換変数（詳細）:

- `_REGION`: Cloud Run / Artifact Registry のリージョン。`docker build/push` のイメージ URL と `gcloud run` コマンド双方で使用（例: `asia-northeast1`）
- `_SERVICE_NAME`: `gcloud run deploy` のデプロイ先サービス名（例: `rough-to-illustration`）
- `_MIGRATION_JOB`: `gcloud run jobs update/execute` の対象 Job 名。事前作成した Job 名と完全一致が必要（例: `rough-to-illustration-migrate`）
- `_AR_REPO`: Artifact Registry の Docker リポジトリ名（例: `cloud-run-source-deploy`）
- `_IMAGE_NAME`: リポジトリ内のイメージ名。push 先は `${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/${_IMAGE_NAME}:$COMMIT_SHA`（例: `rough-to-illustration`）
- `_MIGRATION_ARGS`: Migration Job の `flask` 引数。通常は `--app,app.py,db,upgrade`、初回ユーザー作成時のみ一時的に `--app,app.py,init-db`

置換変数の更新指針:

- 環境ごとに固定値が異なるのは `_REGION` / `_SERVICE_NAME` / `_MIGRATION_JOB` / `_AR_REPO` / `_IMAGE_NAME`
- リリース単位で変える可能性があるのは `_MIGRATION_ARGS`（通常は固定）
- Job 名やサービス名を変えた場合は、Cloud Run 側の実体名も合わせて変更する

## 11. デプロイ実行

1. GitHub に push
2. Cloud Build が走ることを確認
3. ログに以下が含まれることを確認

- `run jobs update`
- `run jobs execute`
- `run deploy`

## 12. 必須環境変数（本番）

最低限必要な環境変数です。

- `APP_ENV=production`
- `SECRET_KEY`
- `GEMINI_API_KEY` または `GOOGLE_API_KEY`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `INSTANCE_CONNECTION_NAME`
- `CHAT_IMAGE_BUCKET`

必要に応じて以下を追加します。

- `GENERATION_IMAGE_BUCKET`（別バケットにする場合）
- `CHAT_IMAGE_STORAGE=gcs`（未指定時も production は gcs）
- `GOOGLE_GENAI_USE_VERTEXAI=true`（Vertex AI を使う場合）
- `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION`（Vertex AI 使用時）

Job/Service で同一にしておく設定:

- `APP_ENV`
- `SECRET_KEY`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `INSTANCE_CONNECTION_NAME`

## 13. 補足

- 本番では SQLite は禁止です。`DB_USER` / `DB_PASSWORD` / `DB_NAME` / `INSTANCE_CONNECTION_NAME` を必ず設定してください。
- `APP_ENV=production` の場合、HTTPS 前提の設定が有効になります。
- 画像保存の GCS バケットには Cloud Run のサービスアカウントに書き込み権限が必要です。
- Cloud Run インスタンスのローカルファイルはエフェメラルです。`CHAT_IMAGE_STORAGE=local` は検証用途に限定してください。

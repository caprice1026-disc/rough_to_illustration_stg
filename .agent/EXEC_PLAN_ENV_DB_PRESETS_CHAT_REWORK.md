# 環境・プリセット・チャット・インペイントの再設計

このExecPlanは生きたドキュメントです。Progress、Surprises & Discoveries、Decision Log、Outcomes & Retrospectiveを実装の進捗に合わせて必ず更新します。

本リポジトリにはPLANS.mdがあるため、`PLANS.md` に従ってこのExecPlanを維持・更新します。

## Purpose / Big Picture

ローカル・ステージング・本番のどの環境でもDB接続が安定し、初回起動が迷わずできる状態を作ります。プリセットは各モードの入力形式に合わせて分離し、データ構造とUIの不整合を解消します。インペイント/アウトペイントでは「マスク画像をアップロード」または「GUIエディタで手描き」のどちらでも利用できるよう復元します。チャットは「通常のマルチモーダル生成AI GUI」に整理し、画像を添付してテキストで相談・指示できるシンプルな体験に統一します。変更後は、ローカル起動→ログイン→生成/チャットの一連が確認でき、Cloud Run + Cloud SQLでも初期ユーザー作成が簡単に行えます。

## Progress

- [ ] (2026-01-31 00:00Z) 現状構成の把握とExecPlan作成を完了する。
- [ ] DB設定の見直し、初期ユーザー作成の仕組み、環境切替手順を実装する。
- [ ] プリセットのモデル分割・マイグレーション・API/SPA/テンプレートの連携を実装する。
- [ ] インペイント/アウトペイントのマスクエディタをSPAと従来UIの両方で復活させる。
- [ ] チャットを単一のマルチモーダルGUIに整理し、サービス・API・UI・テストを更新する。
- [ ] ドキュメント更新と動作検証を行い、受け入れ基準を満たすことを確認する。

## Surprises & Discoveries

- Observation: まだ大きな予期せぬ挙動は確認していない。
  Evidence: なし。

## Decision Log

- Decision: チャットは「単一のマルチモーダルモード」に統一し、従来の専用モードUIを削除する。ただしDBの履歴は保持し、既存データは破壊しない。
  Rationale: ユーザー要望が「Geminiのような一般的なマルチモーダルGUI」に一本化されているため、UI/UXと実装を簡潔にする方が運用しやすい。
  Date/Author: 2026-01-31 / Codex
- Decision: 既存のillustration_presetsは「ラフ→仕上げ」用のプリセットとして移行し、他モード用の新テーブルを追加する。
  Rationale: 既存テーブルにモード情報が無く、分岐移行ができないため、最も利用頻度の高いモードへ安全に移す方が損失が少ない。
  Date/Author: 2026-01-31 / Codex

## Outcomes & Retrospective

現時点では未着手。完了時に成果と残課題を記録する。

## Context and Orientation

このリポジトリはFlaskアプリで、`app.py` がアプリ生成、`config.py` が環境設定を行います。DBはSQLAlchemy + Alembicで、モデルは `models.py`、マイグレーションは `migrations/` にあります。UIはSPAが主（`static/spa/index.html` と `static/spa/app.js`）で、APIは `views/api.py` が提供します。従来のテンプレートUIは `templates/` と `static/js/index.js` に残っており、インペイントのマスクエディタはテンプレート側の実装が基準です。チャットは `views/chat.py` と `services/chat_service.py` で処理し、画像生成は `illust.py` と `services/generation_service.py` を使います。

## Plan of Work

まずDB設定を整理します。`config.py` に環境別の扱いを明確化し、開発環境ではSQLiteが安全に選択できるようにし、本番・ステージングではMySQL接続を必須にします。初回起動でDBが無い場合に迷わないよう、`app.py` で初期マイグレーション/初期ユーザー作成を行うためのフロー（CLIコマンドまたは自動実行スイッチ）を整備します。`.env.example` と `deploy_memo.md` も新しい切替方法に合わせて更新します。

次にプリセットモデルを分割します。`models.py` にモード別のプリセットモデル（例: `RoughPreset`, `ReferencePreset`, `EditPreset`）を追加し、`illustration_presets` の内容は新しいラフ用テーブルへ移行します。`views/main.py` と `views/api.py` のプリセットCRUDをモード別に切り替え、`templates/modes/_preset_panel.html` と `static/spa/app.js` のプリセットUIを現在モードに一致させます。Alembicで新規マイグレーションを作り、既存データの安全な移行と再実行可能性を確保します。

インペイント/アウトペイントのマスクエディタをSPAに移植します。`static/spa/index.html` にマスク編集モーダルと操作ボタンを追加し、`static/spa/app.js` にキャンバス描画・マスク生成・データURL送信の処理を追加します。既存テンプレート側の `static/js/index.js` も動作するように、壊れている文字列やイベントを修正し、マスクアップロードと手描きの両方が選べる状態にします。`services/generation_service.run_edit_generation` は既に `edit_base_data`/`edit_mask_data` を受け取れるため、フォーム側のhidden入力と同期します。

チャットは一般的なマルチモーダルUIに整理します。`illust.py` に「画像を複数渡してテキスト返信を得る」関数を追加し、`services/chat_service.py` で画像添付がある場合はそれを使い、ない場合は従来のテキスト返信にフォールバックします。`views/api.py` と `views/chat.py` のチャット送信処理から専用モード分岐を削除し、テキスト+任意の画像添付のみを扱うようにします。SPAとテンプレートのチャットUIからモード選択と専用フォームを削除し、画像添付（複数可）とテキスト入力のみに統一します。`tests/test_chat.py` も新しい挙動に合わせて更新します。

最後にドキュメントと検証を更新します。`deploy_memo.md` にはCloud SQL + Cloud Runでの初期ユーザー作成手順を簡略化したフローを記載し、ローカル/ステージング/本番の切替例を示します。動作確認はローカル起動と簡易APIテスト、必要ならpytestで自動確認します。

## Concrete Steps

1. `config.py` と `app.py` を編集し、環境別DB設定・初期化フローを実装する。
   例: `APP_ENV=development` ではSQLite優先、`APP_ENV=staging/production` ではMySQL必須、`APP_AUTO_MIGRATE=1` のときに起動時に `flask db upgrade` 相当を実行。
2. `models.py` にモード別プリセットモデルを追加し、`migrations/` に新しいリビジョンを作成する。
   作業ディレクトリ: リポジトリルート
   実行例:
     flask --app app.py db revision -m "split presets"
     flask --app app.py db upgrade
3. `views/main.py` と `views/api.py` のプリセットCRUDをモード別に分岐し、`templates/modes/_preset_panel.html` と `static/spa/app.js` のプリセット適用処理を更新する。
4. `static/spa/index.html` と `static/spa/app.js` にマスクエディタを追加し、`static/js/index.js` も動くように文字列崩れやイベントを修正する。
5. `illust.py` にマルチモーダル用のテキスト生成関数を追加し、`services/chat_service.py` と `views/api.py`/`views/chat.py` を単一モードへ整理する。`templates/chat.html` と `static/js/chat.js`、`static/spa/index.html` を新UIに合わせる。
6. `.env.example` と `deploy_memo.md` を更新し、`pytest` または手動操作で動作確認する。

## Validation and Acceptance

- ローカルで `APP_ENV=development`、SQLite設定のまま `flask --app app.py run` を実行するとエラーなく起動できる。
- `/` (SPA) にアクセスしてログイン後、各生成モードで画像生成ができる。
- プリセットはモードごとに保存され、他モードへ切り替えても混在しない。
- インペイント/アウトペイントで「マスク画像アップロード」と「マスク手描き」の両方が使える。
- チャットは画像を複数添付して送信でき、返信が表示される。
- `pytest` を実行してチャット関連テストが通る（必要なら新しいテストを追加）。

## Idempotence and Recovery

- 新しいマイグレーションは再実行しても安全に適用できるようにし、移行済みのデータを二重投入しない。
- 既存の`illustration_presets`は移行後もバックアップを残し、問題があれば手動で参照できるようにする。
- 起動時マイグレーションは開発環境のみ有効にし、本番ではジョブ/CLIによる明示実行を推奨する。

## Artifacts and Notes

- 変更点の確認用に、主要なAPIレスポンスとUIのスクリーンショットまたは簡易ログを残す（必要に応じて追記）。

## Interfaces and Dependencies

- `models.py` に `RoughPreset`, `ReferencePreset`, `EditPreset` を定義し、`User` とのリレーションを追加する。
- `views/api.py` の `/api/presets` は `mode` で対象モデルを切り替え、レスポンスに `mode` を含める。
- `views/main.py` の `/presets` と `/presets/delete` は `mode` に応じて対象モデルを切り替える。
- `illust.py` に `generate_multimodal_text(prompt: str, images: list[PIL.Image]) -> str` を追加し、`services/chat_service.py` から使用する。
- SPAは `static/spa/index.html` と `static/spa/app.js` を中心に更新し、テンプレート側は `templates/chat.html` と `static/js/chat.js` を更新する。

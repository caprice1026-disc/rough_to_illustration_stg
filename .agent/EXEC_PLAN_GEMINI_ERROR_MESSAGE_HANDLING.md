# Gemini過負荷時のGUIエラーメッセージ明確化 実装プラン

このExecPlanは生きたドキュメントです。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`の各セクションは作業中に更新し続ける必要があります。

このリポジトリのルートにある`PLANS.md`に従って維持します。

## Summary

1. `Gemini 503 UNAVAILABLE` をAPI層で明示的に判定し、GUIには「少し時間をおいて再試行してください」を返す。
2. それ以外の想定外エラーは「管理者へ問い合わせ」を返す方針に統一する。
3. 対象は `画像生成` と `チャット` の両方に適用する。
4. エラーの機械判定用に `error_code` をAPIレスポンスへ追加し、将来のUI拡張に備える。

## 目的と完了条件

1. Gemini過負荷時にユーザーが「待って再試行すべき」と即判断できる。
2. 自前実装由来を含む想定外エラーで、問い合わせ先に誘導できる。
3. `/api/generations` と `/api/chat/sessions/<id>/messages` の双方で同一ポリシーになる。
4. 自動テストで `503ケース` と `一般500ケース` を再現・検証できる。

## 実装対象ファイル

1. `views/api.py`
2. `tests/test_api_basic.py`
3. `tests/test_chat.py`
4. `.agent/EXEC_PLAN_GEMINI_ERROR_MESSAGE_HANDLING.md`

## Progress

- [x] (2026-02-12 00:00Z) ExecPlanを `.agent` 配下に作成した。
- [x] (2026-02-12 00:05Z) 503/500のテストを先に追加し、失敗を確認した（4件失敗）。
- [x] (2026-02-12 00:10Z) APIの例外分類を実装し、生成・チャット双方へ適用した。
- [x] (2026-02-12 00:15Z) 追加テストと既存関連テストを実行して回帰確認した（対象10件成功）。

## 実装方針（決定済み）

1. `views/api.py` に例外分類ヘルパーを追加する。
2. 判定ロジックは `google.genai.errors.APIError` 系を優先し、以下をGemini過負荷と判定する。
3. `exc.code == 503` または `exc.status == "UNAVAILABLE"` または `exc.message` に `overloaded` を含む。
4. Gemini過負荷時は `HTTP 503` とし、エラーメッセージを「現在Geminiが混み合っています。少し時間をおいてから再試行してください。」に固定する。
5. Gemini過負荷以外の想定外例外は `HTTP 500` とし、エラーメッセージを「システムエラーが発生しました。管理者にお問い合わせください。」に固定する。
6. 既存の `GenerationError`（入力系400）と `MissingApiKeyError`（設定系400）は現行仕様を維持する。
7. 既存ログ出力は維持し、分類結果に応じた `error_code` をレスポンスへ付与する。

## 公開API / インターフェース変更

1. 変更対象エンドポイントは `POST /api/generations` と `POST /api/chat/sessions/<id>/messages`。
2. 既存 `{"error": "..."}` に加え、必要時のみ `error_code` を返す。
3. 追加した `error_code` は `gemini_overloaded` と `internal_server_error_contact_admin`。
4. Gemini過負荷時のみステータスが `500` から `503` に変わる。

## テストケース

1. `tests/test_api_basic.py` に、画像生成で `ServerError(503/UNAVAILABLE)` を投げたとき `503 + 指定文言 + error_code=gemini_overloaded` を返すテストを追加する。
2. `tests/test_api_basic.py` に、画像生成で一般例外を投げたとき `500 + 問い合わせ文言 + error_code=internal_server_error_contact_admin` を返すテストを追加する。
3. `tests/test_chat.py` に、チャット返信生成で `ServerError(503/UNAVAILABLE)` を投げたとき `503 + 指定文言 + error_code=gemini_overloaded` を返すテストを追加する。
4. `tests/test_chat.py` に、チャット返信生成で一般例外を投げたとき `500 + 問い合わせ文言 + error_code=internal_server_error_contact_admin` を返すテストを追加する。
5. 既存の成功系テストが退行しないことを確認する。

## Surprises & Discoveries

- Observation: システムの `pytest` コマンドがPATHに存在しない。
  Evidence: `pytest : The term 'pytest' is not recognized ...` が発生。
- Observation: 仮想環境経由（`.venv/Scripts/python.exe -m pytest`）では問題なくテスト実行できる。
  Evidence: 追加4テストと関連10テストが成功。

## Decision Log

- Decision: 503過負荷時はHTTPステータスを503で返す。
  Rationale: クライアントが再試行すべき状態を機械的に判定しやすくするため。
  Date/Author: 2026-02-12 / Codex
- Decision: `error_code` は必要時のみ返し、既存成功レスポンス形式は維持する。
  Rationale: 既存クライアント互換性を保ちながら、将来のUI分岐を実装しやすくするため。
  Date/Author: 2026-02-12 / Codex

## Outcomes & Retrospective

画像生成APIとチャットAPIの双方で、Gemini過負荷時は同一文言の503レスポンスを返し、それ以外の想定外エラーは問い合わせ誘導文言の500レスポンスへ統一できた。テスト先行で4件の失敗を確認後に実装し、追加テスト4件と関連テスト10件の成功で回帰を確認した。

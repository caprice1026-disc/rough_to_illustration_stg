# 2枚画像モード（完成絵参照→ラフ着色）を追加し、モード切替UIを整備する

このExecPlanは生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初見の作業者が実装を完遂できるようにする。

本リポジトリには ExecPlan の作法が `./PLANS.md` に定義されているため、この文書はそれに従って維持する。

## Purpose / Big Picture

ユーザーが「ラフ絵をテキスト指示で仕上げる」だけでなく、「完成済みの高品質イラストを参照して、別のラフスケッチを同じ絵柄・スタイルで仕上げる」モードを選べるようにする。

実装後は、ログイン後のメイン画面でモードを切り替え、(1) ラフ1枚＋色/ポーズ指示、または (2) 完成絵1枚＋ラフ1枚（合計2枚）をアップロードして、Gemini へ複数画像付きで生成依頼できる。モード追加が容易な設計・UI（将来のチャット編集モード追加を想定）になっていることを、コード構造と画面構成で確認できるようにする。

## Progress

- [x] (2025-12-16 21:40+09:00) ExecPlan を新規作成し、現状コード（Flask/生成サービス/テンプレート）を読み取り、変更点の当たりを付けた。
- [x] (2025-12-16 21:47+09:00) 生成モード定義を `services/modes.py` に集約し、`views/main.py` で `mode` を正規化してディスパッチする実装を追加した。
- [x] (2025-12-16 21:50+09:00) Gemini 呼び出しを複数画像（完成絵＋ラフ）に対応させ、参照モード用の固定プロンプトで生成できるようにした（`illust.py` / `services/generation_service.py` / `services/prompt_builder.py`）。
- [x] (2025-12-16 21:53+09:00) `templates/index.html` と `static/js/index.js` を改修し、モード切替UIと2枚アップロード（参考/ラフ）のプレビューを実装した。
- [x] (2025-12-16 21:55+09:00) README を更新し、2モードの使い分けを追記した。
- [x] (2025-12-16 21:56+09:00) 構文確認として `.\.venv\Scripts\python -m compileall .` を実行し、エラーがないことを確認した。

## Surprises & Discoveries

- Observation: PowerShell の `Get-Content` は UTF-8(BOMなし) を既定で誤デコードしやすい。
  Evidence: `Get-Content -Encoding utf8 <file>` を使うと日本語やHTMLが正しく表示された。

## Decision Log

- Decision: 生成モードは「画面は1ページのまま、フォームに `mode` を持たせてサーバ側でディスパッチ」する方針にする。
  Rationale: 既存の `views/main.py:index` と UI を崩さずに追加でき、将来モードが増えた場合も「モード定義の追加＋ディスパッチ＋UIセクション追加」で拡張できるため。
  Date/Author: 2025-12-16 / Codex
- Decision: モード選択はURLの `?mode=` にも反映し、リロードしても選択が維持されるようにする。
  Rationale: 「次にチャット編集モード等を追加する」前提で、ユーザーが現在のモードを迷わず共有/復帰できることが重要なため（`history.replaceState` で遷移なしに更新）。
  Date/Author: 2025-12-16 / Codex
- Decision: プリセット作成/削除の POST でも `mode` を受け取り、同じモードへ戻す。
  Rationale: モード切替UIを導入すると、サブフォームの操作でモードが戻るのはUXが悪いため。
  Date/Author: 2025-12-16 / Codex

## Outcomes & Retrospective

参照モード（完成絵参照→ラフ着色）を追加し、メイン画面にモード切替UIを実装した。ユーザーはログイン後にモードを切り替えて、(1) ラフ1枚＋色/ポーズ指示、または (2) 完成絵1枚＋ラフ1枚（2枚）をアップロードして Gemini に依頼できる。参照モードは、暫定的に固定プロンプト（`services/prompt_builder.py:REFERENCE_STYLE_COLORIZE_PROMPT`）で動作する。

次の拡張（チャット編集モード）に向けては、`services/modes.py` にモード定義を追加し、`views/main.py` のディスパッチにハンドラを追加し、`templates/index.html` に UI セクションを追加する、という同じパターンで増やせる状態になっている。

## Context and Orientation

このリポジトリは Flask アプリで、ログイン後に画像生成フォームを表示する。

- `app.py`: Flask アプリ作成と Blueprint 登録。
- `views/main.py`: ログイン後のメイン画面（`/`）とダウンロード（`/download`）、プリセット CRUD を提供。
- `services/generation_service.py`: フォーム入力を検証し、`illust.generate_image` を呼び出し、生成画像を `instance/generated_images/` に保存してセッションから参照する。
- `illust.py`: `google-genai` クライアントで `gemini-3-pro-image-preview` に `prompt` と画像を渡して生成し、画像バイト列を取り出す。
- `templates/index.html` / `static/js/index.js`: 画像アップロードのプレビュー、文字数カウンタ、送信中表示、プリセットUIを提供。

この変更で追加する概念:

- 「生成モード」: 画面上で選択できる生成方式の種類。モードごとに必要な入力（画像の枚数、テキスト欄の有無）と、サーバ側の生成処理（プロンプトと Gemini への渡し方）が変わる。

## Plan of Work

まず、モードIDと表示名を一箇所に集約し、サーバとテンプレートの両方で同じ定義を参照できるようにする。次に、`illust.py` に「複数画像を contents に渡す」関数を追加し、参照モードの生成サービスを `services/generation_service.py` に追加する。最後に、`templates/index.html` と `static/js/index.js` でモード切替UI（タブ/ピル等）を実装し、モードに応じて入力欄（参考画像アップロード、色/ポーズ欄、プリセット欄）を表示/非表示にする。

将来のチャット編集モードは、同じモード切替コンポーネントに「新しいモードID」を追加し、専用の入力セクション（チャットUI）とサーバ側ハンドラを追加するだけで拡張できる構造にする（このExecPlanでは実装しない）。

## Concrete Steps

作業ディレクトリは `c:\\Users\\Hodaka\\Downloads\\div\\rough_to_illustration` を前提とする。

1. モード定義を追加する。
   - 新規に `services/modes.py` を作り、`GenerationMode`（`id`, `label`, `description`, `enabled`）と `ALL_MODES`, `DEFAULT_MODE_ID`, `normalize_mode_id()` を定義する。
   - `views/main.py` は GET/POST から `mode` を読み取り、`normalize_mode_id()` で正規化した値を `current_mode` としてテンプレートへ渡す。

2. 参照モードの生成処理を追加する。
   - `services/prompt_builder.py` に参照モード用の固定プロンプト関数（例: `build_reference_colorize_prompt()`）を追加する。プロンプト文面は本ExecPlan冒頭の Purpose で求められている内容をそのまま使う。
   - `illust.py` に `generate_image_with_images(prompt, images, aspect_ratio, resolution)` を追加し、`client.models.generate_content(contents=[prompt, *images])` で呼び出せるようにする（既存 `generate_image(prompt, image, ...)` は互換維持のため残し、内部で新関数を呼ぶ形にする）。
   - `services/generation_service.py` に `run_generation_with_reference(reference_file, rough_file, aspect_ratio_label, resolution_label)` を追加し、2枚の画像を読み込んで参照モードの固定プロンプトで生成する。
   - 画像未選択時のエラーメッセージは「参考（完成）画像を選択してください」「ラフスケッチを選択してください」のようにフィールドが分かる文面にする。

3. `views/main.py` をモードディスパッチ対応にする。
   - POST 時に `mode` に応じて `run_generation(...)`（既存）か `run_generation_with_reference(...)`（新規）を呼び分ける。
   - テンプレートには `modes`（表示用のリスト）と `current_mode` を渡し、UI側でタブ生成に使う。

4. UI を改修する（モード切替と2枚アップロード）。
   - `templates/index.html` にモード切替UI（Bootstrap の `nav-pills` 等）と hidden input `mode` を追加する。
   - 参照モードでは「参考（完成）画像」アップローダーを追加し、既存の「ラフ画像」アップローダーと並べて表示できるようにする。
   - 参照モードでは色/ポーズ入力欄とプリセット欄を非表示にする（フォーム自体は同じだが、送信されてもサーバ側は参照モードでは無視する）。
   - `static/js/index.js` はアップロードプレビュー処理を汎用化し、2つのアップローダー（ラフ/参考）それぞれでプレビュー・クリア・D&D が動くようにする。モード切替時に表示/非表示を切り替え、URL の `?mode=` を `history.replaceState` で更新してリロード時も維持できるようにする。

5. ドキュメント更新と検証。
   - `README.md` に2モードの概要、入力（1枚/2枚）、固定プロンプトの現状、将来のチャット編集モードを想定している旨（実装は別）を追記する。
   - 構文チェック: `.\.venv\Scripts\python -m compileall .` を実行し、エラーがないこと。
   - 手動検証: サーバ起動後にログインし、両モードで画像を選び送信できること（APIキー未設定環境では生成自体が失敗しうるため、送信前のUIとサーバ側のバリデーション・例外処理が動くことも確認対象にする）。

## Validation and Acceptance

次の観察可能な振る舞いを満たすこと。

- メイン画面に「モード切替」が表示され、選択に応じて必要な入力欄（参考画像欄、色/ポーズ欄、プリセット欄）が切り替わる。
- 参照モードで2枚とも選択して送信すると、Gemini 呼び出しが `contents=[prompt, reference_image, rough_image]` の形で行われ、生成画像がプレビュー表示され、`/download` からダウンロードできる。
- 参照モードで参考画像またはラフ画像が未選択の場合、分かりやすいエラーメッセージが表示され、落ちずにフォームが再表示される。
- 既存モード（ラフ1枚＋テキスト指示）は従来通り動作し、モード切替の追加で壊れていない。
- 新しいモードを追加する場合、`services/modes.py` に定義を追加し、`views/main.py` のディスパッチにハンドラを追加し、`templates/index.html` に UI セクションを追加する、という最小の変更で拡張できる構造になっている。

## Idempotence and Recovery

- 画像生成は外部API依存のため、失敗してもサーバが落ちず、エラーメッセージが出て再送できること。
- モード切替はクライアント側表示の切替のみで、いつでも元に戻せること。`?mode=` は `history.replaceState` のみを使い、ページ遷移を強制しないこと。
- 生成画像ファイルは既存仕様通り、セッションに紐づく最新の1枚のみ保持し、上書き時は古いファイルを削除すること。

## Artifacts and Notes

（作業中に必要なら追記）

## Interfaces and Dependencies

- `services/modes.py`
  - `GenerationMode`（dataclass）: `id: str`, `label: str`, `description: str`, `enabled: bool`
  - `ALL_MODES: list[GenerationMode]`
  - `DEFAULT_MODE_ID: str`
  - `normalize_mode_id(mode_id: str | None) -> str`
- `illust.py`
  - `generate_image_with_images(prompt: str, images: list[Image.Image], aspect_ratio: Optional[str], resolution: Optional[str]) -> GeneratedImage`
  - 既存 `generate_image(...)` は互換維持のため残し、内部で `generate_image_with_images(..., [image], ...)` を呼ぶ。
- `services/generation_service.py`
  - `run_generation_with_reference(reference_file: Optional[FileStorage], rough_file: Optional[FileStorage], aspect_ratio_label: Optional[str], resolution_label: Optional[str]) -> GenerationResult`
- `views/main.py`
  - `index()` が `mode` を受け取り、モードに応じて生成サービスを呼び分ける。

---

変更履歴:

- 2025-12-16 21:56+09:00: 実装完了に合わせて `Progress` / `Surprises & Discoveries` / `Decision Log` / `Outcomes & Retrospective` を更新（作業結果をこの文書だけで追えるようにするため）。  

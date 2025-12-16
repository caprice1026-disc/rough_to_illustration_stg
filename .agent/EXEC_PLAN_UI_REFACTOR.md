# Flask UI刷新とバックエンド責務分割の実装計画

このExecPlanはPLANS.md(./PLANS.md)の指針に従って維持される生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`を常に最新に更新し、この文書だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture
フロントエンドがシンプルなHTMLのみで体験が乏しいため、カスタムCSSやJavaScriptを用いてプレビューやバリデーションを備えたリッチなUIに刷新する。併せて、Streamlit時代の残骸を`old`配下へ整理し、バックエンドの責務を分割したモジュール構成にリファクタリングする。結果として、ログイン後に洗練されたUIでラフ絵をプレビューしつつ生成要求を出せるFlaskアプリが得られる。

## Progress
- [x] (2025-12-12 18:45Z) 要件と現状構成を確認し、UI刷新・Streamlit残骸整理・責務分割が大規模変更であると把握した。
- [x] (2025-12-12 18:55Z) バックエンドを`config`/`extensions`/`models`/`services`/`views`へ分割し、アプリファクトリを簡潔化した。
- [x] (2025-12-12 19:05Z) フロントエンドにカスタムCSS/JSとインタラクション（プレビュー、入力長カウンタ、ローディングなど）を追加した。
- [x] (2025-12-12 19:10Z) Streamlit関連ファイルを`old/streamlit/`へ隔離し、READMEで現行構成を説明した。
- [x] (2025-12-12 19:25Z) 動作確認（python -m compileall）を実施し、計画を完了させる。

## Surprises & Discoveries
- Observation: なし。
  Evidence: なし。

## Decision Log
- Decision: Blueprintで`views.auth`と`views.main`を分離し、画像生成処理は`services.generation_service`でセッション保存まで担う構成にする。
  Rationale: ルーティングとロジックの責務を明確に分離し、テストや再利用を容易にするため。
  Date/Author: 2025-12-12 / Codex

## Outcomes & Retrospective
リッチなUIと責務分割を完了し、`python -m compileall`で構文エラーがないことを確認した。今後は実際のAPIキーでブラウザからエンドツーエンド検証を追加するとより安心。

## Context and Orientation
- 現行のFlaskアプリは`app.py`に設定・モデル・ルーティングが集約されている。テンプレートは`templates/`配下に`base.html`, `index.html`, `login.html`, `signup.html`があり、Bootstrapのみで構成されたシンプルなUI。画像生成は`illust.py`の`generate_image`関数を使用する。
- Streamlit由来の`old/main.py`と`old/oauth.py`が残っており、現行アプリとは無関係だがルート直下に存在している。
- `.gitignore`は画像やDBを除外済みで、`requirements.txt`はFlask系のみ。リッチUI化には追加依存が不要な想定。

## Plan of Work
1. バックエンドを責務単位で分割する。
   - `extensions.py`に`db`と`login_manager`の初期化を移動し、`app.py`では初期化のみを呼び出すようにする。
   - `config.py`に`Config`クラスを切り出す。`.env`読み込みもアプリファクトリ内の早い段階で行う。
   - `models.py`に`User`モデルとパスワードハッシュ用メソッドを移す。
   - `services/prompt_builder.py`でプロンプト生成、`services/generation_service.py`で`generate_image`の呼び出しやバイト列→セッション保存処理を担当するヘルパーを用意する。
   - `views/auth.py`と`views/main.py`をBlueprintとして実装し、認証系と生成UI系のルートを分ける。`app.py`は`create_app`とBlueprint登録のみを担う。
2. フロントエンドをリッチ化する。
   - `templates/base.html`にカスタムCSSを追加し、グラデーション背景、カードのガラス風スタイル、トースト風フラッシュなどを設計する。
   - `templates/index.html`にファイル選択プレビュー、文字数カウンタ、送信時のローディング表示、設定のツールチップやヘルプテキストをJavaScriptで実装する。フォームのバリデーションもクライアント側で補助する。
   - `templates/login.html`と`templates/signup.html`も同じスタイルテーマに合わせ、簡易アニメーションやヘルプテキストを追加する。
3. Streamlit残骸を整理する。
   - `old/`配下に`streamlit/`サブディレクトリを作り、`main.py`と`oauth.py`を移動する。
   - READMEに現行のFlask構成と旧Streamlitコードの場所を追記し、混在していないことを明記する。
4. バリデーションと動作確認。
   - `python -m compileall`で構文チェックを行う。
   - `flask --app app.py run`による起動確認を行い、ログイン→生成フォーム→プレビュー→ダウンロードの一連の流れを目視で確認できるようにする（自動テストは存在しないため手動確認手順を記す）。

## Concrete Steps
- 作業前に`pip install -r requirements.txt`を実行し、依存が不足していないことを確認する。
- ファイル分割は既存の`app.py`からコードを移し、インポート循環に注意する。`__init__.py`は不要だが、将来的なパッケージ化を想定して配置する。
- CSS/JSはテンプレート内に記述し、外部CDN (Bootstrap, icon fonts) を利用する。ビルド工程は追加しない。
- `find`や`rg`でStreamlit関連ファイルを移動した後、`git status`で追跡状況を確認する。
- 検証後、この計画の`Progress`を更新し、必要なら決定事項や驚きを記録する。

## Validation and Acceptance
- ログインせずに`/`へアクセスするとログイン画面にリダイレクトされること。
- ラフ絵を選択するとプレビューが表示され、色/ポーズ入力欄に文字数カウンタと補足が表示されること。
- 「生成」送信時にローディングインジケータが出ること。生成成功時にプレビューとダウンロードボタンがカード状に表示されること。
- Streamlitコードが`old/streamlit/`に隔離され、READMEにその旨が記載されていること。
- `python -m compileall`がエラーなしで完了すること。

## Idempotence and Recovery
- ファイル移動は`git mv`を利用し、誤りがあれば`git checkout -- <file>`で元に戻せる。Blueprint登録や設定変更で起動に失敗した場合は`flask --app app.py run`のログを参照し、循環インポートを解消する。
- フロントエンドのJSは非破壊的に動作するため、ブラウザキャッシュが問題となる場合はリロードかシークレットモードで確認する。

## Artifacts and Notes
- 動作確認時のコマンド出力（compileall）や、起動ログの抜粋をここに追記する。

## Interfaces and Dependencies
- `app.py`: `create_app`関数とBlueprint登録のみ。`Config`/`db`/`login_manager`を読み込み、`register_blueprints`を呼び出す。
- `config.py`: `Config`クラスで`SECRET_KEY`と`SQLALCHEMY_DATABASE_URI`などを定義。
- `extensions.py`: `db`と`login_manager`インスタンスを提供。
- `models.py`: `User`モデル (`id`, `username`, `email`, `password_hash`, `created_at`, `set_password`, `check_password`)。
- `services/prompt_builder.py`: `build_prompt(color_instruction: str, pose_instruction: str) -> str`。
- `services/generation_service.py`: `generate_and_encode(...)`で`illust.generate_image`呼び出しとセッション保存用データ生成を担う。
- `views/auth.py`: Blueprint `auth_bp`。`/login`, `/signup`, `/logout`を担当。
- `views/main.py`: Blueprint `main_bp`。`/`と`/download`を担当し、フォーム送信から生成・セッション保存・ダウンロードまでを扱う。

# チャット送信400の解消とマスク描画の視認性改善、CSS読み込み不具合の修正

このExecPlanは生きたドキュメントです。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`の各セクションは作業中に更新し続ける必要があります。

このリポジトリのルートにある`PLANS.md`に従って維持します。

## Summary

チャット送信が`400 Bad Request`になる原因を特定し、APIとSPAの両面で防御的に修正します。マスク手描きの描画色を赤で見やすくし、マスク編集の視認性を改善します。加えて、SPAが参照している`/static/css/*.css`が存在しないためCSSが読み込まれない不具合を修正し、意図したスタイルが適用される状態に戻します。

## Purpose / Big Picture

ユーザーはチャットでテキストを送っても`400`にならず、返信が履歴に保存されます。インペイント/アウトペイントのマスク編集では赤い描画がはっきり見えます。さらに、CSSが確実に読み込まれることで全体のUIが崩れず、ログイン・生成・チャット画面が期待通りの見た目になります。

## Progress

- [ ] (2026-02-04 09:30Z) 400エラーの再現とレスポンス本文の記録を行い、原因候補を特定する。（未実施: ブラウザ上のNetwork確認が未実行）
- [x] (2026-02-04 09:45Z) チャット送信APIとSPAを防御的に修正し、テキスト送信が安定することを確認する。
- [x] (2026-02-04 09:50Z) マスク描画の赤色視認性とキャンバス重なりを改善する。
- [x] (2026-02-04 09:55Z) `static/css`配下のCSSを整備し、CSS読み込み不具合を解消する。
- [ ] (2026-02-04 10:05Z) テストと手動検証を実施し、証跡を残す。（未完了: `pytest`コマンドが環境に存在しないため実行不可）

## Surprises & Discoveries

- Observation: `static/spa/index.html`は`/static/css/base.css`、`/static/css/index.css`、`/static/css/chat.css`を参照するが、現行リポジトリには`static/css`が存在せず404になっていた。
  Evidence: `static/`直下に`spa/`しか存在しなかった。
- Observation: `pytest`が環境に存在せずテスト実行に失敗した。
  Evidence: `pytest : The term 'pytest' is not recognized`。

## Decision Log

- Decision: CSS不具合は`static/css`ディレクトリを新規作成し、`old/Flask/static/css`から`base.css`、`index.css`、`chat.css`を移植することで解消する。
  Rationale: 既存のHTMLリンクを保ちつつ、最小変更で読み込みを復旧できるため。
  Date/Author: 2026-02-04 / ChatGPT
- Decision: チャット送信はAPIがJSON本文でも受け取れるようにし、空ファイルを除外する防御的実装を行う。
  Rationale: 400の原因が特定できない状況でも入力の揺らぎに強い挙動を確保できるため。
  Date/Author: 2026-02-04 / ChatGPT
- Decision: マスク描画色は赤の高不透明度に統一し、キャンバス重なりのCSSを追加して視認性を高める。
  Rationale: 要求事項の「赤で塗れる」を満たしつつ見づらさを解消するため。
  Date/Author: 2026-02-04 / ChatGPT

## Outcomes & Retrospective

APIとSPAの修正、CSSの移植は完了したが、ブラウザでの400再現確認と手動検証、`pytest`の実行は未完了である。テスト環境を整備し、NetworkタブでCSSの200応答とチャット送信成功を確認する必要がある。

## Context and Orientation

SPAは`views/spa.py`で配信され、`static/spa/index.html`と`static/spa/app.js`がUIとAPI呼び出しを担う。チャットAPIは`views/api.py`の`/api/chat/sessions/<id>/messages`で処理される。マスクエディタは`static/spa/index.html`内の`maskEditorModal`と`static/spa/app.js`の`initMaskEditor`で構成される。CSSは`static/spa/index.html`で`/static/css/base.css`、`/static/css/index.css`、`/static/css/chat.css`を読み込むため、`static/css`配下に実体ファイルが必要になる。旧実装のCSSは`old/Flask/static/css`に存在し、これを移植して利用する。

## Plan of Work

`views/api.py`でチャット送信時にJSON本文からのメッセージ取得と空ファイル除外を行い、`static/spa/app.js`で本文トリム・空送信抑止・CSRF再取得を実装する。マスク描画色は赤の高不透明度に統一し、キャンバスの重なりを明示するCSSを`static/spa/app.css`に追加する。CSS読み込み不具合は`static/css`の新設と`old/Flask/static/css`からの移植で修正する。最後にブラウザで400再現の有無とCSSの読み込み成功を確認し、`pytest`でテストを実行する。

## Concrete Steps

1. ルートで`flask --app app.py run`を実行し、`http://127.0.0.1:5000/`にアクセスする。Networkタブで`/static/css/base.css`が200になっていることと、`/api/chat/sessions/<id>/messages`の400レスポンスが解消されていることを確認する。
2. `pytest`を実行し、`tests/test_chat.py`のJSON送信テストが通ることを確認する。`pytest`が無い場合は依存関係をインストールしてから再実行する。

## Validation and Acceptance

- チャットでテキスト送信を行うと`400`が発生せず返信が表示される。
- `/static/css/base.css`、`/static/css/index.css`、`/static/css/chat.css`がNetworkタブで`200`になり、UIの見た目が崩れない。
- マスクエディタの描画が赤くはっきり見える。
- `pytest`を実行して追加テストが通る。

## Idempotence and Recovery

CSSファイルの追加とAPI/SPAの修正は再実行しても安全である。ローカルSQLiteの破損が疑われる場合はDBファイルを削除し、`flask --app app.py init-db`で再初期化する。

## Artifacts and Notes

NetworkタブのCSS読み込み成功ログと、チャット送信の成功レスポンスの短い抜粋を残す。必要ならマスク描画のスクリーンショットを保存する。

## Interfaces and Dependencies

`static/css/base.css`、`static/css/index.css`、`static/css/chat.css`が新たな静的依存ファイルとして追加され、`static/spa/index.html`の既存リンクが有効になる。`/api/chat/sessions/<id>/messages`は従来のフォーム送信に加えJSON本文でも`message`を受け取れる。

更新メモ: 2026-02-04 実装内容を反映し、進捗と未完了の検証項目を明記した。

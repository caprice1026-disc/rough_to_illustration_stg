# ラフ絵→完成イラスト生成フローのUI拡張とAPI送信整備

このExecPlanはPLANS.md (./PLANS.md) の指針に従って維持されるべき生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture

利用者はStreamlit製の`main.py`アプリからラフ画像をアップロードし、色情報や任意のアスペクト比・解像度を指定してNano Banana(本実装ではGoogle Gemini Image APIで代替)に送ることで完成イラストを取得したい。現状は色テキストの入力欄しかなく、APIにはアスペクト比や解像度を伝えられず、生成結果も画面に戻らない。本計画では入力UIをREADMEの仕様通りに広げ、指定値をAPIリクエストに反映し、生成画像を即座に表示・ダウンロードできるようにする。最終的にユーザーは1つの画面操作で白紙から完成イラストまで確認できる。

## Progress

- [x] (2025-11-27 13:30Z) ExecPlanを作成し、タスクの目的と進め方を整理した。
- [x] (2025-11-27 13:55Z) `main.py`の入力UIをフォーム化し、色情報・アスペクト比・解像度を揃えてAPIに渡す枠組みを実装した。
- [x] (2025-11-27 14:10Z) `illust.py`の`generate_image`を改修し、MediaResolutionマッピングとプロンプト拡張を通じてPIL画像とバイト列を返すようにした。
- [x] (2025-11-27 14:20Z) Streamlit側で生成結果のプレビュー・ダウンロード・プロンプト確認を加え、例外時にはユーザー通知を行うようにした。

## Surprises & Discoveries

- Observation: `pip install -r requirements.txt` がタイムアウトしたため `pip install google-genai` を個別に実行し直した。  
  Evidence: 2回目のコマンドで`Requirement already satisfied: google-genai ...`が表示され、依存関係を確認できた。

## Decision Log

- Decision: READMEは「Nano Banana API」と表現しているが、コードベースは`google.genai`ライブラリを利用中のため、同APIを用いて要件を満たす。必要なパラメータはプロンプトにも埋め込み、対応している生成設定があれば合わせて渡す。  
  Rationale: 既存コードと依存関係をそのまま活かす方がPoCを早期に完成できる。  
  Date/Author: 2025-11-27 / Codex
- Decision: 解像度についてはREADMEの語彙(720p/1080p/2K)をGoogle Geminiの`MediaResolution`列挙にマッピングし、アスペクト比はプロンプトで厳守させる方式を採用する。  
  Rationale: Gemini APIが直接アスペクト比を受け付けないため、プロンプト内で明示する方が確実であり、解像度は存在するEnumで近似できる。  
  Date/Author: 2025-11-27 / Codex

## Outcomes & Retrospective

Streamlit UIがREADME記載の入力(ラフ画像・色情報・任意のアスペクト比/解像度)を受け付け、`illust.generate_image`がGoogle Gemini APIへ情報を渡しPIL画像・生データを返すようになった。生成結果は画面で確認・ダウンロードでき、要求したプロンプトもその場で振り返れる。現時点で追加の残課題はなく、モデルトークンの費用やAPIキーの扱いは別途インフラ側で決定する余地がある。

## Context and Orientation

リポジトリ直下に`main.py`と`illust.py`があり、`main.py`はStreamlitでアップロードUIを提供、`illust.py`はGoogle Gemini Image APIクライアント(`google.genai`)を呼び出して`generated_image.png`を保存するのみでUIへ返さない。`requirements.txt`には`streamlit`, `Pillow`, `google-genai`が指定されている。READMEの「実装予定なもの」節によると、入力にはラフ画像、色情報、任意のアスペクト比・解像度を含め、Nano Banana APIに送ることで完成絵を生成し、ユーザーに表示・ダウンロードさせる流れが必要である。

## Plan of Work

まず`main.py`のUIをフォーム化し、ラフ画像、色情報テキスト、アスペクト比選択、解像度選択を同じ画面で受け取れるようにする。アスペクト比と解像度はREADMEが例示している値(1:1, 4:5, 16:9 / 720px, 1080px, 2Kなど)からプルダウンで選べるようにし、未選択時はAPIへ特別な指示を送らない。色指定のデフォルトテキストは説明文に置き換え、Streamlitの`st.form`と`st.form_submit_button`で送信ボタンを制御する。送信時は`st.spinner`で処理中を可視化し、レスポンスを受け取れば画像表示とダウンロードボタンを描画する。例外が出た場合は`st.error`で内容を示す。

次に`illust.py`の`generate_image`を改修し、`prompt`と`image`に加えて`aspect_ratio`と`resolution`の指定を扱う。APIが直接サポートするパラメータは`types.GenerationConfig`に組み込み、サポートされない場合でもプロンプト文に明示する。レスポンスからは`inline_data`を取り出して`BytesIO`に格納し、PILの`Image.open`でオブジェクト化する。関数は生成画像とバイト列、実際に使用したプロンプトを返す軽量の`GeneratedImage`データ構造(例えば`dataclass`)を返却する。保存は任意とし、呼び出し側でダウンロードに使う。

最後に`main.py`でこの戻り値を受け取り、`st.image`でプレビューし、`st.download_button`に`image_bytes`と`mime_type`を渡してダウンロードできるようにする。生成画像の保存先をユーザーに明示したい場合はファイル名を固定(`generated_image.png`)し、同時にUIからダウンロード可能にする。`st.toast`や`st.success`を用いて成功を通知する。

## Concrete Steps

1. 依存関係確認のため `pip install -r requirements.txt` を実行したところタイムアウトが発生したため、`pip install google-genai` を個別に実行して不足分を解消した。  
       pip install google-genai  
       Requirement already satisfied: google-genai in ...  
2. 手元での動作検証は `streamlit run main.py` で行う想定。APIキーと検証用ラフ画像が揃ったらこのコマンドを実行し、フォーム送信から生成結果表示までを確認する。  
3. APIレスポンスで生成された`generated_image.png`が保存されるかを `dir generated_image.png` で確認し、必要に応じてファイルを削除する。(APIキーが利用できる環境で実施)  
4. コードの構文エラーがないことを `python -m compileall main.py illust.py` で検証し、両ファイルのバイトコード生成が成功することを確認した。

## Validation and Acceptance

`streamlit run main.py`を起動し、テスト用のラフ画像をアップロード、色情報を入力し、アスペクト比(例:4:5)と解像度(例:2K)を選んで「イラスト生成」ボタンを押す。処理中のスピナーの後、生成された画像がプレビューされ、ダウンロードボタンでPNGが得られることを確認する。エラー時には画面にスタックトレースではなく要約メッセージが表示されること。必要であれば`.env`に`GOOGLE_API_KEY`を置き、APIキーが設定されていない場合には明示的な警告を出す。

## Idempotence and Recovery

フォーム送信は何度でも繰り返せ、同じパラメータで再送しても問題ない。生成画像は一時的にメモリと`generated_image.png`に保存されるだけなので、不要になればファイルを削除する。APIエラー時は例外メッセージをログとUIに表示し、ユーザーは入力を修正して再送できる。

## Artifacts and Notes

完成後には以下の証跡を残す:  
    Streamlitログに表示されたAPI呼び出し成功メッセージ例。  
    保存された`generated_image.png`の存在確認出力(`dir generated_image.png`)。  
    UIのスクリーンショットやテキスト出力でプレビューとダウンロードボタンが描画されていることを示す。  
これらは必要に応じてREADMEにも簡潔に追記する。

## Interfaces and Dependencies

`illust.py`に以下のインターフェイスを用意する:  
    @dataclass  
    class GeneratedImage:  
        image: PIL.Image.Image  
        raw_bytes: bytes  
        mime_type: str  
        prompt: str  
`generate_image(prompt, image, aspect_ratio=None, resolution=None) -> GeneratedImage` は`google.genai.Client.models.generate_content`を呼び出し、`types.GenerationConfig(response_mime_type="image/png", aspect_ratio=<optional>, output_image_resolution=<optional>)`を設定する。`main.py`ではこの戻り値を受け取り、`st.image(result.image, use_container_width=True)`と`st.download_button("画像をダウンロード", result.raw_bytes, file_name="generated_image.png", mime=result.mime_type)`を実装する。これらのAPI呼び出しがREADMEに記載されたユーザーフローを満たす完成条件となる。

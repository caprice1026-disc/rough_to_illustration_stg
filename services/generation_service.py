from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from flask import session
from PIL import Image
from werkzeug.datastructures import FileStorage

from illust import generate_image
from services.prompt_builder import build_prompt


@dataclass
class GenerationResult:
    """生成結果をフロントエンドで扱いやすい形にまとめたデータクラス。"""

    image_data_uri: str
    prompt_text: str
    mime_type: str
    encoded_image: str


class GenerationError(ValueError):
    """入力バリデーションや前処理で発生した例外。"""


def normalize_optional(label: Optional[str]) -> Optional[str]:
    """フォームの「auto」をNoneに変換してAPIに渡す形へ揃える。"""

    if not label or label == "auto":
        return None
    return label


def decode_uploaded_image(file: Optional[FileStorage]) -> Image.Image:
    """アップロードされた画像ファイルをPIL Imageとして読み込む。"""

    if file is None or file.filename == "":
        raise GenerationError("ラフ絵ファイルを選択してください。")

    try:
        raw_bytes = file.read()
        image = Image.open(BytesIO(raw_bytes)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise GenerationError(f"画像の読み込みに失敗しました: {exc}") from exc

    return image


def run_generation(
    *,
    file: Optional[FileStorage],
    color_instruction: str,
    pose_instruction: str,
    aspect_ratio_label: Optional[str],
    resolution_label: Optional[str],
) -> GenerationResult:
    """入力からプロンプトを作成し、画像生成APIを呼び出して結果を返す。"""

    image = decode_uploaded_image(file)
    aspect_ratio = normalize_optional(aspect_ratio_label)
    resolution = normalize_optional(resolution_label)
    prompt = build_prompt(color_instruction, pose_instruction)

    generated = generate_image(
        prompt=prompt,
        image=image,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )

    encoded = base64.b64encode(generated.raw_bytes).decode("utf-8")
    return GenerationResult(
        image_data_uri=f"data:{generated.mime_type};base64,{encoded}",
        prompt_text=generated.prompt,
        mime_type=generated.mime_type,
        encoded_image=encoded,
    )


def save_result_to_session(result: GenerationResult) -> None:
    """生成結果をセッションへ保存して再描画時に利用できるようにする。"""

    session["generated_image"] = result.encoded_image
    session["generated_mime"] = result.mime_type
    session["generated_prompt"] = result.prompt_text


def load_result_from_session() -> Optional[GenerationResult]:
    """セッションに保存された生成結果を復元する。"""

    encoded = session.get("generated_image")
    if not encoded:
        return None

    mime_type = session.get("generated_mime", "image/png")
    prompt_text = session.get("generated_prompt") or ""
    return GenerationResult(
        image_data_uri=f"data:{mime_type};base64,{encoded}",
        prompt_text=prompt_text,
        mime_type=mime_type,
        encoded_image=encoded,
    )

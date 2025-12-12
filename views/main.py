from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional

from flask import Blueprint, abort, flash, render_template, request, send_file
from flask_login import login_required

from services.generation_service import (
    GenerationError,
    load_result_from_session,
    run_generation,
    save_result_to_session,
)


main_bp = Blueprint("main", __name__)

ASPECT_RATIO_OPTIONS = ["auto", "1:1", "4:5", "16:9"]
RESOLUTION_OPTIONS = ["auto", "1K", "2K", "4K"]


def _restore_result() -> tuple[Optional[str], Optional[str]]:
    """セッションに保存された結果から表示用データを復元する。"""

    existing = load_result_from_session()
    if not existing:
        return None, None
    return existing.image_data_uri, existing.prompt_text


@main_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    image_data: Optional[str] = None
    prompt_text: Optional[str] = None

    if request.method == "POST":
        file = request.files.get("rough_image")
        color_instruction = request.form.get("color_instruction", "")
        pose_instruction = request.form.get("pose_instruction", "")
        aspect_ratio_label = request.form.get("aspect_ratio") or "auto"
        resolution_label = request.form.get("resolution") or "auto"

        try:
            result = run_generation(
                file=file,
                color_instruction=color_instruction,
                pose_instruction=pose_instruction,
                aspect_ratio_label=aspect_ratio_label,
                resolution_label=resolution_label,
            )
        except GenerationError as exc:
            flash(str(exc), "error")
        except Exception as exc:  # noqa: BLE001
            flash(f"画像生成に失敗しました: {exc}", "error")
        else:
            save_result_to_session(result)
            image_data = result.image_data_uri
            prompt_text = result.prompt_text
            flash("イラストの生成が完了しました。", "success")

    if not image_data:
        image_data, prompt_text = _restore_result()

    return render_template(
        "index.html",
        image_data=image_data,
        prompt_text=prompt_text,
        aspect_ratio_options=ASPECT_RATIO_OPTIONS,
        resolution_options=RESOLUTION_OPTIONS,
    )


@main_bp.route("/download")
@login_required
def download():
    existing = load_result_from_session()
    if not existing:
        abort(404)

    raw_bytes = base64.b64decode(existing.encoded_image)
    return send_file(
        BytesIO(raw_bytes),
        mimetype=existing.mime_type,
        as_attachment=True,
        download_name="generated_image.png",
    )

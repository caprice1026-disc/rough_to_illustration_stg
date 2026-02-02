from __future__ import annotations

from io import BytesIO
from typing import Any

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from illust import MissingApiKeyError
from models import ChatAttachment, ChatMessage, ChatSession
from services.chat_service import (
    CHAT_MODES,
    add_message,
    create_session,
    generate_multimodal_reply,
    last_assistant_image,
    load_chat_image_bytes,
    save_uploaded_image,
    touch_session,
    update_session_title,
)
from services.generation_service import GenerationError, decode_uploaded_image_raw, ensure_rgb


chat_bp = Blueprint("chat", __name__)


def _session_or_404(session_id: int) -> ChatSession:
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        abort(404)
    return session


def _serialize_message(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "text": message.text or "",
        "mode_id": message.mode_id,
        "created_at": message.created_at.isoformat() if message.created_at else "",
        "attachments": [
            {
                "kind": attachment.kind,
                "mime_type": attachment.mime_type,
                "url": url_for("chat.image", image_id=attachment.image_id),
            }
            for attachment in message.attachments
        ],
    }


@chat_bp.route("/chat", methods=["GET"])
@login_required
def index() -> str:
    sessions = (
        ChatSession.query.filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    session_id = request.args.get("session_id", type=int)
    selected: ChatSession | None = None

    if session_id:
        selected = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not selected:
            flash("指定されたチャットセッションが見つかりません。", "error")

    if selected is None:
        selected = sessions[0] if sessions else create_session(current_user.id, title="新しいチャット")
        if not sessions:
            sessions = [selected]

    last_image = last_assistant_image(selected)

    return render_template(
        "chat.html",
        chat_sessions=sessions,
        current_session=selected,
        chat_modes=CHAT_MODES,
        last_image=last_image,
    )


@chat_bp.route("/chat/new", methods=["POST"])
@login_required
def new_session() -> str:
    session = create_session(current_user.id, title="新しいチャット")
    return redirect(url_for("chat.index", session_id=session.id))


@chat_bp.route("/chat/images/<image_id>")
@login_required
def image(image_id: str):
    attachment = (
        ChatAttachment.query.join(ChatMessage)
        .join(ChatSession)
        .filter(ChatAttachment.image_id == image_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not attachment:
        abort(404)

    raw_bytes = load_chat_image_bytes(image_id)
    if raw_bytes is None:
        abort(404)
    return send_file(BytesIO(raw_bytes), mimetype=attachment.mime_type)


@chat_bp.route("/chat/messages", methods=["POST"])
@login_required
def send_message():
    session_id = request.form.get("session_id", type=int)
    if not session_id:
        return jsonify({"error": "セッションが見つかりません。"}), 400

    session = _session_or_404(session_id)
    user_message = (request.form.get("message") or "").strip()
    files = request.files.getlist("images")

    if not user_message and not files:
        return jsonify({"error": "メッセージまたは画像を入力してください。"}), 400

    try:
        attachments = []
        images = []
        for index, file in enumerate(files):
            stored = save_uploaded_image(file, label=f"添付画像{index + 1}")
            attachments.append(("image", stored))
            image = decode_uploaded_image_raw(file, label="添付画像")
            images.append(ensure_rgb(image))

        add_message(
            session=session,
            role="user",
            text=user_message,
            mode_id="text_chat",
            attachments=attachments,
        )
        update_session_title(session, user_message)

        reply = generate_multimodal_reply(session, user_message, images)
        assistant_message = add_message(
            session=session,
            role="assistant",
            text=reply,
            mode_id="text_chat",
        )

        touch_session(session)
    except MissingApiKeyError:
        return jsonify({"error": "APIキーが設定されていません。"}), 400
    except GenerationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": "チャット処理に失敗しました。"}), 500

    return jsonify({"assistant": _serialize_message(assistant_message)})



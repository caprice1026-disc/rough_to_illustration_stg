from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from flask import Blueprint, abort, current_app, jsonify, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import db
from illust import MissingApiKeyError
from models import ChatAttachment, ChatMessage, ChatSession, Generation, GenerationAsset, Preset, User
from services import chat_service, generation_service, modes, storage


api_bp = Blueprint("api", __name__, url_prefix="/api")

ASPECT_RATIO_OPTIONS = ["auto", "1:1", "4:5", "16:9"]
RESOLUTION_OPTIONS = ["auto", "1K", "2K", "4K"]


def _json(payload: dict[str, Any], status: int = 200):
    return jsonify(payload), status


def _error(message: str, status: int = 400):
    return _json({"error": message}, status)


def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_initial_user": user.is_initial_user,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
    }


def _serialize_admin_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "is_initial_user": user.is_initial_user,
        "created_at": user.created_at.isoformat() if user.created_at else "",
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else "",
    }


def _serialize_preset(preset: Preset) -> dict[str, Any]:
    return {
        "id": preset.id,
        "mode": preset.mode,
        "name": preset.name,
        "payload_json": preset.payload_json or {},
        "created_at": preset.created_at.isoformat() if preset.created_at else "",
        "updated_at": preset.updated_at.isoformat() if preset.updated_at else "",
    }


def _serialize_generation(generation: Generation) -> dict[str, Any]:
    return {
        "id": generation.id,
        "mode": generation.mode,
        "status": generation.status,
        "aspect_ratio": generation.aspect_ratio,
        "resolution": generation.resolution,
        "edit_mode": generation.edit_mode,
        "error_message": generation.error_message,
        "created_at": generation.created_at.isoformat() if generation.created_at else "",
        "finished_at": generation.finished_at.isoformat() if generation.finished_at else "",
    }


def _serialize_asset(asset: GenerationAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "mime_type": asset.mime_type,
        "byte_size": asset.byte_size,
        "width": asset.width,
        "height": asset.height,
        "url": url_for("api.asset", asset_id=asset.id),
        "download_url": url_for("api.asset", asset_id=asset.id, download=1),
        "created_at": asset.created_at.isoformat() if asset.created_at else "",
    }


def _serialize_chat_mode(mode: chat_service.ChatMode) -> dict[str, Any]:
    return {
        "id": mode.id,
        "label": mode.label,
        "description": mode.description,
        "helper": mode.helper,
    }


def _serialize_chat_message(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "text": message.text or "",
        "mode_id": message.mode_id,
        "created_at": message.created_at.isoformat() if message.created_at else "",
        "attachments": [
            {
                "id": attachment.id,
                "kind": attachment.kind,
                "mime_type": attachment.mime_type,
                "url": url_for("api.chat_asset", attachment_id=attachment.id),
            }
            for attachment in message.attachments
        ],
    }


def _serialize_chat_session(session: ChatSession, *, include_messages: bool = False) -> dict[str, Any]:
    payload = {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else "",
        "updated_at": session.updated_at.isoformat() if session.updated_at else "",
    }
    if include_messages:
        payload["messages"] = [_serialize_chat_message(message) for message in session.messages]
    return payload


def _session_or_404(session_id: int) -> ChatSession:
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        abort(404)
    return session


def _extract_payload() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return {}


def _require_admin():
    if not current_user.is_authenticated:
        return _error("認証が必要です。", 401)
    if not current_user.is_admin:
        return _error("管理者のみが利用できます。", 403)
    return None


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return None


def _ensure_chat_enabled():
    if not current_app.config.get("CHAT_ENABLED", True):
        abort(404)


def _build_payload_json(mode: str, data: dict[str, Any]) -> dict[str, Any]:
    if "payload_json" in data and isinstance(data["payload_json"], dict):
        return data["payload_json"]

    if mode == modes.MODE_REFERENCE_STYLE_COLORIZE.id:
        return {"reference_instruction": (data.get("reference_instruction") or "").strip()}
    if mode == modes.MODE_INPAINT_OUTPAINT.id:
        return {
            "edit_instruction": (data.get("edit_instruction") or "").strip(),
            "edit_mode": (data.get("edit_mode") or "inpaint").strip(),
        }
    return {
        "color_instruction": (data.get("color_instruction") or "").strip(),
        "pose_instruction": (data.get("pose_instruction") or "").strip(),
    }


def _validate_payload_json(mode: str, payload: dict[str, Any]) -> str | None:
    if mode == modes.MODE_REFERENCE_STYLE_COLORIZE.id:
        if not payload.get("reference_instruction"):
            return "追加指示を入力してください。"
        return None
    if mode == modes.MODE_INPAINT_OUTPAINT.id:
        if not payload.get("edit_instruction"):
            return "追加指示を入力してください。"
        return None
    if not payload.get("color_instruction") or not payload.get("pose_instruction"):
        return "色とポーズの指示を両方入力してください。"
    return None


@api_bp.get("/health")
def health():
    db_ok = True
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        current_app.logger.error("DBヘルスチェックに失敗しました: %s", exc)
    status = "ok" if db_ok else "error"
    return _json({"status": status, "timestamp": datetime.utcnow().isoformat(), "db_ok": db_ok})


@api_bp.get("/csrf")
def csrf_token():
    return _json({"csrf_token": generate_csrf()})


@api_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return _json({"authenticated": False})
    return _json({"authenticated": True, "user": _serialize_user(current_user)})


@api_bp.post("/auth/login")
def login():
    if current_user.is_authenticated:
        return _json({"user": _serialize_user(current_user)})

    data = _extract_payload()
    if not data:
        data = request.form.to_dict()

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return _error("ユーザー名とパスワードを入力してください。", 400)

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return _error("ユーザー名またはパスワードが違います。", 401)
    if not user.is_active:
        return _error("このアカウントは無効化されています。", 403)

    login_user(user)
    user.last_login_at = datetime.utcnow()
    db.session.add(user)
    db.session.commit()
    return _json({"user": _serialize_user(user)})


@api_bp.post("/auth/logout")
@login_required
def logout():
    logout_user()
    return _json({"ok": True})


@api_bp.patch("/users/me/password")
@login_required
def update_my_password():
    data = _extract_payload()
    if not data:
        data = request.form.to_dict()

    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    if not current_password or not new_password:
        return _error("現在のパスワードと新しいパスワードを入力してください。", 400)
    if not current_user.check_password(current_password):
        return _error("現在のパスワードが正しくありません。", 400)
    if current_password == new_password:
        return _error("新しいパスワードは現在のパスワードと異なる内容を指定してください。", 400)

    current_user.set_password(new_password)
    db.session.add(current_user)
    db.session.commit()
    return _json({"ok": True})


@api_bp.post("/auth/signup")
@login_required
def signup():
    error = _require_admin()
    if error:
        return error

    data = _extract_payload()
    if not data:
        data = request.form.to_dict()

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return _error("すべての項目を入力してください。", 400)

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return _error("同じユーザー名またはメールアドレスが既に存在します。", 400)

    user = User(username=username, email=email)
    user.set_password(password)
    user.role = "user"
    db.session.add(user)
    db.session.commit()
    return _json({"user": _serialize_user(user)}, 201)


@api_bp.get("/admin/users")
@login_required
def admin_users():
    error = _require_admin()
    if error:
        return error
    users = User.query.order_by(User.created_at.asc()).all()
    return _json({"users": [_serialize_admin_user(user) for user in users]})


@api_bp.post("/admin/users")
@login_required
def admin_create_user():
    error = _require_admin()
    if error:
        return error

    data = _extract_payload()
    if not data:
        data = request.form.to_dict()

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return _error("すべての項目を入力してください。", 400)
    if len(username) > 80:
        return _error("ユーザー名は80文字以内にしてください。", 400)
    if len(email) > 255:
        return _error("メールアドレスは255文字以内にしてください。", 400)

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return _error("同じユーザー名またはメールアドレスが既に存在します。", 400)

    user = User(username=username, email=email)
    user.set_password(password)
    user.role = "user"
    user.is_active = True
    db.session.add(user)
    db.session.commit()
    return _json({"user": _serialize_admin_user(user)}, 201)


@api_bp.patch("/admin/users/<int:user_id>/status")
@login_required
def admin_update_user_status(user_id: int):
    error = _require_admin()
    if error:
        return error

    data = _extract_payload()
    is_active = _parse_bool(data.get("is_active"))
    if is_active is None:
        return _error("is_active を true/false で指定してください。", 400)

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return _error("対象ユーザーが見つかりません。", 404)
    if user.id == current_user.id and not is_active:
        return _error("自分自身を無効化することはできません。", 400)

    user.is_active = is_active
    db.session.add(user)
    db.session.commit()
    return _json({"user": _serialize_admin_user(user)})


@api_bp.patch("/admin/users/<int:user_id>/password")
@login_required
def admin_reset_password(user_id: int):
    error = _require_admin()
    if error:
        return error

    data = _extract_payload()
    password = data.get("password") or ""
    if not password:
        return _error("新しいパスワードを入力してください。", 400)

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return _error("対象ユーザーが見つかりません。", 404)
    if user.id == current_user.id:
        return _error("自分自身のパスワード変更はアカウント設定から実行してください。", 400)

    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return _json({"user": _serialize_admin_user(user)})


@api_bp.patch("/admin/users/<int:user_id>/role")
@login_required
def admin_update_user_role(user_id: int):
    error = _require_admin()
    if error:
        return error

    data = _extract_payload()
    role = (data.get("role") or "").strip()
    if role != "admin":
        return _error("role には admin のみ指定できます。", 400)

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return _error("対象ユーザーが見つかりません。", 404)

    user.role = "admin"
    db.session.add(user)
    db.session.commit()
    return _json({"user": _serialize_admin_user(user)})


@api_bp.get("/modes")
def list_modes():
    return _json(
        {
            "modes": [
                {
                    "id": mode.id,
                    "label": mode.label,
                    "description": mode.description,
                    "enabled": mode.enabled
                    if mode.id != modes.MODE_CHAT.id
                    else bool(current_app.config.get("CHAT_ENABLED", True)),
                }
                for mode in modes.ALL_MODES
            ]
        }
    )


@api_bp.get("/options")
def options():
    return _json({"aspect_ratio_options": ASPECT_RATIO_OPTIONS, "resolution_options": RESOLUTION_OPTIONS})


@api_bp.get("/presets")
@login_required
def presets():
    mode_id = modes.normalize_mode_id(request.args.get("mode"))
    presets_list = (
        Preset.query.filter_by(user_id=current_user.id, mode=mode_id)
        .order_by(Preset.updated_at.desc())
        .all()
    )
    return _json({"presets": [_serialize_preset(preset) for preset in presets_list]})


@api_bp.post("/presets")
@login_required
def create_preset():
    data = _extract_payload()
    if not data:
        data = request.form.to_dict()
    if "payload_json" in data and not isinstance(data["payload_json"], dict):
        return _error("payload_json はJSONオブジェクトで指定してください。", 400)

    mode_id = modes.normalize_mode_id(data.get("mode"))
    name = (data.get("name") or "").strip()
    if not name:
        return _error("プリセット名を入力してください。", 400)
    if len(name) > 80:
        return _error("プリセット名は80文字以内にしてください。", 400)

    payload_json = _build_payload_json(mode_id, data)
    error = _validate_payload_json(mode_id, payload_json)
    if error:
        return _error(error, 400)

    preset = Preset(user_id=current_user.id, mode=mode_id, name=name, payload_json=payload_json)
    db.session.add(preset)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("同じ名前のプリセットが既に存在します。", 400)

    return _json({"preset": _serialize_preset(preset)}, 201)


@api_bp.delete("/presets/<int:preset_id>")
@login_required
def delete_preset(preset_id: int):
    mode_id = modes.normalize_mode_id(request.args.get("mode"))
    preset = Preset.query.filter_by(id=preset_id, user_id=current_user.id, mode=mode_id).first()
    if not preset:
        return _error("指定されたプリセットが見つかりません。", 404)

    db.session.delete(preset)
    db.session.commit()
    return _json({"ok": True})


@api_bp.post("/generations")
@login_required
def create_generation():
    mode_id = modes.normalize_mode_id(request.form.get("mode"))
    if mode_id == modes.MODE_CHAT.id:
        return _error("チャットモードでは生成できません。", 400)

    try:
        if mode_id == modes.MODE_REFERENCE_STYLE_COLORIZE.id:
            outcome = generation_service.run_generation_reference(
                user_id=current_user.id,
                reference_file=request.files.get("reference_image"),
                rough_file=request.files.get("rough_image"),
                reference_instruction=request.form.get("reference_instruction", ""),
                aspect_ratio_label=request.form.get("aspect_ratio"),
                resolution_label=request.form.get("resolution"),
            )
        elif mode_id == modes.MODE_INPAINT_OUTPAINT.id:
            outcome = generation_service.run_generation_edit(
                user_id=current_user.id,
                base_file=request.files.get("edit_base_image"),
                base_data=request.form.get("edit_base_data"),
                mask_file=request.files.get("edit_mask_image"),
                mask_data=request.form.get("edit_mask_data"),
                edit_mode=request.form.get("edit_mode", "inpaint"),
                edit_instruction=request.form.get("edit_instruction", ""),
            )
        else:
            outcome = generation_service.run_generation_rough(
                user_id=current_user.id,
                file=request.files.get("rough_image"),
                color_instruction=request.form.get("color_instruction", ""),
                pose_instruction=request.form.get("pose_instruction", ""),
                aspect_ratio_label=request.form.get("aspect_ratio"),
                resolution_label=request.form.get("resolution"),
            )
    except generation_service.GenerationError as exc:
        return _error(str(exc), 400)
    except MissingApiKeyError:
        current_app.logger.error("Missing API key for image generation.")
        return _error("APIキーが設定されていません。", 400)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Image generation failed: %s", exc)
        return _error("画像生成に失敗しました。", 500)

    return _json(
        {
            "generation": _serialize_generation(outcome.generation),
            "assets": [_serialize_asset(asset) for asset in outcome.assets],
        }
    )


@api_bp.get("/generations")
@login_required
def list_generations():
    generations = (
        Generation.query.filter_by(user_id=current_user.id)
        .order_by(Generation.created_at.desc())
        .limit(20)
        .all()
    )
    payload = []
    for generation in generations:
        assets = GenerationAsset.query.filter_by(generation_id=generation.id).all()
        payload.append(
            {
                "generation": _serialize_generation(generation),
                "assets": [_serialize_asset(asset) for asset in assets],
            }
        )
    return _json({"items": payload})


@api_bp.get("/generations/<int:generation_id>")
@login_required
def get_generation(generation_id: int):
    generation = Generation.query.filter_by(id=generation_id, user_id=current_user.id).first()
    if not generation:
        abort(404)
    assets = GenerationAsset.query.filter_by(generation_id=generation.id).all()
    return _json(
        {
            "generation": _serialize_generation(generation),
            "assets": [_serialize_asset(asset) for asset in assets],
        }
    )


@api_bp.get("/assets/<int:asset_id>")
@login_required
def asset(asset_id: int):
    asset_row = (
        GenerationAsset.query.join(Generation)
        .filter(GenerationAsset.id == asset_id, Generation.user_id == current_user.id)
        .first()
    )
    if not asset_row:
        abort(404)
    if not asset_row.object_name:
        abort(404)
    raw_bytes = storage.load_bytes(
        storage_backend=asset_row.storage_backend,
        bucket_name=asset_row.bucket,
        object_name=asset_row.object_name,
        local_dir_key="GENERATION_IMAGE_DIR",
        default_local_dir="generated_images",
    )
    if raw_bytes is None:
        abort(404)
    download = request.args.get("download") == "1"
    filename = f"generated_image{generation_service.extension_for_mime_type(asset_row.mime_type)}"
    return send_file(
        BytesIO(raw_bytes),
        mimetype=asset_row.mime_type,
        as_attachment=download,
        download_name=filename,
    )


@api_bp.get("/chat/modes")
@login_required
def chat_modes():
    _ensure_chat_enabled()
    return _json({"modes": [_serialize_chat_mode(mode) for mode in chat_service.CHAT_MODES]})


@api_bp.get("/chat/sessions")
@login_required
def chat_sessions():
    _ensure_chat_enabled()
    sessions = (
        ChatSession.query.filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    if not sessions:
        session = chat_service.create_session(current_user.id, title="新しいチャット")
        sessions = [session]
    return _json({"sessions": [_serialize_chat_session(session) for session in sessions]})


@api_bp.post("/chat/sessions")
@login_required
def create_chat_session():
    _ensure_chat_enabled()
    data = _extract_payload()
    title = (data.get("title") or "").strip() or "新しいチャット"
    session = chat_service.create_session(current_user.id, title=title)
    return _json({"session": _serialize_chat_session(session)}, 201)


@api_bp.get("/chat/sessions/<int:session_id>")
@login_required
def chat_session_detail(session_id: int):
    _ensure_chat_enabled()
    session = _session_or_404(session_id)
    return _json({"session": _serialize_chat_session(session, include_messages=True)})


@api_bp.post("/chat/sessions/<int:session_id>/messages")
@login_required
def chat_messages(session_id: int):
    _ensure_chat_enabled()
    session = _session_or_404(session_id)
    data = _extract_payload()
    user_message = (request.form.get("message") or data.get("message") or "").strip()
    raw_files = request.files.getlist("images")
    files = [file for file in raw_files if file and file.filename]

    if not user_message and not files:
        return _error("メッセージまたは画像を入力してください。", 400)

    try:
        attachments = []
        images = []
        for index, file in enumerate(files):
            stored = chat_service.save_uploaded_image(file, label=f"添付画像{index + 1}")
            attachments.append(stored)
            raw_bytes, filename, mime_type = generation_service.read_uploaded_bytes(
                file,
                label="添付画像",
                reset_stream=True,
            )
            image = generation_service.decode_image_bytes(
                raw_bytes,
                label="添付画像",
                filename=filename,
                mime_type=mime_type,
                convert_to_rgb=True,
            )
            images.append(image)

        chat_service.add_message(
            session=session,
            role="user",
            text=user_message,
            mode_id="text_chat",
            attachments=attachments,
        )
        chat_service.update_session_title(session, user_message)

        reply = chat_service.generate_multimodal_reply(session, user_message, images)
        assistant_message = chat_service.add_message(
            session=session,
            role="assistant",
            text=reply,
            mode_id="text_chat",
        )

        chat_service.touch_session(session)
    except MissingApiKeyError:
        return _error("APIキーが設定されていません。", 400)
    except generation_service.GenerationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Chat handling failed: %s", exc)
        return _error("チャット処理に失敗しました。", 500)

    return _json({"assistant": _serialize_chat_message(assistant_message)})


@api_bp.get("/chat/assets/<int:attachment_id>")
@login_required
def chat_asset(attachment_id: int):
    _ensure_chat_enabled()
    attachment = (
        ChatAttachment.query.join(ChatMessage)
        .join(ChatSession)
        .filter(ChatAttachment.id == attachment_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not attachment:
        abort(404)
    if not attachment.object_name:
        abort(404)

    raw_bytes = chat_service.load_chat_image_bytes(attachment)
    if raw_bytes is None:
        abort(404)
    return send_file(BytesIO(raw_bytes), mimetype=attachment.mime_type)

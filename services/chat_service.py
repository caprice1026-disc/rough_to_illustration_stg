from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from flask import current_app
from PIL import Image
from werkzeug.datastructures import FileStorage

from extensions import db
from illust import generate_multimodal_text, generate_text
from models import ChatAttachment, ChatMessage, ChatSession
from services import storage
from services.generation_service import decode_image_bytes, mime_type_for_image, read_uploaded_bytes


@dataclass(frozen=True)
class ChatMode:
    """チャットモードの定義。"""

    id: str
    label: str
    description: str
    helper: str


CHAT_MODE_TEXT = ChatMode(
    id="text_chat",
    label="Multimodal chat",
    description="Send text with optional images.",
    helper="Attach images or send text only.",
)

CHAT_MODES: list[ChatMode] = [
    CHAT_MODE_TEXT,
]


@dataclass
class StoredAttachment:
    """保存済み添付画像の情報。"""

    kind: str
    storage_backend: str
    bucket: str | None
    object_name: str
    mime_type: str
    byte_size: int
    width: int | None
    height: int | None
    sha256: str


def _storage_backend() -> str:
    return (current_app.config.get("CHAT_IMAGE_STORAGE") or "local").strip().lower()


def _bucket_name() -> str | None:
    return current_app.config.get("CHAT_IMAGE_BUCKET")


def _extension_for_mime(mime_type: str) -> str:
    if mime_type == "image/png":
        return ".png"
    if mime_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    return ".png"


def save_uploaded_image(file: Optional[FileStorage], *, label: str) -> StoredAttachment:
    """アップロード画像を保存して添付情報を返す。"""

    raw_bytes, filename, mime_type = read_uploaded_bytes(file, label=label, reset_stream=True)
    image = decode_image_bytes(
        raw_bytes,
        label=label,
        filename=filename,
        mime_type=mime_type,
        convert_to_rgb=False,
    )
    stored = storage.save_bytes(
        raw_bytes=raw_bytes,
        extension=_extension_for_mime(mime_type_for_image(image)),
        storage_backend=_storage_backend(),
        bucket_name=_bucket_name(),
        local_dir_key="CHAT_IMAGE_DIR",
        default_local_dir="chat_images",
        object_prefix="chat_images",
        content_type=mime_type_for_image(image),
    )
    width, height = image.size
    return StoredAttachment(
        kind="image",
        storage_backend=stored.storage_backend,
        bucket=stored.bucket,
        object_name=stored.object_name,
        mime_type=mime_type_for_image(image),
        byte_size=stored.byte_size,
        width=width,
        height=height,
        sha256=stored.sha256,
    )


def load_chat_image_bytes(attachment: ChatAttachment) -> Optional[bytes]:
    """添付画像のバイト列を取得する。"""

    if not attachment.object_name:
        return None
    return storage.load_bytes(
        storage_backend=attachment.storage_backend,
        bucket_name=attachment.bucket,
        object_name=attachment.object_name,
        local_dir_key="CHAT_IMAGE_DIR",
        default_local_dir="chat_images",
    )


def create_session(user_id: int, *, title: str) -> ChatSession:
    """チャットセッションを作成する。"""

    session = ChatSession(user_id=user_id, title=title)
    db.session.add(session)
    db.session.commit()
    return session


def touch_session(session: ChatSession) -> None:
    """セッションの更新日時を更新する。"""

    session.updated_at = db.func.now()
    db.session.add(session)
    db.session.commit()


def update_session_title(session: ChatSession, user_text: str) -> None:
    """初回メッセージからセッション名を更新する。"""

    if session.title != "新しいチャット":
        return
    trimmed = user_text.strip()
    if not trimmed:
        return
    session.title = trimmed[:30]
    db.session.add(session)
    db.session.commit()


def add_message(
    *,
    session: ChatSession,
    role: str,
    text: Optional[str] = None,
    mode_id: Optional[str] = None,
    attachments: Optional[Iterable[StoredAttachment]] = None,
) -> ChatMessage:
    """メッセージと添付を保存する。"""

    message = ChatMessage(session=session, role=role, text=text, mode_id=mode_id)
    db.session.add(message)

    if attachments:
        for stored in attachments:
            db.session.add(
                ChatAttachment(
                    message=message,
                    kind=stored.kind,
                    storage_backend=stored.storage_backend,
                    bucket=stored.bucket,
                    object_name=stored.object_name,
                    mime_type=stored.mime_type,
                    byte_size=stored.byte_size,
                    width=stored.width,
                    height=stored.height,
                    sha256=stored.sha256,
                )
            )

    db.session.commit()
    return message


def fetch_recent_text_history(session: ChatSession, *, limit: int = 8) -> list[ChatMessage]:
    """直近のテキスト履歴を取得する。"""

    return (
        ChatMessage.query.filter_by(session_id=session.id)
        .filter(ChatMessage.text.isnot(None))
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()[::-1]
    )


def build_text_prompt(history: list[ChatMessage], user_text: str) -> str:
    """テキストチャット用のプロンプトを組み立てる。"""

    lines = [
        "You are a helpful assistant for illustration workflows.",
        "Use the prior context if it helps.",
    ]
    for message in history:
        role = "User" if message.role == "user" else "Assistant"
        if message.text:
            lines.append(f"{role}: {message.text}")
    lines.append("---")
    lines.append(f"User: {user_text}")
    lines.append("Assistant:")
    return "\n".join(lines)


def generate_text_reply(session: ChatSession, user_text: str) -> str:
    """テキストのみの返信を生成する。"""

    history = fetch_recent_text_history(session)
    if history and history[-1].role == "user" and history[-1].text == user_text:
        history = history[:-1]
    prompt = build_text_prompt(history, user_text)
    return generate_text(prompt)


def generate_multimodal_reply(session: ChatSession, user_text: str, images: list[Image.Image]) -> str:
    """画像を含む返信を生成する。"""

    history = fetch_recent_text_history(session)
    if history and history[-1].role == "user" and history[-1].text == user_text:
        history = history[:-1]
    prompt_text = user_text.strip() if user_text.strip() else "Please describe the images."
    prompt = build_text_prompt(history, prompt_text)
    if images:
        return generate_multimodal_text(prompt, images)
    return generate_text(prompt)

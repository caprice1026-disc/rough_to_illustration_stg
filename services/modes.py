from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GenerationMode:
    """画面/サーバで共通に扱う生成モード定義。"""

    id: str
    label: str
    description: str
    enabled: bool = True


MODE_ROUGH_WITH_INSTRUCTIONS = GenerationMode(
    id="rough_with_instructions",
    label="ラフ→仕上げ（色・ポーズ指示）",
    description="ラフスケッチ1枚とテキスト指示で仕上げます。",
)

MODE_REFERENCE_STYLE_COLORIZE = GenerationMode(
    id="reference_style_colorize",
    label="完成絵参照→ラフ着色（2枚）",
    description="完成済みイラストを参照して、ラフスケッチを同じ絵柄で仕上げます。",
)

MODE_CHAT_EDIT = GenerationMode(
    id="chat_edit",
    label="チャット編集（準備中）",
    description="チャットで対話しながら画像を編集します。（後日実装）",
    enabled=False,
)

ALL_MODES: list[GenerationMode] = [
    MODE_ROUGH_WITH_INSTRUCTIONS,
    MODE_REFERENCE_STYLE_COLORIZE,
    MODE_CHAT_EDIT,
]

DEFAULT_MODE_ID: str = MODE_ROUGH_WITH_INSTRUCTIONS.id


def normalize_mode_id(mode_id: Optional[str]) -> str:
    """未対応/無効なモードIDはデフォルトへフォールバックする。"""

    for mode in ALL_MODES:
        if mode.enabled and mode.id == mode_id:
            return mode.id
    return DEFAULT_MODE_ID


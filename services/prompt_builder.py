from __future__ import annotations


def build_prompt(color_instruction: str, pose_instruction: str) -> str:
    """色指定とポーズ指示を組み合わせたプロンプトを生成する。"""

    base_prompt = (
        "Using the provided image of my rough drawing, create a detailed and polished illustration "
        "in the style of a high-quality anime. Pay close attention to the fidelity of the original sketch, "
        "fill in missing lines cleanly, and follow these color instructions to finish the artwork: {colors} "
        "Follow these pose instructions to position the character: {pose}"
    )
    return base_prompt.format(
        colors=color_instruction.strip() or "No specific colors were provided.",
        pose=pose_instruction.strip() or "Please maintain the pose of the original image.",
    )


REFERENCE_STYLE_COLORIZE_PROMPT = """
**Task:** Convert **Image 1 (rough sketch / target for editing)** into a **high-quality finished illustration**. Use **Image 2 (finished illustration)** only as a **style reference** (art style, texture, saturation range, and shading). **Output exactly one image: the finished illustration derived from Image 1.**

**Priorities:**

* **Preserve from Image 1 (highest priority):** composition, character proportions / facial features, pose, props, and overall placement.
* **Match to Image 2:** line weight and brush feel, paint/grain texture, shading and shadow rendering, color range/contrast, and background treatment.

**What to do:**

* Clean up and smooth the rough lines (fix gaps, wobbles, and inconsistencies).
* Add necessary details and apply shading to create convincing volume and depth.
* Enrich the coloring, keeping lighting and shadows consistent with a single coherent light source.
* Balance the overall image including the background (align background handling with the tendencies in Image 2).

**Strict prohibitions (important):**

* Do **not** change the character’s identity (no changes to face, hairstyle, age, body type; no unauthorized outfit changes).
* Do **not** add extra props, text, logos, or watermarks that are not present in Image 1.
* Do **not** make major composition changes or alter the camera angle compared to Image 1.
"""


def build_reference_style_colorize_prompt() -> str:
    """完成絵(参照)＋ラフ(対象)の2枚入力モード用の固定プロンプト。"""

    return REFERENCE_STYLE_COLORIZE_PROMPT.strip()

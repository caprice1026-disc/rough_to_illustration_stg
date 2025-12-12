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

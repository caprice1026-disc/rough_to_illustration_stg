from google import genai
from google.genai import types
from PIL import Image
import requests

client = genai.Client()

def generate_image(
    prompt: str, 
    image: Image.Image, 
    aspect_ratio: str | None = None,
    resolution: str | None = None
    ) -> types.Content:
    '''
    プロンプトと画像を使って画像生成APIを呼び出す関数
    '''
    response = client.models.generate_content(
        model="gemini-2.5-flash-image", # モデルは後で差し替えれるようにする、gemini-3-pro-image-previewを使用する予定
        contents=[prompt, image],
    )

    for part in response.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = part.as_image()
            image.save("generated_image.png")
        

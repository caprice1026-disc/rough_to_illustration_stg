from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()

prompt = (
    "Create a picture of my cat eating a nano-banana in a "
    "fancy restaurant under the Gemini constellation",
)
aspect_ratio = "5:4" # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
resolution = "2K" # "1K", "2K", "4K"

''' 画像の読み込みは以下のリンクを参照して実装すること
https://ai.google.dev/gemini-api/docs/image-understanding?hl=ja
'''
image = Image.open("/path/to/cat_image.png") # 画像のパスを指定。修正予定

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
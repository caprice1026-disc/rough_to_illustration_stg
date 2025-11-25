# Streamlitを使用してGUIを作成
import streamlit as st
from PIL import Image

st.title("ラフ絵2イラスト")

# ファイルアップロード
uploaded_file = st.file_uploader("画像を選択してください", type=["png", "jpg", "jpeg"])
if uploaded_file is not None:  
    image = Image.open(uploaded_file)
    st.image(image, caption='アップロードされた画像', use_column_width=True)

    # 色指定のテキスト入力
    illustration_collar = st.text_area("イラストに使用する色を指定してください", "ここに画像にどのような色を付けるか指定する文章を入れるようにする")

    if st.button("イラスト生成"):
        from illust import generate_image

        # プロンプトは別のファイルからインポートする形に変更したほうが良いかも
        prompt = (
            '''Using the provided image of my rough drawing, please create a detailed and polished illustration in the style of a high-quality anime. 
            Please use the following colors for the final image.
            {}.'''.format(illustration_collar)
        )

        # 画像生成関数の呼び出し
        generate_image(
            prompt=prompt,
            image=image,
            # ここのアスペクト比と解像度の指定はGUIで行うようにする
            aspect_ratio="5:4",
            resolution="2K"
        )
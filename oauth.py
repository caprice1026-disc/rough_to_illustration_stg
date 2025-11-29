from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth


def _build_credentials_from_secrets() -> dict:
    '''st.secrets から streamlit-authenticator 用の credentials を組み立てる。'''
    users_conf = st.secrets["auth"]["users"]

    credentials: dict = {"usernames": {}}

    for key, user in users_conf.items():
        # secrets 側に username があればそれを優先。なければ key を使う
        username = user.get("username", key)

        # secrets.toml には「平文パスワード」を置く想定
        raw_password: str = user["password"]

        # ★ 0.4.2 の正しい API：Hasher.hash()
        hashed_password: str = stauth.Hasher.hash(raw_password)

        credentials["usernames"][username] = {
            "name": user["name"],
            "email": user["email"],
            "password": hashed_password,
        }

    return credentials


def _create_authenticator() -> stauth.Authenticate:
    credentials = _build_credentials_from_secrets()
    cookie_conf = st.secrets["auth"]["cookie"]

    authenticator = stauth.Authenticate(
        credentials,
        cookie_conf["name"],
        cookie_conf["key"],
        cookie_conf["expiry_days"],
    )
    return authenticator


def require_login():
    '''ログインしていなければここで止める。成功したら (name, username, authenticator) を返す。'''
    authenticator = _create_authenticator()

    # ★ 0.4.2 の login は戻り値ではなく session_state に書き込む
    try:
        authenticator.login(location="main")
    except Exception as e:
        st.error(f"ログイン処理でエラーが発生しました: {e}")
        st.stop()

    auth_status = st.session_state.get("authentication_status")
    name = st.session_state.get("name")
    username = st.session_state.get("username")

    if auth_status:
        st.sidebar.write(f"ログイン中: {name}")
        authenticator.logout("ログアウト", location="sidebar")
        return name, username, authenticator

    elif auth_status is False:
        st.error("ユーザー名かパスワードが違います")
        st.stop()

    else:
        st.info("機能を利用するにはユーザー名とパスワードを入力してください。")
        st.stop()

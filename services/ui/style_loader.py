import os
import streamlit as st
import streamlit.components.v1 as components
import base64
 

def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def inject_local_font(font_path, font_name):
    if not os.path.exists(font_path):
        return
    
    with open(font_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    ext = os.path.splitext(font_path)[1].lstrip(".")
    fmt = {"otf": "opentype"}.get(ext, ext)
    mime = {"otf": "font/otf"}.get(ext, f"font/{ext}")

    st.markdown(f"""
        <style>
        @font-face {{
            font-family: '{font_name}';
            src: url('data:{mime};base64,{encoded}') format('{fmt}');
            font-weight: 100 900;
            font-style: normal;
            font-display: swap;
        }}
        </style>
    """, unsafe_allow_html=True)


def inject_webrtc_styles():
    if st.session_state.get("_webrtc_styles_injected", False):
        return
    st.session_state["_webrtc_styles_injected"] = True

    st.markdown(
        """
        <style>
        div[data-testid="stCustomComponentV1"] iframe {
            border-radius: 12px !important;
            border: 1px solid var(--border-neon) !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

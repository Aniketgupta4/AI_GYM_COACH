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
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    font_path = os.path.join(base_dir, "static", "AdobeClean.otf")
    encoded_font = ""
    
    if os.path.exists(font_path):
        with open(font_path, "rb") as font_file:
            encoded_font = base64.b64encode(font_file.read()).decode()

    components.html(
        f"""
        <script>
        (function patchWebRTCStyles() {{
            function injectIntoIframe(iframe) {{
                try {{
                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!doc || !doc.head) return;
                    if (doc.head.querySelector('#webrtc-custom-styles')) return;
                    const style = doc.createElement('style');
                    style.id = 'webrtc-custom-styles';
                    style.textContent = `
                        @font-face {{
                            font-family: 'AdobeClean';
                            src: url('data:font/otf;base64,{encoded_font}') format('opentype');
                            font-weight: 100 900;
                            font-style: normal;
                        }}
                        video {{
                            width: 100% !important;
                            height: auto !important;
                            max-width: 100% !important;
                            border-radius: 8px !important;
                            object-fit: contain !important;
                        }}
                        .MuiButtonBase-root,
                        .MuiButton-root,
                        .MuiButton-contained,
                        .MuiButton-text {{
                            border-radius: 8px !important;
                            font-family: 'AdobeClean', sans-serif !important;
                            letter-spacing: 0.03em !important;
                            min-height: 44px !important;
                            font-size: 0.95rem !important;
                            font-weight: 600 !important;
                        }}
                        .MuiBox-root {{
                            max-width: 100% !important;
                            display: flex !important;
                            flex-wrap: wrap !important;
                            gap: 8px !important;
                            justify-content: center !important;
                        }}
                    `;
                    doc.head.appendChild(style);
                }} catch (e) {{
                    console.warn('[patcher] could not inject:', e);
                }}
            }}

            function findAndPatch() {{
                try {{
                    const parentDoc = window.parent.document;
                    const iframes = parentDoc.querySelectorAll('iframe');
                    iframes.forEach(iframe => {{
                        if (iframe.src && iframe.src.includes('webrtc')) {{
                            if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {{
                                injectIntoIframe(iframe);
                            }} else {{
                                iframe.addEventListener('load', () => injectIntoIframe(iframe));
                            }}
                        }}
                    }});
                }} catch (e) {{}}
            }}

            findAndPatch();
        }})();
        </script>
        """,
        height=0,
    )


def ensure_sidebar_expanded():
    components.html(
        """
        <script>
        (function ensureSidebar() {
            function triggerExpand() {
                try {
                    const doc = window.parent.document;
                    if (!doc) return;
                    const expandBtn = doc.querySelector('[data-testid="stExpandSidebarButton"]') || 
                                      doc.querySelector('button[data-testid="stExpandSidebarButton"]');
                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (expandBtn && (!sidebar || sidebar.getAttribute('aria-expanded') === 'false')) {
                        expandBtn.click();
                    }
                } catch (e) {}
            }
            triggerExpand();
            setTimeout(triggerExpand, 300);
            setTimeout(triggerExpand, 1000);
        })();
        </script>
        """,
        height=0,
    )

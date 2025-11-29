import re

def render_html_to_text(html: str) -> str:
    text = re.sub(r"<br\\s*/?>", "\\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

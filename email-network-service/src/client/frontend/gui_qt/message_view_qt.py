import re


from src.common.logger import get_class_logger


def render_html_to_text(html: str) -> str:
    """Simplistic HTML to plain text conversion for the Qt viewer."""
    log.debug(f"Rendering HTML to text. Original length: {len(html)}")
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    stripped_text = text.strip()
    log.debug(f"Converted to plain text. New length: {len(stripped_text)}")
    return stripped_text

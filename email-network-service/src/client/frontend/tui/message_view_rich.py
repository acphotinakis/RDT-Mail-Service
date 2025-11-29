from rich.text import Text
import re


class MessageView:
    """
    Terminal version of the message viewer.
    Renders either HTML or plain text using Rich.
    """

    @staticmethod
    def render_html(html: str) -> Text:
        """Simplistic HTML → Text conversion."""
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        return Text(text.strip())

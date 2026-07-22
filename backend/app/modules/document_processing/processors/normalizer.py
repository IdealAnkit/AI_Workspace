"""Text normalization that preserves meaningful paragraph boundaries."""

import re
import unicodedata


class TextNormalizer:
    """Normalize extracted text without collapsing paragraph structure."""

    _control_characters = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _inline_whitespace = re.compile(r"[ \t]+")
    _excessive_blank_lines = re.compile(r"\n{3,}")

    def normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
        normalized = self._control_characters.sub("", normalized)
        normalized = "\n".join(
            self._inline_whitespace.sub(" ", line).strip() for line in normalized.split("\n")
        )
        normalized = self._excessive_blank_lines.sub("\n\n", normalized)
        return normalized.strip()

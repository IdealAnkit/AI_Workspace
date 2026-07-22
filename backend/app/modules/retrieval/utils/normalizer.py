import re
import unicodedata


class QueryNormalizer:
    def normalize(self, query: str) -> str:
        normalized = unicodedata.normalize("NFC", query).casefold().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return re.sub(r"([!?.,])\1+", r"\1", normalized)

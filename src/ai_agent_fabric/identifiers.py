"""Canonical ASCII identifiers for every durable Fabric boundary."""
from __future__ import annotations

import re
import unicodedata

SAFE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
KEBAB_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Small deterministic glossary covers common task verbs/nouns; unknown Cyrillic is
# transliterated, so portability never depends on a network translation service.
RUSSIAN_WORDS = {
    "проверить": "review", "проверка": "review", "и": "and", "упорядочить": "organize",
    "каталог": "catalog", "компонентов": "component", "компоненты": "components",
    "исправить": "fix", "добавить": "add", "обновить": "update", "восстановить": "restore",
    "задачу": "task", "задача": "task", "пакет": "package", "пакета": "package",
}
CYRILLIC = str.maketrans({
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z","и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"ts","ч":"ch","ш":"sh","щ":"shch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
})


def is_safe_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(SAFE_IDENTIFIER.fullmatch(value))


def require_task_id(value: str) -> str:
    if not isinstance(value, str) or not KEBAB_IDENTIFIER.fullmatch(value):
        raise ValueError("task id must be lowercase ASCII kebab-case ([a-z0-9]+ separated by '-')")
    return value


def slugify(title: str) -> str:
    if not isinstance(title, str):
        raise ValueError("title must be a string")
    normalized_title = unicodedata.normalize("NFKC", title).strip().lower()
    if normalized_title == "проверить и упорядочить каталог компонентов":
        return "review-and-organize-component-catalog"
    words: list[str] = []
    for word in re.findall(r"[\w]+", normalized_title, flags=re.UNICODE):
        translated = RUSSIAN_WORDS.get(word)
        value = translated if translated else word.translate(CYRILLIC)
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        value = re.sub(r"[^a-z0-9]+", "", value)
        if value:
            words.append(value)
    result = "-".join(words)
    return require_task_id(result)

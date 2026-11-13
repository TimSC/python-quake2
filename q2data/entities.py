"""The entity string of a map: ``{ "key" "value" ... }`` blocks."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from q2data.errors import FormatError


def tokens(text: str) -> Iterator[str]:
    """Split text into tokens the way Quake II's parser does.

    Whitespace is any character up to and including space; ``//`` starts a
    comment to the end of the line; a ``"`` starts a quoted token that ends at
    the next ``"`` (no escapes); anything else runs to the next whitespace.
    """
    i, n = 0, len(text)
    while True:
        while i < n and text[i] <= " ":
            i += 1
        if i >= n:
            return
        if text.startswith("//", i):
            end = text.find("\n", i)
            if end < 0:
                return
            i = end
            continue
        if text[i] == '"':
            end = text.find('"', i + 1)
            if end < 0:
                yield text[i + 1:]
                return
            yield text[i + 1:end]
            i = end + 1
            continue
        start = i
        while i < n and text[i] > " ":
            i += 1
        yield text[start:i]


@dataclass(slots=True)
class Entity:
    """One entity: its key/value pairs in file order (keys may repeat)."""

    pairs: list[tuple[str, str]] = field(default_factory=list)

    def get(self, key: str, default: str | None = None) -> str | None:
        """The value of ``key``; the last one wins if it repeats."""
        for k, v in reversed(self.pairs):
            if k == key:
                return v
        return default

    def __getitem__(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        return any(k == key for k, _ in self.pairs)

    @property
    def classname(self) -> str | None:
        return self.get("classname")


def parse_entities(text: str) -> list[Entity]:
    """Parse a whole entity string."""
    entities: list[Entity] = []
    stream = tokens(text)
    for token in stream:
        if token != "{":
            raise FormatError(f"found {token!r} when expecting {{")
        entity = Entity()
        while True:
            key = next(stream, None)
            if key is None:
                raise FormatError("EOF without closing brace")
            if key == "}":
                break
            value = next(stream, None)
            if value is None:
                raise FormatError("EOF without closing brace")
            if value == "}":
                raise FormatError("closing brace without data")
            entity.pairs.append((key, value))
        entities.append(entity)
    return entities


def format_entities(entities: list[Entity]) -> str:
    """Write entities back as an entity string."""
    lines: list[str] = []
    for entity in entities:
        lines.append("{")
        lines.extend(f'"{key}" "{value}"' for key, value in entity.pairs)
        lines.append("}")
    return "\n".join(lines) + "\n"

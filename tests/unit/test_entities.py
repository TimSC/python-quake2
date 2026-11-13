import pytest

from q2data import FormatError
from q2data.entities import Entity, format_entities, parse_entities, tokens


def test_tokens():
    text = '{ "key" "a value"  // comment "ignored"\n word{ "" }'
    assert list(tokens(text)) == ["{", "key", "a value", "word{", "", "}"]


def test_unterminated_quote_runs_to_end():
    assert list(tokens('"abc')) == ["abc"]


def test_parse_entities():
    text = """
    {
    "classname" "worldspawn"
    "message" "The Outer Base"
    }
    {
    "classname" "light"
    "light" "200"
    "light" "300"
    }
    """
    worldspawn, light = parse_entities(text)
    assert worldspawn.classname == "worldspawn"
    assert worldspawn["message"] == "The Outer Base"
    assert light.get("light") == "300"  # the last of a repeated key wins
    assert light.pairs.count(("light", "200")) == 1
    assert "origin" not in light
    with pytest.raises(KeyError):
        light["origin"]


@pytest.mark.parametrize("text, message", [
    ('"classname" "x"', "expecting"),
    ('{ "classname" "x"', "EOF without closing brace"),
    ('{ "classname" }', "closing brace without data"),
    ('{ "classname"', "EOF without closing brace"),
])
def test_parse_errors(text, message):
    with pytest.raises(FormatError, match=message):
        parse_entities(text)


def test_format_round_trip():
    entities = [Entity([("classname", "worldspawn")]),
                Entity([("classname", "info_player_start"), ("origin", "0 0 24")])]
    assert parse_entities(format_entities(entities)) == entities

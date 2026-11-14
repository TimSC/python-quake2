import pytest

from client.sound.music import GameType, gog_track


@pytest.mark.parametrize("track, game, expected", [
    (0, GameType.OTHER, 0), (1, GameType.OTHER, 0),  # no track, the CD's data track
    (2, GameType.OTHER, 2), (11, GameType.OTHER, 11),
    (2, GameType.ROGUE, 12), (11, GameType.ROGUE, 21),
    (2, GameType.XATRIX, 9), (3, GameType.XATRIX, 13), (8, GameType.XATRIX, 15),
    (12, GameType.XATRIX, 12),  # beyond the CD: unchanged
])
def test_gog_track(track, game, expected):
    assert gog_track(track, game) == expected

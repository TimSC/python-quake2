# Unit checks of common/shared/shared.py against the behaviour of Yamagi's shared.c (no game data needed).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"]="1"
from common.shared import shared as S
s = ""
s = S.Info_SetValueForKey(s, "name", "Player")
s = S.Info_SetValueForKey(s, "skin", "male/grunt")
s = S.Info_SetValueForKey(s, "hand", "2")
print(repr(s))
assert s == "\\name\\Player\\skin\\male/grunt\\hand\\2"
assert S.Info_ValueForKey(s, "skin") == "male/grunt"
assert S.Info_ValueForKey(s, "nam") == ""
assert S.Info_ValueForKey(s, "hand") == "2"
assert S.Info_ValueForKey(s, "x") == ""
s = S.Info_SetValueForKey(s, "skin", "female/athena")
assert s == "\\name\\Player\\hand\\2\\skin\\female/athena", s
s = S.Info_RemoveKey(s, "name")
assert s == "\\hand\\2\\skin\\female/athena", s
assert S.Info_SetValueForKey(s, "bad;key", "1") == s
assert S.Info_SetValueForKey(s, "k", "a\"b") == s
assert S.Info_SetValueForKey(s, "hand", "") == "\\skin\\female/athena"
assert S.Info_Validate("abc") and not S.Info_Validate("a;b")
print("info ok")

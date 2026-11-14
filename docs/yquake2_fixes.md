# Fixes to apply to the yquake2 branch

Bugs found while reworking the `pythonic` branch (see
`docs/pythonic_plan.md`) that the `yquake2` branch still has. Each was
checked against the `yquake2` branch; all were still there on 2026-11-14.

Applied there, they are `Q2PORT` fixes or follow Yamagi's C. Tick an item
when it is applied, and add new ones as they are found.

- [ ] **`serverrecord` crashes the server** (`server/sv_entities.py`,
  `SV_RecordDemoMessage`): `shared_c.LittleLong(buf.cursize)` unpacks
  bytes, so an int raises `TypeError` on the first recorded frame. Write
  the length with `struct.pack("<i", buf.cursize)`. (Playing the demo
  back is then refused with "msglen > MAX_MSGLEN", as in Yamagi.)
- [ ] **The `info` reply is aligned wrongly** (`server/sv_conless.py`,
  `SVC_Info`): `"{:16s} {:8s} {}/{}"` left-aligns the fields; the C's
  `"%16s %8s %2i/%2i"` right-aligns them and pads the counts to 2. The C
  also cuts the reply at 63 characters (`char string[64]`).
- [ ] **Number arguments of connectionless packets** (`SVC_Info`,
  `SVC_DirectConnect`): a value that isn't a number becomes `None`,
  where the C's `strtol` gives 0 or the leading digits (`"12abc"` is 12).
  In `SVC_DirectConnect` one bad value also makes both qport and
  challenge `None`. `shared_c.atoi` parses as the C does.
- [ ] **`kick` and `dumpuser` crash the server** (`server/sv_cmd.py`,
  `SV_SetPlayer`): `idnum = int(s)` raises on a slot like `1abc` (the C's
  strtol reads 1), and `s[0]` raises on an empty name (`kick ""`). Use
  `shared_c.atoi` and `s[:1]`.
- [ ] **`setmaster` after a bad address** (`SV_SetMaster_f`): the C (and
  the port) parse each address into `master_adr[i]` but use
  `master_adr[slot]`, so after a bad one the addresses go in the wrong
  slots. A bug in Yamagi too: fix it only as a `Q2PORT` change.
- [ ] **Lengths the C caps** (`SVC_DirectConnect`, `SVC_RemoteCommand`):
  the userinfo is not cut at `MAX_INFO_STRING - 1` before the `ip` key is
  added (`Q_strlcpy`), and the rcon command is not cut at 1023
  characters (`char remaining[1024]`).

# Fixes to apply to the yquake2 branch

Bugs found while reworking the `pythonic` branch (see
`docs/pythonic_plan.md`) that the `yquake2` branch still has. Each was
checked against the `yquake2` branch; all were still there on 2026-11-14.

Applied there, they are `Q2PORT` fixes or follow Yamagi's C. Tick an item
when it is applied, and add new ones as they are found.

All the items below were applied on the `yquake2` branch on 2026-11-14
(commit ba68fc8, "Issues found during pythonic work 2").

- [x] **`serverrecord` crashes the server** (`server/sv_entities.py`,
  `SV_RecordDemoMessage`): `shared_c.LittleLong(buf.cursize)` unpacks
  bytes, so an int raises `TypeError` on the first recorded frame. Write
  the length with `struct.pack("<i", buf.cursize)`. (Playing the demo
  back is then refused with "msglen > MAX_MSGLEN", as in Yamagi.)
- [x] **The `info` reply is aligned wrongly** (`server/sv_conless.py`,
  `SVC_Info`): `"{:16s} {:8s} {}/{}"` left-aligns the fields; the C's
  `"%16s %8s %2i/%2i"` right-aligns them and pads the counts to 2. The C
  also cuts the reply at 63 characters (`char string[64]`).
- [x] **Number arguments of connectionless packets** (`SVC_Info`,
  `SVC_DirectConnect`): a value that isn't a number becomes `None`,
  where the C's `strtol` gives 0 or the leading digits (`"12abc"` is 12).
  In `SVC_DirectConnect` one bad value also makes both qport and
  challenge `None`. `shared_c.atoi` parses as the C does.
- [x] **`kick` and `dumpuser` crash the server** (`server/sv_cmd.py`,
  `SV_SetPlayer`): `idnum = int(s)` raises on a slot like `1abc` (the C's
  strtol reads 1), and `s[0]` raises on an empty name (`kick ""`). Use
  `shared_c.atoi` and `s[:1]`.
- [x] **`setmaster` after a bad address** (`SV_SetMaster_f`): the C (and
  the port) parse each address into `master_adr[i]` but use
  `master_adr[slot]`, so after a bad one the addresses go in the wrong
  slots. A bug in Yamagi too: fix it only as a `Q2PORT` change.
- [x] **Lengths the C caps** (`SVC_DirectConnect`, `SVC_RemoteCommand`):
  the userinfo is not cut at `MAX_INFO_STRING - 1` before the `ip` key is
  added (`Q_strlcpy`), and the rcon command is not cut at 1023
  characters (`char remaining[1024]`).

Found while applying them, on both branches, and fixed on both:

- [x] **`setmaster` crashes with any address** (`SV_SetMaster_f`): it
  called `NET_StringToAdr(s, adr)`, but the port's `NET_StringToAdr` takes
  the string and returns the address (or None).
- [x] **A bad host name can crash the game**
  (`backends/unix/network.py`, `NET_StringToSockaddr`): for a name like
  `bad..host` Python's `getaddrinfo` raises `UnicodeError` (its IDNA
  encoding), which wasn't caught. `connect`, `rcon_address` and
  `setmaster` all reach it. It now prints the error and refuses the
  address, as the C's failing `getaddrinfo` does.

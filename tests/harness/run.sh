#!/bin/sh
# Build the C collision/pmove harnesses and compare their output with the
# Python twins on seeded random traces and moves (output must match exactly).
# Built against Yamagi's src/common by default; C=id builds against id's 3.21 source
# (quake2-original) instead.
# usage (from the repo root): tests/harness/run.sh
set -e
PY=${PY:-env/bin/python}
OUT=${OUT:-/tmp/q2tests/harness}
Y=yquake2/src
mkdir -p "$OUT"
# the inputs come from a map in the (proprietary) game data; skip without it
if [ ! -d "${Q2DATA:-/home/tim/dev/quake2data/Data}/baseq2" ]; then
	echo "skip cmharness, pmharness, rand  (no game data)"; exit 0
fi
$PY tests/harness/gen_inputs.py "$OUT" ${MAP:-base1} ${SEED:-1}
if [ "$C" = id ]; then
	Q=quake2-original
	gcc -O0 -g -w -I$Q/qcommon -I$Q/game -o "$OUT/cmharness" tests/harness/cmharness.c $Q/qcommon/cmodel.c $Q/game/q_shared.c $Q/qcommon/md4.c -lm
	gcc -O0 -g -w -I$Q/qcommon -I$Q/game -o "$OUT/pmharness" tests/harness/pmharness.c $Q/qcommon/pmove.c $Q/qcommon/cmodel.c $Q/game/q_shared.c $Q/qcommon/md4.c -lm
else
	YF="-O0 -g -w -DYQ2 -DDEDICATED_ONLY -DYQ2OSTYPE=\"Linux\" -DYQ2ARCH=\"x86_64\" -I$Y/common"
	gcc $YF -o "$OUT/cmharness" tests/harness/cmharness.c $Y/common/collision.c $Y/common/shared/shared.c $Y/common/md4.c -lm
	gcc $YF -o "$OUT/pmharness" tests/harness/pmharness.c $Y/common/pmove.c $Y/common/collision.c $Y/common/shared/shared.c $Y/common/md4.c -lm
fi
export BSP="$OUT/${MAP:-base1}.bsp"
export PYGAME_HIDE_SUPPORT_PROMPT=1
export Q2PORT_NOMOUSE=1	# no mouse capture while the tests run
fail=0
for h in cm pm; do
	"$OUT/${h}harness" < "$OUT/${h}_in.txt" > "$OUT/${h}_c.out"
	$PY tests/harness/${h}harness.py < "$OUT/${h}_in.txt" > "$OUT/${h}_py.out" 2>"$OUT/${h}_py.err" || { echo "FAIL ${h}harness.py (see $OUT/${h}_py.err)"; fail=1; continue; }
	if cmp -s "$OUT/${h}_c.out" "$OUT/${h}_py.out"; then
		echo "ok   ${h}harness ($(wc -l < "$OUT/${h}_c.out") lines match)"
	else
		echo "FAIL ${h}harness: $(diff "$OUT/${h}_c.out" "$OUT/${h}_py.out" | grep -c '^<') lines differ (diff $OUT/${h}_c.out $OUT/${h}_py.out)"; fail=1
	fi
done
# Yamagi's PRNG (always built from yquake2/, which has it)
gcc -O0 -o "$OUT/randtest" tests/harness/randtest.c yquake2/src/common/shared/rand.c
"$OUT/randtest" > "$OUT/rand_c.out"
$PY tests/harness/randtest.py > "$OUT/rand_py.out"
if cmp -s "$OUT/rand_c.out" "$OUT/rand_py.out"; then echo "ok   rand"; else echo "FAIL rand (diff $OUT/rand_c.out $OUT/rand_py.out)"; fail=1; fi
exit $fail

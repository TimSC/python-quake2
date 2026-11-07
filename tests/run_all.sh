#!/bin/sh
# Headless-ish smoke tests for the port: each runs the real game for a short time
# and checks the log for Python tracebacks and an expected line.
# The game data is read from $Q2DATA (never copied into the repo).
# usage: tests/run_all.sh [name ...]      (from the repo root)
# The C collision/pmove comparison is separate: tests/harness/run.sh
Q2DATA=${Q2DATA:-/home/tim/dev/quake2data/Data}
PY=${PY:-env/bin/python}
OUT=${OUT:-/tmp/q2tests}
export OUT SHOT="${OUT}/vr_t%d.png"
mkdir -p "$OUT"
export PYGAME_HIDE_SUPPORT_PROMPT=1
export Q2PORT_NOMOUSE=1	# no mouse capture while the tests run
fail=0
run() {	# name timeout expected-regex args...
	name=$1; t=$2; want=$3; shift 3
	if [ -n "$ONLY" ] && ! echo " $ONLY " | grep -q " $name "; then return; fi
	timeout -k 10 "$t" $PY -u tests/$name.py "$@" > "$OUT/$name.log" 2>&1
	if grep -q "Traceback\|Error:" "$OUT/$name.log" || ! grep -q "$want" "$OUT/$name.log"; then
		echo "FAIL $name  (log: $OUT/$name.log)"; fail=1
	else
		echo "ok   $name"
	fi
}
ONLY="$*"
if [ -z "$ONLY" ] || echo " $ONLY " | grep -q " static "; then
	if $PY tests/check_static.py > "$OUT/static.log" 2>&1; then echo "ok   static"; else echo "FAIL static  (log: $OUT/static.log)"; fail=1; fi
	# module-level undefined names too (pyflakes, if installed in the venv)
	if $PY -m pyflakes --version > /dev/null 2>&1; then
		$PY -m pyflakes common server game client linux ref_gl qcommon tests 2>&1 | grep "undefined name" | grep -v "sys_linux.py:.*elapse_time" > "$OUT/pyflakes.log"
		if [ -s "$OUT/pyflakes.log" ]; then echo "FAIL pyflakes  (log: $OUT/pyflakes.log)"; fail=1; else echo "ok   pyflakes"; fi
	fi
fi
if [ -z "$ONLY" ] || echo " $ONLY " | grep -q " unit "; then
	ok=1
	for u in tests/unit_*.py; do $PY "$u" > "$OUT/$(basename $u .py).log" 2>&1 || { echo "FAIL $(basename $u .py)  (log: $OUT/$(basename $u .py).log)"; ok=0; fail=1; }; done
	[ $ok = 1 ] && echo "ok   unit"
fi
run state_trace 90 "40s\|30s frame" +set basedir "$Q2DATA" +map base1
run monster_all 240 "mon: finished calls .* errors 0" +set basedir "$Q2DATA" +skill 2 +set g_select_empty 1 +map base1
# walk into base1's func_wall *9 ledge (the old fall-through-the-floor bug)
run walk_test 90 "walk: passed" -427.6 108.4 -23.9 -50 200 4 +set basedir "$Q2DATA" +map base1
run fire_test 90 "fire: done" +set basedir "$Q2DATA" +map base1
run cin_play 60 "cin: finished" +set basedir "$Q2DATA" +map idlog.cin
run ogg_music 90 "ogg: done" +set basedir "$Q2DATA" +map base1
run menu_settings_test 120 "ms: after renderer restart" +set basedir "$Q2DATA" +map base1
run vidrestart_shot 60 "vr: t=12 polys [1-9]" +set basedir "$Q2DATA" +map base1
run dedicated 60 "dedicated: .* state ss_game, map base1" +set basedir "$Q2DATA" +set dedicated 1 +map base1
run save_load 120 "save_load: level contents restored" +set basedir "$Q2DATA" +map base1
# the map run again with every GL extension off
NOEXT="+set gl_ext_multitexture 0 +set gl_ext_pointparameters 0 +set gl_ext_palettedtexture 0 +set gl_ext_swapinterval 0 +set gl_ext_compiled_vertex_array 0"
if [ -z "$ONLY" ] || echo " $ONLY " | grep -q " noext "; then
	ONLY_SAVE=$ONLY; ONLY=""
	timeout 90 $PY -u tests/state_trace.py +set basedir "$Q2DATA" $NOEXT +map base1 > "$OUT/noext.log" 2>&1
	if grep -q "Traceback\|Error:" "$OUT/noext.log" || ! grep -q "30s frame" "$OUT/noext.log"; then echo "FAIL noext  (log: $OUT/noext.log)"; fail=1; else echo "ok   noext"; fi
	ONLY=$ONLY_SAVE
fi
exit $fail

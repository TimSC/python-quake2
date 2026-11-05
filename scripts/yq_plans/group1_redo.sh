#!/bin/sh
# Regenerate group 1's split of game/q_shared.py from a pre-move copy and re-apply the port edits.
# usage: scripts/yq_plans/group1_redo.sh <backup.tgz with game/q_shared.py>
set -e
PY=${PY:-env/bin/python}
tar xzf "$1" game/q_shared.py
$PY scripts/yq_plans/regen_split.py scripts/yq_plans/group1.py game/q_shared.py "$1"
rm game/q_shared.py
$PY scripts/yq_alias.py common.header.shared=shared common.shared.shared=shared_c common.header.common=common_h common.header.files=files_h common.shared.flash=flash
$PY scripts/yq_plans/group1_port.py

"""Re-run only the split of one module of a yq_move plan (after the plan was applied).
usage: regen_split.py <plan.py> <old module path, restored temporarily> <backup.tgz with the plan's old files>"""
import sys, os, tarfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import yq_move as ym
plan_path, old, tgz = sys.argv[1:4]
ns = {}; exec(open(plan_path).read(), ns)
plan = ym.Plan(ns.get("RENAMES", {}), ns.get("SPLITS", {}))
t = tarfile.open(tgz)
for o in list(plan.renames) + list(plan.splits):
	ym._SYMS[ym.mod_of(o)] = ym.toplevel_names(t.extractfile(o).read().decode())
for nm, text in ym.split_module(old, plan.splits[old], plan).items():
	p = ym.path_of(nm)
	out, notes = ym.rewrite_file(p, text, plan, nm, ym.mod_of(old), own_mod=nm)
	compile(out, p, "exec")
	open(p, "w").write(ym.merge_parts([out]))
	print("wrote", p, notes)

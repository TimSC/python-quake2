// Reference pmove harness: the C pmove and collision code with stubbed engine services.
// stdin: pm_type ox oy oz vx vy vz flags time gravity dx dy dz  msec buttons ax ay az fwd side up  snapinitial  frames  nmodels [models...]
// Runs Pmove `frames` times (feeding the state back), printing the state after each frame.
#include "stubs.h"

static int nmodels, models[16];
static int world_ent, model_ents[16];	// distinct addresses used as entity pointers
static vec3_t origin0 = {0, 0, 0};

// world trace then each inline model, merged as in SV_ClipMoveToEntities
static trace_t H_Trace (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end)
{
	trace_t tr, t; int i; char name[16];
	tr = CM_BoxTrace (start, end, mins, maxs, 0, MASK_PLAYERSOLID);
	tr.ent = (struct edict_s *)&world_ent;
	if (tr.fraction == 0)
		return tr;
	for (i = 0; i < nmodels; i++)
	{
		if (tr.allsolid)
			return tr;
		sprintf (name, "*%d", models[i]);
		t = CM_TransformedBoxTrace (start, end, mins, maxs, CM_InlineModel (name)->headnode, MASK_PLAYERSOLID, origin0, vec3_origin);
		if (t.allsolid || t.startsolid || t.fraction < tr.fraction)
		{
			t.ent = (struct edict_s *)&model_ents[i];
			if (tr.startsolid) { tr = t; tr.startsolid = true; }
			else tr = t;
		}
		else if (t.startsolid)
			tr.startsolid = true;
	}
	return tr;
}

static int H_PointContents (vec3_t p) { return CM_PointContents (p, 0); }

static const char *entname (struct edict_s *e)
{
	int i;
	if (!e) return "None";
	if (e == (struct edict_s *)&world_ent) return "world";
	for (i = 0; i < nmodels; i++) if (e == (struct edict_s *)&model_ents[i]) return "model";
	return "?";
}

int main (void)
{
	unsigned checksum; pmove_t pm; int v[24], frames, f, i, snap;
	Swap_Init ();
	CM_LoadMap ("maps/x.bsp", false, &checksum);
	while (scanf ("%d %d %d %d %d %d %d %d %d %d %d %d %d", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8], &v[9], &v[10], &v[11], &v[12]) == 13)
	{
		memset (&pm, 0, sizeof(pm));
		pm.s.pm_type = v[0];
		for (i = 0; i < 3; i++) { pm.s.origin[i] = v[1+i]; pm.s.velocity[i] = v[4+i]; pm.s.delta_angles[i] = v[10+i]; }
		pm.s.pm_flags = v[7]; pm.s.pm_time = v[8]; pm.s.gravity = v[9];
		scanf ("%d %d %d %d %d %d %d %d %d %d %d", &v[13], &v[14], &v[15], &v[16], &v[17], &v[18], &v[19], &v[20], &snap, &frames, &nmodels);
		for (i = 0; i < nmodels; i++) scanf ("%d", &models[i]);
		for (f = 0; f < frames; f++)
		{
			pm.cmd.msec = v[13]; pm.cmd.buttons = v[14];
			pm.cmd.angles[0] = v[15]; pm.cmd.angles[1] = v[16]; pm.cmd.angles[2] = v[17];
			pm.cmd.forwardmove = v[18]; pm.cmd.sidemove = v[19]; pm.cmd.upmove = v[20];
			pm.snapinitial = (f == 0) ? snap : false;
			pm.trace = H_Trace; pm.pointcontents = H_PointContents;
			Pmove (&pm);
			printf ("f %d origin %d %d %d velocity %d %d %d flags %d time %d ground %s\n", f, pm.s.origin[0], pm.s.origin[1], pm.s.origin[2],
				pm.s.velocity[0], pm.s.velocity[1], pm.s.velocity[2], pm.s.pm_flags, pm.s.pm_time, entname (pm.groundentity));
		}
	}
	return 0;
}

// Reference collision harness: the C collision code with stubbed engine services.
// stdin lines:  model ox oy oz ax ay az  sx sy sz  ex ey ez  minx miny minz  maxx maxy maxz  mask
// model 0 traces the world (headnode 0); model N traces inline model *N at origin/angles.
#include "stubs.h"

int main (void)
{
	unsigned checksum; int model; vec3_t o, a, s, e, mn, mx; int mask; trace_t t; char name[16];
	Swap_Init ();
	CM_LoadMap ("maps/x.bsp", false, &checksum);
	printf ("checksum %u numinline %d\n", checksum, CM_NumInlineModels ());
	while (scanf ("%d %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %d", &model, &o[0], &o[1], &o[2], &a[0], &a[1], &a[2],
		&s[0], &s[1], &s[2], &e[0], &e[1], &e[2], &mn[0], &mn[1], &mn[2], &mx[0], &mx[1], &mx[2], &mask) == 20)
	{
		int headnode = 0;
		if (model) { sprintf (name, "*%d", model); headnode = CM_InlineModel (name)->headnode; }
		t = CM_TransformedBoxTrace (s, e, mn, mx, headnode, mask, o, a);
		printf ("frac %.4f end %.2f %.2f %.2f startsolid %d allsolid %d normal %.4f %.4f %.4f contents %d\n", t.fraction,
			t.endpos[0], t.endpos[1], t.endpos[2], t.startsolid, t.allsolid, t.plane.normal[0], t.plane.normal[1], t.plane.normal[2], t.contents);
	}
	return 0;
}

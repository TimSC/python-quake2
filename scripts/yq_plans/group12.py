"""yq_move.py plan for group 12 (by hand): the menus move to client/menu/ whole; Yamagi's
menu.c, qmenu.c and videomenu.c are then ported into them (most of menu.c is new)."""

RENAMES = {'client/menu.py': 'client/menu/menu.py',
 'client/qmenu.py': 'client/menu/qmenu.py',
 'linux/vid_menu.py': 'client/menu/videomenu.py'}

SPLITS = {}

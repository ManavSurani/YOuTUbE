# Plan 25 Phase 0: The Audit Sees What the User Sees

Date: 2026-11-02 · Branch: `fix/ui-pass`

## Done
- `tools/ui_snapshots.py` builds every menu from its real parent in the real window:
  - the History row ⋯ menu from a real row in the list;
  - the row's right-click menu, through `contextMenuEvent` (its blocking `exec` is caught on the menu instance);
  - History ⋯ and the tray menu;
  - the History search box, Audio link box, and Settings folder field right-click menus.
- The tool now renders 58 images (8 new menu images).

## Gate: tool catches the bug
```
FINDING dark_08c_history_row_menu: background #000000 does not match theme surface #212121
FINDING dark_08g_history_row_right_click: background #000000 does not match theme surface #212121
FINDING light_08c_history_row_menu: background #000000 does not match theme surface #f2f2f2
FINDING light_08g_history_row_right_click: background #000000 does not match theme surface #f2f2f2
```
No findings for any other menu. The row menu's background is fully transparent, which Windows shows as black (see the owner's screenshot). On the real screen, a parentless copy of the same menu shows `#F2F2F2`, while the real row menu is black.

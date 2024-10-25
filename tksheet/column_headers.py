try:
    from __future__ import annotations
except SyntaxError:
    # Requires Python 3.7
    pass

import tkinter as tk
from collections import defaultdict
from collections.abc import (
    Callable,
    Hashable,
    Sequence,
)
from functools import (
    partial,
)
from itertools import (
    cycle,
    islice,
    repeat,
)
from math import ceil, floor
from operator import (
    itemgetter,
)
from typing import Literal

from .colors import (
    color_map,
)
from .formatters import is_bool_like, try_to_bool
from .functions import (
    consecutive_ranges,
    event_dict,
    get_n2a,
    is_contiguous,
    new_tk_event,
    pickled_event_dict,
    rounded_box_coords,
    try_binding,
)
from .other_classes import (
    DotDict,
    DraggedRowColumn,
    DropdownStorage,
    TextEditorStorage,
)
from .text_editor import (
    TextEditor,
)
from .vars import (
    USER_OS,
    rc_binding,
    symbols_set,
    text_editor_close_bindings,
    text_editor_newline_bindings,
    text_editor_to_unbind,
)


class ColumnHeaders(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(
            self,
            kwargs["parent"],
            background=kwargs["parent"].ops.header_bg,
            highlightthickness=0,
        )
        self.PAR = kwargs["parent"]
        self.current_height = None  # is set from within MainTable() __init__ or from Sheet parameters
        self.MT = None  # is set from within MainTable() __init__
        self.RI = None  # is set from within MainTable() __init__
        self.TL = None  # is set from within TopLeftRectangle() __init__
        self.popup_menu_loc = None
        self.extra_begin_edit_cell_func = None
        self.extra_end_edit_cell_func = None
        self.centre_alignment_text_mod_indexes = (slice(1, None), slice(None, -1))
        self.c_align_cyc = cycle(self.centre_alignment_text_mod_indexes)
        self.b1_pressed_loc = None
        self.closed_dropdown = None
        self.being_drawn_item = None
        self.extra_motion_func = None
        self.extra_b1_press_func = None
        self.extra_b1_motion_func = None
        self.extra_b1_release_func = None
        self.extra_double_b1_func = None
        self.ch_extra_begin_drag_drop_func = None
        self.ch_extra_end_drag_drop_func = None
        self.extra_rc_func = None
        self.selection_binding_func = None
        self.shift_selection_binding_func = None
        self.ctrl_selection_binding_func = None
        self.drag_selection_binding_func = None
        self.column_width_resize_func = None
        self.width_resizing_enabled = False
        self.height_resizing_enabled = False
        self.double_click_resizing_enabled = False
        self.col_selection_enabled = False
        self.drag_and_drop_enabled = False
        self.rc_delete_col_enabled = False
        self.rc_insert_col_enabled = False
        self.hide_columns_enabled = False
        self.edit_cell_enabled = False
        self.dragged_col = None
        self.visible_col_dividers = {}
        self.col_height_resize_bbox = tuple()
        self.cell_options = {}
        self.rsz_w = None
        self.rsz_h = None
        self.new_col_height = 0
        self.lines_start_at = 0
        self.currently_resizing_width = False
        self.currently_resizing_height = False
        self.ch_rc_popup_menu = None
        self.dropdown = DropdownStorage()
        self.text_editor = TextEditorStorage()

        self.disp_text = {}
        self.disp_high = {}
        self.disp_grid = {}
        self.disp_fill_sels = {}
        self.disp_resize_lines = {}
        self.disp_dropdown = {}
        self.disp_checkbox = {}
        self.disp_boxes = set()
        self.hidd_text = {}
        self.hidd_high = {}
        self.hidd_grid = {}
        self.hidd_fill_sels = {}
        self.hidd_resize_lines = {}
        self.hidd_dropdown = {}
        self.hidd_checkbox = {}
        self.hidd_boxes = set()

        self.align = kwargs["header_align"]
        self.basic_bindings()

    def event_generate(self, *args, **kwargs):
        for arg in args:
            if self.MT and arg in self.MT.event_linker:
                self.MT.event_linker[arg]()
            else:
                super().event_generate(*args, **kwargs)

    def basic_bindings(self, enable):
        if enable:
            self.bind("<Motion>", self.mouse_motion)
            self.bind("<ButtonPress-1>", self.b1_press)
            self.bind("<B1-Motion>", self.b1_motion)
            self.bind("<ButtonRelease-1>", self.b1_release)
            self.bind("<Double-Button-1>", self.double_b1)
            self.bind(rc_binding, self.rc)
            self.bind("<MouseWheel>", self.mousewheel)
            if USER_OS == "linux":
                self.bind("<Button-4>", self.mousewheel)
                self.bind("<Button-5>", self.mousewheel)
        else:
            self.unbind("<Motion>")
            self.unbind("<ButtonPress-1>")
            self.unbind("<B1-Motion>")
            self.unbind("<ButtonRelease-1>")
            self.unbind("<Double-Button-1>")
            self.unbind(rc_binding)
            self.unbind("<MouseWheel>")
            if USER_OS == "linux":
                self.unbind("<Button-4>")
                self.unbind("<Button-5>")

    def mousewheel(self, event):
        if isinstance(self.MT._headers, int):
            maxlines = max(
                (
                    len(
                        self.MT.get_valid_cell_data_as_str(self.MT._headers, datacn, get_displayed=True)
                        .rstrip()
                        .split("\n")
                    )
                    for datacn in range(len(self.MT.data[self.MT._headers]))
                ),
                default=0,
            )
        elif isinstance(self.MT._headers, (list, tuple)):
            maxlines = max(
                (
                    len(e.rstrip().split("\n")) if isinstance(e, str) else len(f"{e}".rstrip().split("\n"))
                    for e in self.MT._headers
                ),
                default=0,
            )
        if maxlines == 1:
            maxlines = 0
        if self.lines_start_at > maxlines:
            self.lines_start_at = maxlines
        if (event.delta < 0 or event.num == 5) and self.lines_start_at < maxlines:
            self.lines_start_at += 1
        elif (event.delta >= 0 or event.num == 4) and self.lines_start_at > 0:
            self.lines_start_at -= 1
        self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=False, redraw_table=False)

    def set_height(self, new_height, set_TL=False):
        """Set the height of the widget.

        Args:
            new_height (int): The new height to set for the widget.
            set_TL (bool): Whether to adjust the `TL` dimensions to match
                the new height. Defaults to False.
        """
        self.current_height = new_height
        try:
            self.config(height=new_height)
        except Exception:
            return
        if set_TL and self.TL is not None:
            self.TL.set_dimensions(new_h=new_height)

    def rc(self, event):
        self.mouseclick_outside_editor_or_dropdown_all_canvases(inside=True)
        self.focus_set()
        popup_menu = None
        if self.MT.identify_col(x=event.x, allow_end=False) is None:
            self.MT.deselect("all")
            c = len(self.MT.col_positions) - 1
            if self.MT.rc_popup_menus_enabled:
                popup_menu = self.MT.empty_rc_popup_menu
        elif self.col_selection_enabled and not self.currently_resizing_width and not self.currently_resizing_height:
            c = self.MT.identify_col(x=event.x)
            if c < len(self.MT.col_positions) - 1:
                if self.MT.col_selected(c):
                    if self.MT.rc_popup_menus_enabled:
                        popup_menu = self.ch_rc_popup_menu
                else:
                    if self.MT.single_selection_enabled and self.MT.rc_select_enabled:
                        self.select_col(c, redraw=True)
                    elif self.MT.toggle_selection_enabled and self.MT.rc_select_enabled:
                        self.toggle_select_col(c, redraw=True)
                    if self.MT.rc_popup_menus_enabled:
                        popup_menu = self.ch_rc_popup_menu
        try_binding(self.extra_rc_func, event)
        if popup_menu is not None:
            self.popup_menu_loc = c
            popup_menu.tk_popup(event.x_root, event.y_root)

    def ctrl_b1_press(self, event):
        self.mouseclick_outside_editor_or_dropdown_all_canvases(inside=True)
        if (
            (self.drag_and_drop_enabled or self.col_selection_enabled)
            and self.MT.ctrl_select_enabled
            and self.rsz_h is None
            and self.rsz_w is None
        ):
            c = self.MT.identify_col(x=event.x)
            if c < len(self.MT.col_positions) - 1:
                c_selected = self.MT.col_selected(c)
                if not c_selected and self.col_selection_enabled:
                    self.being_drawn_item = True
                    self.being_drawn_item = self.add_selection(c, set_as_current=True, run_binding_func=False)
                    self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
                    sel_event = self.MT.get_select_event(being_drawn_item=self.being_drawn_item)
                    try_binding(self.ctrl_selection_binding_func, sel_event)
                    self.PAR.emit_event("<<SheetSelect>>", data=sel_event)
                elif c_selected:
                    self.MT.deselect(c=c)
        elif not self.MT.ctrl_select_enabled:
            self.b1_press(event)

    def ctrl_shift_b1_press(self, event):
        self.mouseclick_outside_editor_or_dropdown_all_canvases(inside=True)
        x = event.x
        c = self.MT.identify_col(x=x)
        if (
            (self.drag_and_drop_enabled or self.col_selection_enabled)
            and self.MT.ctrl_select_enabled
            and self.rsz_h is None
            and self.rsz_w is None
        ):
            if c < len(self.MT.col_positions) - 1:
                c_selected = self.MT.col_selected(c)
                if not c_selected and self.col_selection_enabled:
                    if self.MT.selected and self.MT.selected.type_ == "columns":
                        self.being_drawn_item = self.MT.recreate_selection_box(
                            *self.get_shift_select_box(c, self.MT.selected.column),
                            fill_iid=self.MT.selected.fill_iid,
                        )
                    else:
                        self.being_drawn_item = self.add_selection(
                            c,
                            run_binding_func=False,
                            set_as_current=True,
                        )
                    self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
                    sel_event = self.MT.get_select_event(being_drawn_item=self.being_drawn_item)
                    try_binding(self.ctrl_selection_binding_func, sel_event)
                    self.PAR.emit_event("<<SheetSelect>>", data=sel_event)
                elif c_selected:
                    self.dragged_col = DraggedRowColumn(
                        dragged=c,
                        to_move=sorted(self.MT.get_selected_cols()),
                    )
        elif not self.MT.ctrl_select_enabled:
            self.shift_b1_press(event)

    def shift_b1_press(self, event):
        self.mouseclick_outside_editor_or_dropdown_all_canvases(inside=True)
        x = event.x
        c = self.MT.identify_col(x=x)
        if (self.drag_and_drop_enabled or self.col_selection_enabled) and self.rsz_h is None and self.rsz_w is None:
            if c < len(self.MT.col_positions) - 1:
                c_selected = self.MT.col_selected(c)
                if not c_selected and self.col_selection_enabled:
                    if self.MT.selected and self.MT.selected.type_ == "columns":
                        r_to_sel, c_to_sel = self.MT.selected.row, self.MT.selected.column
                        self.MT.deselect("all", redraw=False)
                        self.being_drawn_item = self.MT.create_selection_box(
                            *self.get_shift_select_box(c, c_to_sel), "columns"
                        )
                        self.MT.set_currently_selected(r_to_sel, c_to_sel, self.being_drawn_item)
                    else:
                        self.being_drawn_item = self.select_col(c, run_binding_func=False)
                    self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
                    sel_event = self.MT.get_select_event(being_drawn_item=self.being_drawn_item)
                    try_binding(self.shift_selection_binding_func, sel_event)
                    self.PAR.emit_event("<<SheetSelect>>", data=sel_event)
                elif c_selected:
                    self.dragged_col = DraggedRowColumn(
                        dragged=c,
                        to_move=sorted(self.MT.get_selected_cols()),
                    )

    def get_shift_select_box(self, c, min_c):
        """Determine selection box boundaries from current & minimum
        columns.

        Args:
            c (int): The current column index.
            min_c (int): The minimum column index in the selection.

        Returns:
            tuple(int, int, int, int, str): A tuple containing the top
                row index (0), the starting column index, the last row
                index (length of `MT.row_positions` - 1), and the ending
                column index.
        """
        if c > min_c:
            return 0, min_c, len(self.MT.row_positions) - 1, c + 1
        elif c < min_c:
            return 0, c, len(self.MT.row_positions) - 1, min_c + 1

    def create_resize_line(self, x1, y1, x2, y2, width, fill, tag):
        """Create or update a resize line on the canvas.

        Args:
            x1 (int): The starting x-coordinate of the line.
            y1 (int): The starting y-coordinate of the line.
            x2 (int): The ending x-coordinate of the line.
            y2 (int): The ending y-coordinate of the line.
            width (int): The width of the line.
            fill (str): The color of the line.
            tag (str or tuple of str): The tag(s) associated with the
                line.
        """
        if self.hidd_resize_lines:
            t, sh = self.hidd_resize_lines.popitem()
            self.coords(t, x1, y1, x2, y2)
            if sh:
                self.itemconfig(t, width=width, fill=fill, tag=tag)
            else:
                self.itemconfig(t, width=width, fill=fill, tag=tag, state="normal")
            self.lift(t)
        else:
            t = self.create_line(x1, y1, x2, y2, width=width, fill=fill, tag=tag)
        self.disp_resize_lines[t] = True

    def delete_resize_lines(self):
        self.hidd_resize_lines.update(self.disp_resize_lines)
        self.disp_resize_lines = {}
        for t, sh in self.hidd_resize_lines.items():
            if sh:
                self.itemconfig(t, tags=("",), state="hidden")
                self.hidd_resize_lines[t] = False

    def check_mouse_position_width_resizers(self, x, y):
        """Check if the mouse position is within the boundaries of the width resizers.

        Args:
            x (int): The x-coordinate of the mouse position.
            y (int): The y-coordinate of the mouse position.

        Returns:
            int or None: The column index if the mouse is within a width resizer,
                        otherwise None.
        """
        for c, (x1, y1, x2, y2) in self.visible_col_dividers.items():
            if x >= x1 and y >= y1 and x <= x2 and y <= y2:
                return c

    def mouse_motion(self, event):
        if not self.currently_resizing_height and not self.currently_resizing_width:
            x = self.canvasx(event.x)
            y = self.canvasy(event.y)
            mouse_over_resize = False
            mouse_over_selected = False
            if self.width_resizing_enabled:
                c = self.check_mouse_position_width_resizers(x, y)
                if c is not None:
                    self.rsz_w, mouse_over_resize = c, True
                    if self.MT.current_cursor != "sb_h_double_arrow":
                        self.config(cursor="sb_h_double_arrow")
                        self.MT.current_cursor = "sb_h_double_arrow"
                else:
                    self.rsz_w = None
            if self.height_resizing_enabled and not mouse_over_resize:
                try:
                    x1, y1, x2, y2 = (
                        self.col_height_resize_bbox[0],
                        self.col_height_resize_bbox[1],
                        self.col_height_resize_bbox[2],
                        self.col_height_resize_bbox[3],
                    )
                    if x >= x1 and y >= y1 and x <= x2 and y <= y2:
                        self.rsz_h, mouse_over_resize = True, True
                        if self.MT.current_cursor != "sb_v_double_arrow":
                            self.config(cursor="sb_v_double_arrow")
                            self.MT.current_cursor = "sb_v_double_arrow"
                    else:
                        self.rsz_h = None
                except Exception:
                    self.rsz_h = None
            if not mouse_over_resize:
                if self.MT.col_selected(self.MT.identify_col(event, allow_end=False)):
                    mouse_over_selected = True
                    if self.MT.current_cursor != "hand2":
                        self.config(cursor="hand2")
                        self.MT.current_cursor = "hand2"
            if not mouse_over_resize and not mouse_over_selected:
                self.MT.reset_mouse_motion_creations()
        try_binding(self.extra_motion_func, event)

    def double_b1(self, event):
        self.mouseclick_outside_editor_or_dropdown_all_canvases(inside=True)
        self.focus_set()
        if (
            self.double_click_resizing_enabled
            and self.width_resizing_enabled
            and self.rsz_w is not None
            and not self.currently_resizing_width
        ):
            col = self.rsz_w - 1
            old_width = self.MT.col_positions[self.rsz_w] - self.MT.col_positions[self.rsz_w - 1]
            new_width = self.set_col_width(col)
            self.MT.allow_auto_resize_columns = False
            self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
            if self.column_width_resize_func is not None and old_width != new_width:
                self.column_width_resize_func(
                    event_dict(
                        name="resize",
                        sheet=self.PAR.name,
                        resized_columns={col: {"old_size": old_width, "new_size": new_width}},
                    )
                )
        elif self.col_selection_enabled and self.rsz_h is None and self.rsz_w is None:
            c = self.MT.identify_col(x=event.x)
            if c < len(self.MT.col_positions) - 1:
                if self.MT.single_selection_enabled:
                    self.select_col(c, redraw=True)
                elif self.MT.toggle_selection_enabled:
                    self.toggle_select_col(c, redraw=True)
                datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
                if (
                    self.get_cell_kwargs(datacn, key="dropdown")
                    or self.get_cell_kwargs(datacn, key="checkbox")
                    or self.edit_cell_enabled
                ):
                    self.open_cell(event)
        self.rsz_w = None
        self.mouse_motion(event)
        try_binding(self.extra_double_b1_func, event)

    def b1_press(self, event):
        self.MT.unbind("<MouseWheel>")
        self.focus_set()
        self.closed_dropdown = self.mouseclick_outside_editor_or_dropdown_all_canvases(inside=True)
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        c = self.MT.identify_col(x=event.x)
        self.b1_pressed_loc = c
        if self.check_mouse_position_width_resizers(x, y) is None:
            self.rsz_w = None
        if self.width_resizing_enabled and self.rsz_w is not None:
            x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
            self.currently_resizing_width = True
            x = self.MT.col_positions[self.rsz_w]
            line2x = self.MT.col_positions[self.rsz_w - 1]
            self.create_resize_line(
                x,
                0,
                x,
                self.current_height,
                width=1,
                fill=self.PAR.ops.resizing_line_fg,
                tag="rwl",
            )
            self.MT.create_resize_line(x, y1, x, y2, width=1, fill=self.PAR.ops.resizing_line_fg, tag="rwl")
            self.create_resize_line(
                line2x,
                0,
                line2x,
                self.current_height,
                width=1,
                fill=self.PAR.ops.resizing_line_fg,
                tag="rwl2",
            )
            self.MT.create_resize_line(line2x, y1, line2x, y2, width=1, fill=self.PAR.ops.resizing_line_fg, tag="rwl2")
        elif self.height_resizing_enabled and self.rsz_w is None and self.rsz_h is not None:
            x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
            self.currently_resizing_height = True
            y = event.y
            if y < self.MT.min_header_height:
                y = int(self.MT.min_header_height)
            self.new_col_height = y
        elif self.MT.identify_col(x=event.x, allow_end=False) is None:
            self.MT.deselect("all")
        elif self.col_selection_enabled and self.rsz_w is None and self.rsz_h is None:
            if c < len(self.MT.col_positions) - 1:
                datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
                if (
                    self.MT.col_selected(c)
                    and not self.event_over_dropdown(c, datacn, event, x)
                    and not self.event_over_checkbox(c, datacn, event, x)
                ):
                    self.dragged_col = DraggedRowColumn(
                        dragged=c,
                        to_move=sorted(self.MT.get_selected_cols()),
                    )
                else:
                    if self.MT.single_selection_enabled:
                        self.being_drawn_item = True
                        self.being_drawn_item = self.select_col(c, redraw=True)
                    elif self.MT.toggle_selection_enabled:
                        self.toggle_select_col(c, redraw=True)
        try_binding(self.extra_b1_press_func, event)

    def b1_motion(self, event):
        x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
        if self.width_resizing_enabled and self.rsz_w is not None and self.currently_resizing_width:
            x = self.canvasx(event.x)
            size = x - self.MT.col_positions[self.rsz_w - 1]
            if size >= self.MT.min_column_width and size < self.MT.max_column_width:
                self.hide_resize_and_ctrl_lines(ctrl_lines=False)
                line2x = self.MT.col_positions[self.rsz_w - 1]
                self.create_resize_line(
                    x,
                    0,
                    x,
                    self.current_height,
                    width=1,
                    fill=self.PAR.ops.resizing_line_fg,
                    tag="rwl",
                )
                self.MT.create_resize_line(x, y1, x, y2, width=1, fill=self.PAR.ops.resizing_line_fg, tag="rwl")
                self.create_resize_line(
                    line2x,
                    0,
                    line2x,
                    self.current_height,
                    width=1,
                    fill=self.PAR.ops.resizing_line_fg,
                    tag="rwl2",
                )
                self.MT.create_resize_line(
                    line2x,
                    y1,
                    line2x,
                    y2,
                    width=1,
                    fill=self.PAR.ops.resizing_line_fg,
                    tag="rwl2",
                )
                self.drag_width_resize()
        elif self.height_resizing_enabled and self.rsz_h is not None and self.currently_resizing_height:
            evy = event.y
            if evy > self.current_height:
                y = self.MT.canvasy(evy - self.current_height)
                if evy > self.MT.max_header_height:
                    evy = int(self.MT.max_header_height)
                    y = self.MT.canvasy(evy - self.current_height)
                self.new_col_height = evy
            else:
                y = evy
                if y < self.MT.min_header_height:
                    y = int(self.MT.min_header_height)
                self.new_col_height = y
            self.drag_height_resize()
        elif (
            self.drag_and_drop_enabled
            and self.col_selection_enabled
            and self.MT.anything_selected(exclude_cells=True, exclude_rows=True)
            and self.rsz_h is None
            and self.rsz_w is None
            and self.dragged_col is not None
        ):
            x = self.canvasx(event.x)
            if x > 0:
                self.show_drag_and_drop_indicators(
                    self.drag_and_drop_motion(event),
                    y1,
                    y2,
                    self.dragged_col.to_move,
                )
        elif (
            self.MT.drag_selection_enabled and self.col_selection_enabled and self.rsz_h is None and self.rsz_w is None
        ):
            need_redraw = False
            end_col = self.MT.identify_col(x=event.x)
            if end_col < len(self.MT.col_positions) - 1 and self.MT.selected:
                if self.MT.selected.type_ == "columns":
                    box = self.get_b1_motion_box(self.MT.selected.column, end_col)
                    if (
                        box is not None
                        and self.being_drawn_item is not None
                        and self.MT.coords_and_type(self.being_drawn_item) != box
                    ):
                        if box[3] - box[1] != 1:
                            self.being_drawn_item = self.MT.recreate_selection_box(
                                *box[:-1],
                                fill_iid=self.MT.selected.fill_iid,
                            )
                        else:
                            self.being_drawn_item = self.select_col(self.MT.selected.column, run_binding_func=False)
                        need_redraw = True
                        sel_event = self.MT.get_select_event(being_drawn_item=self.being_drawn_item)
                        try_binding(self.drag_selection_binding_func, sel_event)
                        self.PAR.emit_event("<<SheetSelect>>", data=sel_event)
                if self.scroll_if_event_offscreen(event):
                    need_redraw = True
            if need_redraw:
                self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=False)
        try_binding(self.extra_b1_motion_func, event)

    def drag_height_resize(self):
        self.set_height(self.new_col_height, set_TL=True)
        self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)

    def get_b1_motion_box(self, start_col, end_col):
        """Determine the motion box based on the starting and ending
        columns.

        Args:
            start_col (int): The starting column index.
            end_col (int): The ending column index.

        Returns:
            tuple(int, int, int, int, Literal["columns"]): A tuple containing:
                - The top row index (always 0).
                - The starting column index.
                - The last row index (length of `MT.row_positions` - 1).
                - The ending column index (incremented by 1).
                - A literal string "columns".
        """
        if end_col >= start_col:
            return 0, start_col, len(self.MT.row_positions) - 1, end_col + 1, "columns"
        elif end_col < start_col:
            return 0, end_col, len(self.MT.row_positions) - 1, start_col + 1, "columns"

    def ctrl_b1_motion(self, event):
        x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
        if (
            self.drag_and_drop_enabled
            and self.col_selection_enabled
            and self.MT.anything_selected(exclude_cells=True, exclude_rows=True)
            and self.rsz_h is None
            and self.rsz_w is None
            and self.dragged_col is not None
        ):
            x = self.canvasx(event.x)
            if x > 0:
                self.show_drag_and_drop_indicators(
                    self.drag_and_drop_motion(event),
                    y1,
                    y2,
                    self.dragged_col.to_move,
                )
        elif (
            self.MT.ctrl_select_enabled
            and self.MT.drag_selection_enabled
            and self.col_selection_enabled
            and self.rsz_h is None
            and self.rsz_w is None
        ):
            need_redraw = False
            end_col = self.MT.identify_col(x=event.x)
            if end_col < len(self.MT.col_positions) - 1 and self.MT.selected:
                if self.MT.selected.type_ == "columns":
                    box = self.get_b1_motion_box(self.MT.selected.column, end_col)
                    if (
                        box is not None
                        and self.being_drawn_item is not None
                        and self.MT.coords_and_type(self.being_drawn_item) != box
                    ):
                        if box[3] - box[1] != 1:
                            self.being_drawn_item = self.MT.recreate_selection_box(
                                *box[:-1],
                                self.MT.selected.fill_iid,
                            )
                        else:
                            self.MT.hide_selection_box(self.MT.selected.fill_iid)
                            self.being_drawn_item = self.add_selection(box[1], run_binding_func=False)
                        need_redraw = True
                        sel_event = self.MT.get_select_event(being_drawn_item=self.being_drawn_item)
                        try_binding(self.drag_selection_binding_func, sel_event)
                        self.PAR.emit_event("<<SheetSelect>>", data=sel_event)
                if self.scroll_if_event_offscreen(event):
                    need_redraw = True
            if need_redraw:
                self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=False)
        elif not self.MT.ctrl_select_enabled:
            self.b1_motion(event)

    def drag_and_drop_motion(self, event):
        """Handle the drag and drop motion for a table.

        Args:
            event (object): The event object containing information about the 
                            drag-and-drop action.

        Returns:
            float: The new x-coordinate of the dragged column, or the x-coordinate
                   of the nearest column edge if within a specified range.
        """
        x = event.x
        wend = self.winfo_width()
        xcheck = self.xview()
        if x >= wend - 0 and len(xcheck) > 1 and xcheck[1] < 1:
            if x >= wend + 15:
                self.MT.xview_scroll(2, "units")
                self.xview_scroll(2, "units")
            else:
                self.MT.xview_scroll(1, "units")
                self.xview_scroll(1, "units")
            self.fix_xview()
            self.MT.x_move_synced_scrolls("moveto", self.MT.xview()[0])
            self.MT.main_table_redraw_grid_and_text(redraw_header=True)
        elif x <= 0 and len(xcheck) > 1 and xcheck[0] > 0:
            if x >= -15:
                self.MT.xview_scroll(-1, "units")
                self.xview_scroll(-1, "units")
            else:
                self.MT.xview_scroll(-2, "units")
                self.xview_scroll(-2, "units")
            self.fix_xview()
            self.MT.x_move_synced_scrolls("moveto", self.MT.xview()[0])
            self.MT.main_table_redraw_grid_and_text(redraw_header=True)
        col = self.MT.identify_col(x=x)
        if col == len(self.MT.col_positions) - 1:
            col -= 1
        if col >= self.dragged_col.to_move[0] and col <= self.dragged_col.to_move[-1]:
            if is_contiguous(self.dragged_col.to_move):
                return self.MT.col_positions[self.dragged_col.to_move[0]]
            return self.MT.col_positions[col]
        elif col > self.dragged_col.to_move[-1]:
            return self.MT.col_positions[col + 1]
        return self.MT.col_positions[col]

    def show_drag_and_drop_indicators(self, xpos, y1, y2, cols):
        """Display drag-and-drop indicators for specified columns.

        Args:
            xpos (float): The x-coordinate where the indicators should be shown.
            y1 (float): The starting y-coordinate for the indicators.
            y2 (float): The ending y-coordinate for the indicators.
            cols (Sequence[int]): A sequence of column indices for which the 
                                  indicators should be displayed.
        """
        self.hide_resize_and_ctrl_lines()
        self.create_resize_line(
            xpos,
            0,
            xpos,
            self.current_height,
            width=3,
            fill=self.PAR.ops.drag_and_drop_bg,
            tag="move_columns",
        )
        self.MT.create_resize_line(xpos, y1, xpos, y2, width=3, fill=self.PAR.ops.drag_and_drop_bg, tag="move_columns")
        for boxst, boxend in consecutive_ranges(cols):
            self.MT.show_ctrl_outline(
                start_cell=(boxst, 0),
                end_cell=(boxend, len(self.MT.row_positions) - 1),
                dash=(),
                outline=self.PAR.ops.drag_and_drop_bg,
                delete_on_timer=False,
            )

    def hide_resize_and_ctrl_lines(self, ctrl_lines=True):
        """Hide resize lines and control outlines if specified.

        Args:
            ctrl_lines (bool, optional): If True, control outlines will also 
                                          be hidden. Defaults to True.
        """
        self.delete_resize_lines()
        self.MT.delete_resize_lines()
        if ctrl_lines:
            self.MT.delete_ctrl_outlines()

    def scroll_if_event_offscreen(self, event):
        """Scroll the view if the event occurs off-screen.

        Args:
            event (object): The event object containing the x-coordinate 
                            of the mouse event.

        Returns:
            bool: True if a redraw is needed, False otherwise.
        """
        xcheck = self.xview()
        need_redraw = False
        if event.x > self.winfo_width() and len(xcheck) > 1 and xcheck[1] < 1:
            try:
                self.MT.xview_scroll(1, "units")
                self.xview_scroll(1, "units")
            except Exception:
                pass
            self.fix_xview()
            self.MT.x_move_synced_scrolls("moveto", self.MT.xview()[0])
            need_redraw = True
        elif event.x < 0 and self.canvasx(self.winfo_width()) > 0 and xcheck and xcheck[0] > 0:
            try:
                self.xview_scroll(-1, "units")
                self.MT.xview_scroll(-1, "units")
            except Exception:
                pass
            self.fix_xview()
            self.MT.x_move_synced_scrolls("moveto", self.MT.xview()[0])
            need_redraw = True
        return need_redraw

    def fix_xview(self):
        xcheck = self.xview()
        if xcheck and xcheck[0] < 0:
            self.MT.set_xviews("moveto", 0)
        elif len(xcheck) > 1 and xcheck[1] > 1:
            self.MT.set_xviews("moveto", 1)

    def event_over_dropdown(self, c, datacn, event, canvasx):
        """Determine if the event is over a dropdown.

        Args:
            c (int): The column index of the dropdown.
            datacn (int): The data column index.
            event (object): The event object associated with the mouse event.
            canvasx (float): The x-coordinate in canvas coordinates.

        Returns:
            bool: True if the event occurs over the dropdown, False otherwise.
        """
        if (
            event.y < self.MT.header_txt_height + 5
            and self.get_cell_kwargs(datacn, key="dropdown")
            and canvasx < self.MT.col_positions[c + 1]
            and canvasx > self.MT.col_positions[c + 1] - self.MT.header_txt_height - 4
        ):
            return True
        return False

    def event_over_checkbox(self, c, datacn, event, canvasx):
        """Check if the event occurs over a checkbox.

        Args:
            c (int): The column index of the checkbox.
            datacn (int): The data column index.
            event (object): The event object associated with the mouse event.
            canvasx (float): The x-coordinate in canvas coordinates.

        Returns:
            bool: True if the event occurs over the checkbox, False otherwise.
        """
        if (
            event.y < self.MT.header_txt_height + 5
            and self.get_cell_kwargs(datacn, key="checkbox")
            and canvasx < self.MT.col_positions[c] + self.MT.header_txt_height + 4
        ):
            return True
        return False

    def drag_width_resize(self):
        new_col_pos = int(self.coords("rwl")[0])
        old_width = self.MT.col_positions[self.rsz_w] - self.MT.col_positions[self.rsz_w - 1]
        size = new_col_pos - self.MT.col_positions[self.rsz_w - 1]
        if size < self.MT.min_column_width:
            new_col_pos = ceil(self.MT.col_positions[self.rsz_w - 1] + self.MT.min_column_width)
        elif size > self.MT.max_column_width:
            new_col_pos = floor(self.MT.col_positions[self.rsz_w - 1] + self.MT.max_column_width)
        increment = new_col_pos - self.MT.col_positions[self.rsz_w]
        self.MT.col_positions[self.rsz_w + 1 :] = [
            e + increment for e in islice(self.MT.col_positions, self.rsz_w + 1, None)
        ]
        self.MT.col_positions[self.rsz_w] = new_col_pos
        new_width = self.MT.col_positions[self.rsz_w] - self.MT.col_positions[self.rsz_w - 1]
        self.MT.allow_auto_resize_columns = False
        self.MT.recreate_all_selection_boxes()
        self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
        if self.column_width_resize_func is not None and old_width != new_width:
            self.column_width_resize_func(
                event_dict(
                    name="resize",
                    sheet=self.PAR.name,
                    resized_columns={self.rsz_w - 1: {"old_size": old_width, "new_size": new_width}},
                )
            )

    def b1_release(self, event):
        if self.being_drawn_item is not None and (to_sel := self.MT.coords_and_type(self.being_drawn_item)):
            r_to_sel, c_to_sel = self.MT.selected.row, self.MT.selected.column
            self.MT.hide_selection_box(self.being_drawn_item)
            self.MT.set_currently_selected(
                r_to_sel,
                c_to_sel,
                item=self.MT.create_selection_box(*to_sel, set_current=False),
            )
            sel_event = self.MT.get_select_event(being_drawn_item=self.being_drawn_item)
            try_binding(self.drag_selection_binding_func, sel_event)
            self.PAR.emit_event("<<SheetSelect>>", data=sel_event)
        else:
            self.being_drawn_item = None
        self.MT.bind("<MouseWheel>", self.MT.mousewheel)
        if self.width_resizing_enabled and self.rsz_w is not None and self.currently_resizing_width:
            self.drag_width_resize()
            self.currently_resizing_width = False
            self.hide_resize_and_ctrl_lines(ctrl_lines=False)
        elif self.height_resizing_enabled and self.rsz_h is not None and self.currently_resizing_height:
            self.currently_resizing_height = False
            self.drag_height_resize()
        elif (
            self.drag_and_drop_enabled
            and self.col_selection_enabled
            and self.MT.anything_selected(exclude_cells=True, exclude_rows=True)
            and self.rsz_h is None
            and self.rsz_w is None
            and self.dragged_col is not None
            and self.find_withtag("move_columns")
        ):
            self.hide_resize_and_ctrl_lines()
            c = self.MT.identify_col(x=event.x)
            totalcols = len(self.dragged_col.to_move)
            if (
                c is not None
                and totalcols != len(self.MT.col_positions) - 1
                and not (
                    c >= self.dragged_col.to_move[0]
                    and c <= self.dragged_col.to_move[-1]
                    and is_contiguous(self.dragged_col.to_move)
                )
            ):
                if c > self.dragged_col.to_move[-1]:
                    c += 1
                if c > len(self.MT.col_positions) - 1:
                    c = len(self.MT.col_positions) - 1
                event_data = event_dict(
                    name="move_columns",
                    sheet=self.PAR.name,
                    widget=self,
                    boxes=self.MT.get_boxes(),
                    selected=self.MT.selected,
                    value=c,
                )
                if try_binding(self.ch_extra_begin_drag_drop_func, event_data, "begin_move_columns"):
                    data_new_idxs, disp_new_idxs, event_data = self.MT.move_columns_adjust_options_dict(
                        *self.MT.get_args_for_move_columns(
                            move_to=c,
                            to_move=self.dragged_col.to_move,
                        ),
                        move_data=self.PAR.ops.column_drag_and_drop_perform,
                        move_widths=self.PAR.ops.column_drag_and_drop_perform,
                        event_data=event_data,
                    )
                    event_data["moved"]["columns"] = {
                        "data": data_new_idxs,
                        "displayed": disp_new_idxs,
                    }
                    if self.MT.undo_enabled:
                        self.MT.undo_stack.append(pickled_event_dict(event_data))
                    self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
                    try_binding(self.ch_extra_end_drag_drop_func, event_data, "end_move_columns")
                    self.MT.sheet_modified(event_data)
        elif self.b1_pressed_loc is not None and self.rsz_w is None and self.rsz_h is None:
            c = self.MT.identify_col(x=event.x)
            if (
                c is not None
                and c < len(self.MT.col_positions) - 1
                and c == self.b1_pressed_loc
                and self.b1_pressed_loc != self.closed_dropdown
            ):
                datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
                canvasx = self.canvasx(event.x)
                if self.event_over_dropdown(
                    c,
                    datacn,
                    event,
                    canvasx,
                ) or self.event_over_checkbox(
                    c,
                    datacn,
                    event,
                    canvasx,
                ):
                    self.open_cell(event)
            else:
                self.mouseclick_outside_editor_or_dropdown_all_canvases(inside=True)
            self.b1_pressed_loc = None
            self.closed_dropdown = None
        self.dragged_col = None
        self.currently_resizing_width = False
        self.currently_resizing_height = False
        self.rsz_w = None
        self.rsz_h = None
        self.mouse_motion(event)
        try_binding(self.extra_b1_release_func, event)

    def toggle_select_col(
        self, column, add_selection=True, redraw=True, 
        run_binding_func=True, set_as_current=True, ext=False
    ):
        """Toggle the selection state of a specified column.

        Args:
            column (int): The index of the column to toggle.
            add_selection (bool, optional): Whether to add the column to 
                the selection. Defaults to True.
            redraw (bool, optional): Whether to redraw the column. 
                Defaults to True.
            run_binding_func (bool, optional): Whether to run the binding 
                function. Defaults to True.
            set_as_current (bool, optional): Whether to set the column as 
                the current column. Defaults to True.
            ext (bool, optional): Additional parameter for external 
                handling. Defaults to False.

        Returns:
            int: The fill identifier for the column selection.
        """
        if add_selection:
            if self.MT.col_selected(column):
                fill_iid = self.MT.deselect(c=column, redraw=redraw)
            else:
                fill_iid = self.add_selection(
                    c=column,
                    redraw=redraw,
                    run_binding_func=run_binding_func,
                    set_as_current=set_as_current,
                    ext=ext,
                )
        else:
            if self.MT.col_selected(column):
                fill_iid = self.MT.deselect(c=column, redraw=redraw)
            else:
                fill_iid = self.select_col(column, redraw=redraw, ext=ext)
        return fill_iid

    def select_col(
        self, c, redraw=False, run_binding_func=True, ext=False
    ):
        """Select a specified column and manage the visibility of selection boxes.

        Args:
            c (int): The index of the column to select.
            redraw (bool, optional): Whether to redraw the main table. 
                Defaults to False.
            run_binding_func (bool, optional): Whether to execute the 
                selection binding function. Defaults to True.
            ext (bool, optional): Additional parameter for external 
                handling. Defaults to False.

        Returns:
            int: The fill identifier for the selection box.
        """
        boxes_to_hide = tuple(self.MT.selection_boxes)
        fill_iid = self.MT.create_selection_box(0, c, len(self.MT.row_positions) - 1, c + 1, "columns", ext=ext)
        for iid in boxes_to_hide:
            self.MT.hide_selection_box(iid)
        if redraw:
            self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
        if run_binding_func:
            self.MT.run_selection_binding("columns")
        return fill_iid

    def add_selection(
        self, c, redraw=False, run_binding_func=True, set_as_current=True, ext=False
    ):
        """Add a selection box for the specified column.

        Args:
            c (int): The index of the column to add a selection for.
            redraw (bool, optional): Whether to redraw the main table.
                Defaults to False.
            run_binding_func (bool, optional): Whether to execute the 
                selection binding function. Defaults to True.
            set_as_current (bool, optional): Whether to set the selection 
                as the current one. Defaults to True.
            ext (bool, optional): Additional parameter for external 
                handling. Defaults to False.

        Returns:
            int: The fill identifier for the selection box.
        """
        box = (0, c, len(self.MT.row_positions) - 1, c + 1, "columns")
        fill_iid = self.MT.create_selection_box(*box, set_current=set_as_current, ext=ext)
        if redraw:
            self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
        if run_binding_func:
            self.MT.run_selection_binding("columns")
        return fill_iid

    def display_box(
        self, x1, y1, x2, y2, fill, outline, state, tags, iid=None
    ):
        """Display a rounded or rectangular box on the canvas.

        Args:
            x1 (int): The x-coordinate of the top-left corner.
            y1 (int): The y-coordinate of the top-left corner.
            x2 (int): The x-coordinate of the bottom-right corner.
            y2 (int): The y-coordinate of the bottom-right corner.
            fill (str): The fill color of the box.
            outline (str): The outline color of the box.
            state (str): The state of the box (e.g., 'normal' or 'hidden').
            tags (Union[str, Tuple[str]]): Tags to associate with the box.
            iid (Optional[int]): The identifier of the box to update. 
                Defaults to None.

        Returns:
            int: The identifier for the displayed box.
        """
        coords = rounded_box_coords(
            x1,
            y1,
            x2,
            y2,
            radius=5 if self.PAR.ops.rounded_boxes else 0,
        )
        if isinstance(iid, int):
            self.coords(iid, coords)
            self.itemconfig(iid, fill=fill, outline=outline, state=state, tags=tags)
        else:
            if self.hidd_boxes:
                iid = self.hidd_boxes.pop()
                self.coords(iid, coords)
                self.itemconfig(iid, fill=fill, outline=outline, state=state, tags=tags)
            else:
                iid = self.create_polygon(coords, fill=fill, outline=outline, state=state, tags=tags, smooth=True)
            self.disp_boxes.add(iid)
        return iid

    def hide_box(self, item):
        """Hide a box by changing its state to 'hidden' and managing its 
        visibility tracking.

        Args:
            item (int): The identifier of the box to hide.
        """
        if isinstance(item, int):
            self.disp_boxes.discard(item)
            self.hidd_boxes.add(item)
            self.itemconfig(item, state="hidden")

    def get_cell_dimensions(self, datacn):
        """Retrieve the dimensions of a cell based on its data connection.

        This method measures the width and height of the cell's text,
        accounting for dropdowns and checkboxes if applicable.

        Args:
            datacn (int): The data connection identifier for the cell.

        Returns:
            tuple: A tuple containing the width and height of the cell,
            where the width includes extra space if the cell has a
            dropdown or checkbox.
        """
        txt = self.get_valid_cell_data_as_str(datacn, fix=False)
        if txt:
            self.MT.txt_measure_canvas.itemconfig(
                self.MT.txt_measure_canvas_text,
                text=txt,
                font=self.PAR.ops.header_font,
            )
            b = self.MT.txt_measure_canvas.bbox(self.MT.txt_measure_canvas_text)
            w = b[2] - b[0] + 7
            h = b[3] - b[1] + 5
        else:
            w = self.MT.min_column_width
            h = self.MT.min_header_height
        if datacn in self.cell_options and (
            self.get_cell_kwargs(datacn, key="dropdown") or self.get_cell_kwargs(datacn, key="checkbox")
        ):
            return w + self.MT.header_txt_height, h
        return w, h

    def set_height_of_header_to_text(self, text=None, only_if_too_small=False):
        """Set the height of the header to match the text height.

        This method adjusts the height of the header based on the
        specified text, but only updates it if the current height is
        too small, unless specified otherwise.

        Args:
            text (str, optional): The text to measure for height adjustment.
            only_if_too_small (bool, optional): If True, only adjust
            the height if the current height is smaller than the measured
            text height.

        Returns:
            int: The new height of the header after adjustment.
        """
        h = self.MT.min_header_height
        if (text is None and not self.MT._headers and isinstance(self.MT._headers, list)) or (
            isinstance(self.MT._headers, int) and self.MT._headers >= len(self.MT.data)
        ):
            return h
        self.fix_header()
        qconf = self.MT.txt_measure_canvas.itemconfig
        qbbox = self.MT.txt_measure_canvas.bbox
        qtxtm = self.MT.txt_measure_canvas_text
        qfont = self.PAR.ops.header_font
        default_header_height = self.MT.get_default_header_height()
        if text is not None and text:
            qconf(qtxtm, text=text, font=qfont)
            b = qbbox(qtxtm)
            if (th := b[3] - b[1] + 5) > h:
                h = th
        elif text is None:
            if self.MT.all_columns_displayed:
                if isinstance(self.MT._headers, list):
                    iterable = range(len(self.MT._headers))
                else:
                    iterable = range(len(self.MT.data[self.MT._headers]))
            else:
                iterable = self.MT.displayed_columns
            if (
                isinstance(self.MT._headers, list)
                and (th := max(map(itemgetter(0), map(self.get_cell_dimensions, iterable)), default=h)) > h
            ):
                h = th
            elif isinstance(self.MT._headers, int):
                datarn = self.MT._headers
                for datacn in iterable:
                    if txt := self.MT.get_valid_cell_data_as_str(datarn, datacn, get_displayed=True):
                        qconf(qtxtm, text=txt, font=qfont)
                        b = qbbox(qtxtm)
                        th = b[3] - b[1] + 5
                    else:
                        th = default_header_height
                    if th > h:
                        h = th
        space_bot = self.MT.get_space_bot(0)
        if h > space_bot and space_bot > self.MT.min_header_height:
            h = space_bot
        if h < self.MT.min_header_height:
            h = int(self.MT.min_header_height)
        elif h > self.MT.max_header_height:
            h = int(self.MT.max_header_height)
        if not only_if_too_small or (only_if_too_small and h > self.current_height):
            self.set_height(h, set_TL=True)
            self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=True)
        return h

    def get_col_text_width(self, col, visible_only=False, only_if_too_small=False):
        """Get the width of the text in a specified column.

        This method calculates the width of the text for a specified
        column. It can consider only the visible cells if requested
        and can also restrict the adjustment to cases where the width
        is too small.

        Args:
            col (int): The index of the column to measure.
            visible_only (bool, optional): If True, measure only the
            text in visible rows.
            only_if_too_small (bool, optional): If True, adjust the
            width only if the current width is smaller than the
            measured text width.

        Returns:
            int: The width of the text in the specified column.
        """
        self.fix_header()
        w = self.MT.min_column_width
        datacn = col if self.MT.all_columns_displayed else self.MT.displayed_columns[col]
        # header
        hw, hh_ = self.get_cell_dimensions(datacn)
        # table
        if self.MT.data:
            if self.MT.all_rows_displayed:
                if visible_only:
                    iterable = range(*self.MT.visible_text_rows)
                else:
                    iterable = range(0, len(self.MT.data))
            else:
                if visible_only:
                    start_row, end_row = self.MT.visible_text_rows
                else:
                    start_row, end_row = 0, len(self.MT.displayed_rows)
                iterable = self.MT.displayed_rows[start_row:end_row]
            qconf = self.MT.txt_measure_canvas.itemconfig
            qbbox = self.MT.txt_measure_canvas.bbox
            qtxtm = self.MT.txt_measure_canvas_text
            qtxth = self.MT.table_txt_height
            qfont = self.PAR.ops.table_font
            for datarn in iterable:
                if txt := self.MT.get_valid_cell_data_as_str(datarn, datacn, get_displayed=True):
                    qconf(qtxtm, text=txt, font=qfont)
                    b = qbbox(qtxtm)
                    if (
                        self.MT.get_cell_kwargs(datarn, datacn, key="dropdown")
                        or self.MT.get_cell_kwargs(datarn, datacn, key="checkbox")
                    ) and (tw := b[2] - b[0] + qtxth + 7) > w:
                        w = tw
                    elif (tw := b[2] - b[0] + 7) > w:
                        w = tw
        if hw > w:
            w = hw
        if only_if_too_small and w < self.MT.col_positions[col + 1] - self.MT.col_positions[col]:
            w = self.MT.col_positions[col + 1] - self.MT.col_positions[col]
        if w <= self.MT.min_column_width:
            w = int(self.MT.min_column_width)
        elif w > self.MT.max_column_width:
            w = int(self.MT.max_column_width)
        return w

    def set_col_width(self, col, width=None, only_if_too_small=False, visible_only=False, recreate=True):
        """Set the width of a specified column.

        This method sets the width for a given column, adjusting it 
        based on the text content or other parameters provided. The 
        width can be set only if it is currently too small if 
        specified. Optionally, only visible rows can be considered 
        for the width calculation.

        Args:
            col (int): The index of the column to set the width for.
            width (int, optional): The desired width to set for the column.
            only_if_too_small (bool, optional): If True, set the width 
            only if the current width is smaller than the desired width.
            visible_only (bool, optional): If True, consider only the 
            text in visible rows for width calculations.
            recreate (bool, optional): If True, recreate the column 
            after adjusting the width.

        Returns:
            int: The final width set for the specified column.
        """
        if width is None:
            width = self.get_col_text_width(col=col, visible_only=visible_only)
        if width <= self.MT.min_column_width:
            width = int(self.MT.min_column_width)
        elif width > self.MT.max_column_width:
            width = int(self.MT.max_column_width)
        if only_if_too_small and width <= self.MT.col_positions[col + 1] - self.MT.col_positions[col]:
            return self.MT.col_positions[col + 1] - self.MT.col_positions[col]
        new_col_pos = self.MT.col_positions[col] + width
        increment = new_col_pos - self.MT.col_positions[col + 1]
        self.MT.col_positions[col + 2 :] = [
            e + increment for e in islice(self.MT.col_positions, col + 2, len(self.MT.col_positions))
        ]
        self.MT.col_positions[col + 1] = new_col_pos
        if recreate:
            self.MT.recreate_all_selection_boxes()
        return width

    def set_width_of_all_cols(self, width=None, only_if_too_small=False, recreate=True):
        """Set the width for all columns.

        This method sets the width for each column in the table, either 
        to a specified width or calculates it based on the content. The 
        width can be set only if it is currently too small if specified.

        Args:
            width (int, optional): The desired width to set for all columns.
            only_if_too_small (bool, optional): If True, set the width 
            only if the current width is smaller than the desired width.
            recreate (bool, optional): If True, recreate the columns 
            after adjusting the widths.

        Returns:
            None
        """
        if width is None:
            if self.MT.all_columns_displayed:
                iterable = range(self.MT.total_data_cols())
            else:
                iterable = range(len(self.MT.displayed_columns))
            self.MT.set_col_positions(
                itr=(self.get_col_text_width(cn, only_if_too_small=only_if_too_small) for cn in iterable)
            )
        elif width is not None:
            if self.MT.all_columns_displayed:
                self.MT.set_col_positions(itr=repeat(width, self.MT.total_data_cols()))
            else:
                self.MT.set_col_positions(itr=repeat(width, len(self.MT.displayed_columns)))
        if recreate:
            self.MT.recreate_all_selection_boxes()

    def redraw_highlight_get_text_fg(
        self, fc, sc, c, c_2, c_3, selections, datacn
    ):
        """Redraw the highlight and determine the text foreground color.

        This method checks for highlights and redraws the corresponding
        elements based on the current selections. It calculates the fill
        color and returns the text foreground color along with a flag
        indicating if redrawing occurred.

        Args:
            fc (float): The first coordinate for the highlight.
            sc (float): The second coordinate for the highlight.
            c (int): The current column index.
            c_2 (str): The second color in hex format.
            c_3 (str): The third color in hex format.
            selections (dict): A dictionary containing selected columns and cells.
            datacn (int): The data column number.

        Returns:
            tuple: A tuple containing the text foreground color (str) and
            a boolean indicating if redrawing occurred.
        """
        redrawn = False
        kwargs = self.get_cell_kwargs(datacn, key="highlight")
        if kwargs:
            if kwargs[0] is not None:
                c_1 = kwargs[0] if kwargs[0].startswith("#") else color_map[kwargs[0]]
            if "columns" in selections and c in selections["columns"]:
                tf = (
                    self.PAR.ops.header_selected_columns_fg
                    if kwargs[1] is None or self.PAR.ops.display_selected_fg_over_highlights
                    else kwargs[1]
                )
                if kwargs[0] is not None:
                    fill = (
                        f"#{int((int(c_1[1:3], 16) + int(c_3[1:3], 16)) / 2):02X}"
                        + f"{int((int(c_1[3:5], 16) + int(c_3[3:5], 16)) / 2):02X}"
                        + f"{int((int(c_1[5:], 16) + int(c_3[5:], 16)) / 2):02X}"
                    )
            elif "cells" in selections and c in selections["cells"]:
                tf = (
                    self.PAR.ops.header_selected_cells_fg
                    if kwargs[1] is None or self.PAR.ops.display_selected_fg_over_highlights
                    else kwargs[1]
                )
                if kwargs[0] is not None:
                    fill = (
                        f"#{int((int(c_1[1:3], 16) + int(c_2[1:3], 16)) / 2):02X}"
                        + f"{int((int(c_1[3:5], 16) + int(c_2[3:5], 16)) / 2):02X}"
                        + f"{int((int(c_1[5:], 16) + int(c_2[5:], 16)) / 2):02X}"
                    )
            else:
                tf = self.PAR.ops.header_fg if kwargs[1] is None else kwargs[1]
                if kwargs[0] is not None:
                    fill = kwargs[0]
            if kwargs[0] is not None:
                redrawn = self.redraw_highlight(
                    fc + 1,
                    0,
                    sc,
                    self.current_height - 1,
                    fill=fill,
                    outline=(
                        self.PAR.ops.header_fg
                        if self.get_cell_kwargs(datacn, key="dropdown") and self.PAR.ops.show_dropdown_borders
                        else ""
                    ),
                    tag="hi",
                )
        elif not kwargs:
            if "columns" in selections and c in selections["columns"]:
                tf = self.PAR.ops.header_selected_columns_fg
            elif "cells" in selections and c in selections["cells"]:
                tf = self.PAR.ops.header_selected_cells_fg
            else:
                tf = self.PAR.ops.header_fg
        return tf, redrawn

    def redraw_highlight(
        self, x1, y1, x2, y2, fill, outline, tag
    ):
        """Redraw a highlight rectangle.

        This method either updates the coordinates of an existing hidden
        highlight or creates a new rectangle with the specified attributes.

        Args:
            x1 (float): The x-coordinate of the top-left corner.
            y1 (float): The y-coordinate of the top-left corner.
            x2 (float): The x-coordinate of the bottom-right corner.
            y2 (float): The y-coordinate of the bottom-right corner.
            fill (str): The fill color of the rectangle.
            outline (str): The outline color of the rectangle.
            tag (str or tuple): The tag(s) to associate with the rectangle.

        Returns:
            bool: True if the highlight was successfully redrawn.
        """
        coords = (x1, y1, x2, y2)
        if self.hidd_high:
            iid, showing = self.hidd_high.popitem()
            self.coords(iid, coords)
            if showing:
                self.itemconfig(iid, fill=fill, outline=outline)
            else:
                self.itemconfig(iid, fill=fill, outline=outline, tag=tag, state="normal")
        else:
            iid = self.create_rectangle(coords, fill=fill, outline=outline, tag=tag)
        self.disp_high[iid] = True
        return True

    def redraw_gridline(
        self, points, fill, width, tag
    ):
        """Redraw a gridline using the specified parameters.

        This method either updates an existing hidden gridline or creates a new one
        based on the given coordinates and styles.

        Args:
            points (Sequence[float]): The coordinates of the line to be drawn.
            fill (str): The color of the gridline.
            width (int): The width of the gridline.
            tag (str or tuple): The tag(s) to associate with the gridline.
        """
        if self.hidd_grid:
            t, sh = self.hidd_grid.popitem()
            self.coords(t, points)
            if sh:
                self.itemconfig(t, fill=fill, width=width, tag=tag)
            else:
                self.itemconfig(t, fill=fill, width=width, tag=tag, state="normal")
            self.disp_grid[t] = True
        else:
            self.disp_grid[self.create_line(points, fill=fill, width=width, tag=tag)] = True

    def redraw_dropdown(
        self,
        x1,
        y1,
        x2,
        y2,
        fill,
        outline,
        tag,
        draw_outline=True,
        draw_arrow=True,
        open_=False,
    ):
        """Redraw a dropdown indicator with optional arrow.

        This method updates the appearance of a dropdown, including its outline
        and arrow based on its open or closed state.

        Args:
            x1 (float): The x-coordinate of the top-left corner.
            y1 (float): The y-coordinate of the top-left corner.
            x2 (float): The x-coordinate of the bottom-right corner.
            y2 (float): The y-coordinate of the bottom-right corner.
            fill (str): The fill color for the dropdown arrow.
            outline (str): The outline color for the dropdown.
            tag (str or tuple): The tag(s) to associate with the dropdown.
            draw_outline (bool): Whether to draw the outline. Default is True.
            draw_arrow (bool): Whether to draw the arrow. Default is True.
            open_ (bool): Whether the dropdown is currently open. Default is False.
        """
        if draw_outline and self.PAR.ops.show_dropdown_borders:
            self.redraw_highlight(x1 + 1, y1 + 1, x2, y2, fill="", outline=self.PAR.ops.header_fg, tag=tag)
        if draw_arrow:
            mod = (self.MT.header_txt_height - 1) if self.MT.header_txt_height % 2 else self.MT.header_txt_height
            small_mod = int(mod / 5)
            mid_y = floor(self.MT.min_header_height / 2)
            if open_:
                # up arrow
                points = (
                    x2 - 4 - small_mod - small_mod - small_mod - small_mod,
                    y1 + mid_y + small_mod,
                    x2 - 4 - small_mod - small_mod,
                    y1 + mid_y - small_mod,
                    x2 - 4,
                    y1 + mid_y + small_mod,
                )
            else:
                # down arrow
                points = (
                    x2 - 4 - small_mod - small_mod - small_mod - small_mod,
                    y1 + mid_y - small_mod,
                    x2 - 4 - small_mod - small_mod,
                    y1 + mid_y + small_mod,
                    x2 - 4,
                    y1 + mid_y - small_mod,
                )
            if self.hidd_dropdown:
                t, sh = self.hidd_dropdown.popitem()
                self.coords(t, points)
                if sh:
                    self.itemconfig(t, fill=fill)
                else:
                    self.itemconfig(t, fill=fill, tag=tag, state="normal")
                self.lift(t)
            else:
                t = self.create_line(
                    points,
                    fill=fill,
                    tag=tag,
                    width=2,
                    capstyle=tk.ROUND,
                    joinstyle=tk.BEVEL,
                )
            self.disp_dropdown[t] = True

    def redraw_checkbox(
        self,
        x1,
        y1,
        x2,
        y2,
        fill,
        outline,
        tag,
        draw_check=False,
    ):
        """Redraw a checkbox with an optional check mark.

        This method updates the appearance of a checkbox based on its filled
        state, including whether to draw a check mark.

        Args:
            x1 (float): The x-coordinate of the top-left corner.
            y1 (float): The y-coordinate of the top-left corner.
            x2 (float): The x-coordinate of the bottom-right corner.
            y2 (float): The y-coordinate of the bottom-right corner.
            fill (str): The fill color for the checkbox.
            outline (str): The outline color for the checkbox.
            tag (str or tuple): The tag(s) to associate with the checkbox.
            draw_check (bool): Whether to draw the check mark. Default is False.
        """
        points = rounded_box_coords(x1, y1, x2, y2)
        if self.hidd_checkbox:
            t, sh = self.hidd_checkbox.popitem()
            self.coords(t, points)
            if sh:
                self.itemconfig(t, fill=outline, outline=fill)
            else:
                self.itemconfig(t, fill=outline, outline=fill, tag=tag, state="normal")
            self.lift(t)
        else:
            t = self.create_polygon(points, fill=outline, outline=fill, tag=tag, smooth=True)
        self.disp_checkbox[t] = True
        if draw_check:
            # draw filled box
            x1 = x1 + 4
            y1 = y1 + 4
            x2 = x2 - 3
            y2 = y2 - 3
            points = rounded_box_coords(x1, y1, x2, y2, radius=4)
            if self.hidd_checkbox:
                t, sh = self.hidd_checkbox.popitem()
                self.coords(t, points)
                if sh:
                    self.itemconfig(t, fill=fill, outline=outline)
                else:
                    self.itemconfig(t, fill=fill, outline=outline, tag=tag, state="normal")
                self.lift(t)
            else:
                t = self.create_polygon(points, fill=fill, outline=outline, tag=tag, smooth=True)
            self.disp_checkbox[t] = True

    def configure_scrollregion(self, last_col_line_pos):
        """Configure the scroll region of the widget.

        This method sets the scroll region based on the last column's line
        position and the current height of the widget.

        Args:
            last_col_line_pos (float): The position of the last column line.
        """
        self.configure(
            scrollregion=(
                0,
                0,
                last_col_line_pos + self.PAR.ops.empty_horizontal + 2,
                self.current_height,
            )
        )
    def redraw_grid_and_text(
        self,
        last_col_line_pos,
        scrollpos_left,
        x_stop,
        grid_start_col,
        grid_end_col,
        text_start_col,
        text_end_col,
        scrollpos_right,
        col_pos_exists,
    ):
        """Redraw the grid and associated text in the widget.

        This method redraws the grid lines and text based on the provided
        parameters. It manages the positioning of the grid and text in
        relation to the scrolling position and column boundaries.

        Args:
            last_col_line_pos (float): The position of the last column line.
            scrollpos_left (float): The left scrolling position.
            x_stop (float): The stopping x-coordinate for the drawing.
            grid_start_col (int): The starting column index for the grid.
            grid_end_col (int): The ending column index for the grid.
            text_start_col (int): The starting column index for the text.
            text_end_col (int): The ending column index for the text.
            scrollpos_right (float): The right scrolling position.
            col_pos_exists (bool): Indicates if the column position exists.

        Returns:
            bool: True if redraw was successful, False otherwise.
        """
        try:
            self.configure_scrollregion(last_col_line_pos=last_col_line_pos)
        except Exception:
            return False
        self.hidd_text.update(self.disp_text)
        self.disp_text = {}
        self.hidd_high.update(self.disp_high)
        self.disp_high = {}
        self.hidd_grid.update(self.disp_grid)
        self.disp_grid = {}
        self.hidd_dropdown.update(self.disp_dropdown)
        self.disp_dropdown = {}
        self.hidd_checkbox.update(self.disp_checkbox)
        self.disp_checkbox = {}
        self.visible_col_dividers = {}
        self.col_height_resize_bbox = (
            scrollpos_left,
            self.current_height - 2,
            x_stop,
            self.current_height,
        )
        yend = self.current_height - 5
        if (self.PAR.ops.show_vertical_grid or self.width_resizing_enabled) and col_pos_exists:
            points = [
                x_stop - 1,
                self.current_height - 1,
                scrollpos_left - 1,
                self.current_height - 1,
                scrollpos_left - 1,
                -1,
            ]
            for c in range(grid_start_col, grid_end_col):
                draw_x = self.MT.col_positions[c]
                if c and self.width_resizing_enabled:
                    self.visible_col_dividers[c] = (draw_x - 2, 1, draw_x + 2, yend)
                points.extend(
                    (
                        draw_x,
                        -1,
                        draw_x,
                        self.current_height,
                        draw_x,
                        -1,
                        self.MT.col_positions[c + 1] if len(self.MT.col_positions) - 1 > c else draw_x,
                        -1,
                    )
                )
            self.redraw_gridline(points=points, fill=self.PAR.ops.header_grid_fg, width=1, tag="v")
        top = self.canvasy(0)
        c_2 = (
            self.PAR.ops.header_selected_cells_bg
            if self.PAR.ops.header_selected_cells_bg.startswith("#")
            else color_map[self.PAR.ops.header_selected_cells_bg]
        )
        c_3 = (
            self.PAR.ops.header_selected_columns_bg
            if self.PAR.ops.header_selected_columns_bg.startswith("#")
            else color_map[self.PAR.ops.header_selected_columns_bg]
        )
        font = self.PAR.ops.header_font
        selections = self.get_redraw_selections(text_start_col, grid_end_col)
        dd_coords = self.dropdown.get_coords()
        for c in range(text_start_col, text_end_col):
            draw_y = self.MT.header_first_ln_ins
            cleftgridln = self.MT.col_positions[c]
            crightgridln = self.MT.col_positions[c + 1]
            datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
            fill, dd_drawn = self.redraw_highlight_get_text_fg(
                cleftgridln, crightgridln, c, c_2, c_3, selections, datacn
            )

            if datacn in self.cell_options and "align" in self.cell_options[datacn]:
                align = self.cell_options[datacn]["align"]
            else:
                align = self.align

            kwargs = self.get_cell_kwargs(datacn, key="dropdown")
            if align == "w":
                draw_x = cleftgridln + 3
                if kwargs:
                    mw = crightgridln - cleftgridln - self.MT.header_txt_height - 2
                    self.redraw_dropdown(
                        cleftgridln,
                        0,
                        crightgridln,
                        self.current_height - 1,
                        fill=fill,
                        outline=fill,
                        tag="dd",
                        draw_outline=not dd_drawn,
                        draw_arrow=mw >= 5,
                        open_=dd_coords == c,
                    )
                else:
                    mw = crightgridln - cleftgridln - 1

            elif align == "e":
                if kwargs:
                    mw = crightgridln - cleftgridln - self.MT.header_txt_height - 2
                    draw_x = crightgridln - 5 - self.MT.header_txt_height
                    self.redraw_dropdown(
                        cleftgridln,
                        0,
                        crightgridln,
                        self.current_height - 1,
                        fill=fill,
                        outline=fill,
                        tag="dd",
                        draw_outline=not dd_drawn,
                        draw_arrow=mw >= 5,
                        open_=dd_coords == c,
                    )
                else:
                    mw = crightgridln - cleftgridln - 1
                    draw_x = crightgridln - 3

            elif align == "center":
                if kwargs:
                    mw = crightgridln - cleftgridln - self.MT.header_txt_height - 2
                    draw_x = cleftgridln + ceil((crightgridln - cleftgridln - self.MT.header_txt_height) / 2)
                    self.redraw_dropdown(
                        cleftgridln,
                        0,
                        crightgridln,
                        self.current_height - 1,
                        fill=fill,
                        outline=fill,
                        tag="dd",
                        draw_outline=not dd_drawn,
                        draw_arrow=mw >= 5,
                        open_=dd_coords == c,
                    )
                else:
                    mw = crightgridln - cleftgridln - 1
                    draw_x = cleftgridln + floor((crightgridln - cleftgridln) / 2)
            if not kwargs:
                kwargs = self.get_cell_kwargs(datacn, key="checkbox")
                if kwargs and mw > self.MT.header_txt_height + 1:
                    box_w = self.MT.header_txt_height + 1
                    if align == "w":
                        draw_x += box_w + 3
                    elif align == "center":
                        draw_x += ceil(box_w / 2) + 1
                    mw -= box_w + 3
                    try:
                        draw_check = (
                            self.MT._headers[datacn]
                            if isinstance(self.MT._headers, (list, tuple))
                            else self.MT.data[self.MT._headers][datacn]
                        )
                    except Exception:
                        draw_check = False
                    self.redraw_checkbox(
                        cleftgridln + 2,
                        2,
                        cleftgridln + self.MT.header_txt_height + 3,
                        self.MT.header_txt_height + 3,
                        fill=fill if kwargs["state"] == "normal" else self.PAR.ops.header_grid_fg,
                        outline="",
                        tag="cb",
                        draw_check=draw_check,
                    )
            lns = self.get_valid_cell_data_as_str(datacn, fix=False)
            if not lns:
                continue
            lns = lns.split("\n")
            if mw > self.MT.header_txt_width and not (
                (align == "w" and draw_x > scrollpos_right)
                or (align == "e" and cleftgridln + 5 > scrollpos_right)
                or (align == "center" and cleftgridln + 5 > scrollpos_right)
            ):
                for txt in islice(
                    lns,
                    self.lines_start_at if self.lines_start_at < len(lns) else len(lns) - 1,
                    None,
                ):
                    if draw_y > top:
                        if self.hidd_text:
                            iid, showing = self.hidd_text.popitem()
                            self.coords(iid, draw_x, draw_y)
                            if showing:
                                self.itemconfig(
                                    iid,
                                    text=txt,
                                    fill=fill,
                                    font=font,
                                    anchor=align,
                                )
                            else:
                                self.itemconfig(
                                    iid,
                                    text=txt,
                                    fill=fill,
                                    font=font,
                                    anchor=align,
                                    state="normal",
                                )
                            self.tag_raise(iid)
                        else:
                            iid = self.create_text(
                                draw_x,
                                draw_y,
                                text=txt,
                                fill=fill,
                                font=font,
                                anchor=align,
                                tag="t",
                            )
                        self.disp_text[iid] = True
                        wd = self.bbox(iid)
                        wd = wd[2] - wd[0]
                        if wd > mw:
                            if align == "w":
                                txt = txt[: int(len(txt) * (mw / wd))]
                                self.itemconfig(iid, text=txt)
                                wd = self.bbox(iid)
                                while wd[2] - wd[0] > mw:
                                    txt = txt[:-1]
                                    self.itemconfig(iid, text=txt)
                                    wd = self.bbox(iid)
                            elif align == "e":
                                txt = txt[len(txt) - int(len(txt) * (mw / wd)) :]
                                self.itemconfig(iid, text=txt)
                                wd = self.bbox(iid)
                                while wd[2] - wd[0] > mw:
                                    txt = txt[1:]
                                    self.itemconfig(iid, text=txt)
                                    wd = self.bbox(iid)
                            elif align == "center":
                                self.c_align_cyc = cycle(self.centre_alignment_text_mod_indexes)
                                tmod = ceil((len(txt) - int(len(txt) * (mw / wd))) / 2)
                                txt = txt[tmod - 1 : -tmod]
                                self.itemconfig(iid, text=txt)
                                wd = self.bbox(iid)
                                while wd[2] - wd[0] > mw:
                                    txt = txt[next(self.c_align_cyc)]
                                    self.itemconfig(iid, text=txt)
                                    wd = self.bbox(iid)
                                self.coords(iid, draw_x, draw_y)
                    draw_y += self.MT.header_xtra_lines_increment
                    if draw_y - 1 > self.current_height:
                        break
        for dct in (self.hidd_text, self.hidd_high, self.hidd_grid, self.hidd_dropdown, self.hidd_checkbox):
            for iid, showing in dct.items():
                if showing:
                    self.itemconfig(iid, state="hidden")
                    dct[iid] = False
        return True

    def get_redraw_selections(self, startc, endc):
        """Get the selections that need to be redrawn between specified columns.

        This method identifies which selections (rows or cells) overlap with
        the specified column range and returns a dictionary indicating the
        selections that require redrawing.

        Args:
            startc (int): The starting column index for the range.
            endc (int): The ending column index for the range.

        Returns:
            dict(str: set[int]): A dictionary where the keys are selection types ('cells' or
                  other types), and the values are sets of column indices
                  that need to be redrawn.
        """
        d = defaultdict(set)
        for item, box in self.MT.get_selection_items():
            r1, c1, r2, c2 = box.coords
            for c in range(startc, endc):
                if c1 <= c and c2 > c:
                    d[box.type_ if box.type_ != "rows" else "cells"].add(c)
        return d

    def open_cell(self, event=None, ignore_existing_editor=False):
        """Open the selected cell for editing or interaction.

        This method checks if any cells are selected and whether
        an existing text editor is open. If a cell is selected and
        it is not marked as readonly, it opens a dropdown or checkbox
        if applicable. Otherwise, it opens a text editor for the cell.

        Args:
            event (object, optional): The event object triggered by the
                user interaction. Defaults to None.
            ignore_existing_editor (bool, optional): If set to True,
                allows opening the cell even if an existing editor is
                open. Defaults to False.
        """
        if not self.MT.anything_selected() or (not ignore_existing_editor and self.text_editor.open):
            return
        if not self.MT.selected:
            return
        c = self.MT.selected.column
        datacn = self.MT.datacn(c)
        if self.get_cell_kwargs(datacn, key="readonly"):
            return
        elif self.get_cell_kwargs(datacn, key="dropdown") or self.get_cell_kwargs(datacn, key="checkbox"):
            if self.MT.event_opens_dropdown_or_checkbox(event):
                if self.get_cell_kwargs(datacn, key="dropdown"):
                    self.open_dropdown_window(c, event=event)
                elif self.get_cell_kwargs(datacn, key="checkbox"):
                    self.click_checkbox(c, datacn)
        elif self.edit_cell_enabled:
            self.open_text_editor(event=event, c=c, dropdown=False)

    # displayed indexes
    def get_cell_align(self, c):
        """Get the alignment for a specified cell column.

        This method retrieves the alignment setting for a given
        cell column. If the column is not displayed, it checks
        against the displayed columns. If no specific alignment
        is set for the cell, it defaults to the general alignment
        setting.

        Args:
            c (int): The index of the column for which to retrieve
                the alignment.

        Returns:
            str: The alignment for the specified cell column,
                which can be 'left', 'center', or 'right'.
        """
        datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
        if datacn in self.cell_options and "align" in self.cell_options[datacn]:
            align = self.cell_options[datacn]["align"]
        else:
            align = self.align
        return align

    # c is displayed col
    def open_text_editor(
        self,
        event=None,
        c=0,
        text=None,
        state="normal",
        dropdown=False,
    ):
        """Open the text editor for editing a cell's content.

        This method handles the opening of a text editor for a
        specific cell. It responds to various keyboard events and
        can initialize the editor with existing cell data. The
        editor allows users to modify cell content, and it can
        automatically resize based on the input.

        Args:
            event (object): The event that triggered the editor to open.
            c (int): The index of the column to edit.
            text (object): Optional initial text for the editor.
            state (str): The state of the text editor (e.g., 'normal').
            dropdown (bool): Indicates if the editor was opened from a dropdown.

        Returns:
            bool: True if the editor was successfully opened, False otherwise.
        """
        text = None
        extra_func_key = "??"
        if event is None or self.MT.event_opens_dropdown_or_checkbox(event):
            if event is not None:
                if hasattr(event, "keysym") and event.keysym == "Return":
                    extra_func_key = "Return"
                elif hasattr(event, "keysym") and event.keysym == "F2":
                    extra_func_key = "F2"
            text = self.get_cell_data(self.MT.datacn(c), none_to_empty_str=True, redirect_int=True)
        elif event is not None and (
            (hasattr(event, "keysym") and event.keysym == "BackSpace") or event.keycode in (8, 855638143)
        ):
            extra_func_key = "BackSpace"
            text = ""
        elif event is not None and (
            (hasattr(event, "char") and event.char.isalpha())
            or (hasattr(event, "char") and event.char.isdigit())
            or (hasattr(event, "char") and event.char in symbols_set)
        ):
            extra_func_key = event.char
            text = event.char
        else:
            return False
        if self.extra_begin_edit_cell_func:
            try:
                text = self.extra_begin_edit_cell_func(
                    event_dict(
                        name="begin_edit_header",
                        sheet=self.PAR.name,
                        key=extra_func_key,
                        value=text,
                        loc=c,
                        column=c,
                        boxes=self.MT.get_boxes(),
                        selected=self.MT.selected,
                    )
                )
            except Exception:
                return False
            if text is None:
                return False
            else:
                text = text if isinstance(text, str) else f"{text}"
        text = "" if text is None else text
        if self.PAR.ops.cell_auto_resize_enabled:
            if self.height_resizing_enabled:
                self.set_height_of_header_to_text(text)
            self.set_col_width_run_binding(c)
        if self.text_editor.open and c == self.text_editor.column:
            self.text_editor.set_text(self.text_editor.get() + "" if not isinstance(text, str) else text)
            return
        self.hide_text_editor()
        if not self.MT.see(r=0, c=c, keep_yscroll=True, check_cell_visibility=True):
            self.MT.refresh()
        x = self.MT.col_positions[c] + 1
        y = 0
        w = self.MT.col_positions[c + 1] - x
        h = self.current_height + 1
        if text is None:
            text = self.get_cell_data(self.MT.datacn(c), none_to_empty_str=True, redirect_int=True)
        bg, fg = self.PAR.ops.header_bg, self.PAR.ops.header_fg
        kwargs = {
            "menu_kwargs": DotDict(
                {
                    "font": self.PAR.ops.table_font,
                    "foreground": self.PAR.ops.popup_menu_fg,
                    "background": self.PAR.ops.popup_menu_bg,
                    "activebackground": self.PAR.ops.popup_menu_highlight_bg,
                    "activeforeground": self.PAR.ops.popup_menu_highlight_fg,
                }
            ),
            "sheet_ops": self.PAR.ops,
            "border_color": self.PAR.ops.header_selected_columns_bg,
            "text": text,
            "state": state,
            "width": w,
            "height": h,
            "show_border": True,
            "bg": bg,
            "fg": fg,
            "align": self.get_cell_align(c),
            "c": c,
        }
        if not self.text_editor.window:
            self.text_editor.window = TextEditor(self, newline_binding=self.text_editor_newline_binding)
            self.text_editor.canvas_id = self.create_window((x, y), window=self.text_editor.window, anchor="nw")
        self.text_editor.window.reset(**kwargs)
        if not self.text_editor.open:
            self.itemconfig(self.text_editor.canvas_id, state="normal")
            self.text_editor.open = True
        self.coords(self.text_editor.canvas_id, x, y)
        for b in text_editor_newline_bindings:
            self.text_editor.tktext.bind(b, self.text_editor_newline_binding)
        for b in text_editor_close_bindings:
            self.text_editor.tktext.bind(b, self.close_text_editor)
        if not dropdown:
            self.text_editor.tktext.focus_set()
            self.text_editor.window.scroll_to_bottom()
            self.text_editor.tktext.bind("<FocusOut>", self.close_text_editor)
        for key, func in self.MT.text_editor_user_bound_keys.items():
            self.text_editor.tktext.bind(key, func)
        return True

    # displayed indexes
    def text_editor_has_wrapped(
        self,
        r=0,
        c=0,
        check_lines=None,  # just here to receive text editor arg
    ):
        """Check if the text editor has wrapped lines and adjust its width.

        This method adjusts the width of the text editor based on the
        current width and the header text height. If the width changes,
        it updates the column width and redraws the main table.

        Args:
            r (int): The row index (default is 0).
            c (int): The column index (default is 0).
            check_lines (None): Placeholder for future text editor functionality.

        Returns:
            None
        """
        if self.width_resizing_enabled:
            curr_width = self.text_editor.window.winfo_width()
            new_width = curr_width + (self.MT.header_txt_height * 2)
            if new_width != curr_width:
                self.text_editor.window.config(width=new_width)
                self.set_col_width_run_binding(c, width=new_width, only_if_too_small=False)
                if self.dropdown.open and self.dropdown.get_coords() == c:
                    self.itemconfig(self.dropdown.canvas_id, width=new_width)
                    self.dropdown.window.update_idletasks()
                    self.dropdown.window._reselect()
                self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=False, redraw_table=True)
                self.coords(self.text_editor.canvas_id, self.MT.col_positions[c] + 1, 0)

    # displayed indexes
    def text_editor_newline_binding(self, event=None, check_lines=True):
        """Adjust the height of the text editor on newline binding.

        This method increases the height of the text editor when a newline
        is entered, ensuring that it doesn't exceed the minimum header height
        or the available space. It also updates the dropdown position if open.

        Args:
            event (None): The event associated with the key binding (default is None).
            check_lines (bool): Flag to check if the new height exceeds the current height (default is True).
        """
        if not self.height_resizing_enabled:
            return
        curr_height = self.text_editor.window.winfo_height()
        if curr_height < self.MT.min_header_height:
            return
        if (
            not check_lines
            or self.MT.get_lines_cell_height(
                self.text_editor.window.get_num_lines() + 1,
                font=self.text_editor.tktext.cget("font"),
            )
            > curr_height
        ):
            c = self.text_editor.column
            new_height = curr_height + self.MT.header_xtra_lines_increment
            space_bot = self.MT.get_space_bot(0)
            if new_height > space_bot:
                new_height = space_bot
            if new_height != curr_height:
                self.text_editor.window.config(height=new_height)
                self.set_height(new_height, set_TL=True)
                if self.dropdown.open and self.dropdown.get_coords() == c:
                    win_h, anchor = self.get_dropdown_height_anchor(c, new_height)
                    self.coords(
                        self.dropdown.canvas_id,
                        self.MT.col_positions[c],
                        new_height - 1,
                    )
                    self.itemconfig(self.dropdown.canvas_id, anchor=anchor, height=win_h)

    def refresh_open_window_positions(self, zoom):
        """Refresh the positions of open text editor and dropdown windows.

        This method adjusts the height and width of the text editor and the dropdown
        menu based on the current zoom level. It recalculates positions to ensure
        proper alignment within the grid.

        Args:
            zoom (str): Indicates the zoom action. Accepts "in" to zoom in or "out" to zoom out.

        Returns:
            None
        """
        if self.text_editor.open:
            c = self.text_editor.column
            self.text_editor.window.config(
                height=self.current_height,
                width=self.MT.col_positions[c + 1] - self.MT.col_positions[c] + 1,
            )
            self.text_editor.tktext.config(font=self.PAR.ops.header_font)
            self.coords(
                self.text_editor.canvas_id,
                self.MT.col_positions[c],
                0,
            )
        if self.dropdown.open:
            if zoom == "in":
                self.dropdown.window.zoom_in()
            elif zoom == "out":
                self.dropdown.window.zoom_out()
            c = self.dropdown.get_coords()
            if self.text_editor.open:
                text_editor_h = self.text_editor.window.winfo_height()
                win_h, anchor = self.get_dropdown_height_anchor(c, text_editor_h)
            else:
                text_editor_h = self.current_height
                anchor = self.itemcget(self.dropdown.canvas_id, "anchor")
                # win_h = 0
            self.dropdown.window.config(width=self.MT.col_positions[c + 1] - self.MT.col_positions[c] + 1)
            if anchor == "nw":
                self.coords(
                    self.dropdown.canvas_id,
                    self.MT.col_positions[c],
                    text_editor_h - 1,
                )
                # self.itemconfig(self.dropdown.canvas_id, anchor=anchor, height=win_h)
            elif anchor == "sw":
                self.coords(
                    self.dropdown.canvas_id,
                    self.MT.col_positions[c],
                    0,
                )
                # self.itemconfig(self.dropdown.canvas_id, anchor=anchor, height=win_h)

    def hide_text_editor(self):
        if self.text_editor.open:
            for binding in text_editor_to_unbind:
                self.text_editor.tktext.unbind(binding)
            self.itemconfig(self.text_editor.canvas_id, state="hidden")
            self.text_editor.open = False

    # c is displayed col
    def close_text_editor(self, event):
        """Handle closing the text editor based on user input.

        This method checks if the text editor should be closed based on
        the current focus and the Escape key press. If the editor is
        closed, it updates the cell data with the text editor's value.

        Args:
            event (tk.Event): The event object containing information about
                              the key press or focus change.

        Returns:
            str or None: Returns "break" to indicate the event is handled,
                          or None if no action is taken.
        """
        # checking if text editor should be closed or not
        # errors if __tk_filedialog is open
        try:
            focused = self.focus_get()
        except Exception:
            focused = None
        try:
            if focused == self.text_editor.tktext.rc_popup_menu:
                return "break"
        except Exception:
            pass
        if focused is None:
            return "break"
        if event.keysym == "Escape":
            self.hide_text_editor_and_dropdown()
            self.focus_set()
            return
        # setting cell data with text editor value
        text_editor_value = self.text_editor.get()
        c = self.text_editor.column
        datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
        event_data = event_dict(
            name="end_edit_header",
            sheet=self.PAR.name,
            widget=self,
            cells_header={datacn: self.get_cell_data(datacn)},
            key=event.keysym,
            value=text_editor_value,
            loc=c,
            column=c,
            boxes=self.MT.get_boxes(),
            selected=self.MT.selected,
        )
        edited = False
        set_data = partial(
            self.set_cell_data_undo,
            c=c,
            datacn=datacn,
            check_input_valid=False,
        )
        if self.MT.edit_validation_func:
            text_editor_value = self.MT.edit_validation_func(event_data)
            if text_editor_value is not None and self.input_valid_for_cell(datacn, text_editor_value):
                edited = set_data(value=text_editor_value)
        elif self.input_valid_for_cell(datacn, text_editor_value):
            edited = set_data(value=text_editor_value)
        if edited:
            try_binding(self.extra_end_edit_cell_func, event_data)
        self.MT.recreate_all_selection_boxes()
        self.hide_text_editor_and_dropdown()
        if event.keysym != "FocusOut":
            self.focus_set()
        return "break"

    def get_dropdown_height_anchor(self, c, text_editor_h=None):
        """Calculate the height and anchor position for the dropdown.

        This method computes the height of the dropdown based on the
        number of lines in the dropdown values and the height of the
        text editor. It ensures that the dropdown does not exceed
        predefined size limits.

        Args:
            c (int): The column index for which the dropdown is being
                      calculated.
            text_editor_h (int, optional): The current height of the
                                            text editor. Defaults to None.

        Returns:
            tuple: A tuple containing the calculated height (int) and
                   the anchor position (str) which is always "nw".
        """
        win_h = 5
        datacn = self.MT.datacn(c)
        for i, v in enumerate(self.get_cell_kwargs(datacn, key="dropdown")["values"]):
            v_numlines = len(v.split("\n") if isinstance(v, str) else f"{v}".split("\n"))
            if v_numlines > 1:
                win_h += (
                    self.MT.header_first_ln_ins + (v_numlines * self.MT.header_xtra_lines_increment) + 5
                )  # end of cell
            else:
                win_h += self.MT.min_header_height
            if i == 5:
                break
        if win_h > 500:
            win_h = 500
        space_bot = self.MT.get_space_bot(0, text_editor_h)
        win_h2 = int(win_h)
        if win_h > space_bot:
            win_h = space_bot - 1
        if win_h < self.MT.header_txt_height + 5:
            win_h = self.MT.header_txt_height + 5
        elif win_h > win_h2:
            win_h = win_h2
        return win_h, "nw"

    def dropdown_text_editor_modified(self, dd_window, event, modified_func=None):
        """Handle modifications in the dropdown text editor.

        This method checks if a modification function is provided and
        calls it with the event data. After that, it updates the dropdown
        window by calling its search_and_see method.

        Args:
            dd_window (object): The dropdown window object to be updated.
            event (dict): The event data associated with the modification.
            modified_func (Callable, optional): A function to handle
                                                 the modification. Defaults to None.
        """
        if modified_func:
            modified_func(event)
        dd_window.search_and_see(event)

    def open_dropdown_window(self, c, event=None):
        """Open the dropdown window for the specified column.

        This method hides the text editor, checks if the dropdown can be opened,
        and initializes the dropdown window. It sets the size and position of 
        the dropdown based on the specified column.

        Args:
            c (int): The column index for which to open the dropdown.
            event (object, optional): The event that triggered the dropdown. Defaults to None.
        """
        self.hide_text_editor()
        kwargs = self.get_cell_kwargs(self.MT.datacn(c), key="dropdown")
        if kwargs["state"] == "normal":
            if not self.open_text_editor(event=event, c=c, dropdown=True):
                return
        win_h, anchor = self.get_dropdown_height_anchor(c)
        win_w = self.MT.col_positions[c + 1] - self.MT.col_positions[c] + 1
        ypos = self.current_height - 1
        reset_kwargs = {
            "r": 0,
            "c": c,
            "width": win_w,
            "height": win_h,
            "font": self.PAR.ops.header_font,
            "ops": self.PAR.ops,
            "outline_color": self.PAR.ops.header_selected_columns_bg,
            "align": self.get_cell_align(c),
            "values": kwargs["values"],
        }
        if self.dropdown.window:
            self.dropdown.window.reset(**reset_kwargs)
            self.itemconfig(self.dropdown.canvas_id, state="normal")
            self.coords(self.dropdown.canvas_id, self.MT.col_positions[c], ypos)
            self.dropdown.window.tkraise()
        else:
            self.dropdown.window = self.PAR.dropdown_class(
                self.winfo_toplevel(),
                **reset_kwargs,
                single_index="c",
                close_dropdown_window=self.close_dropdown_window,
                search_function=kwargs["search_function"],
                arrowkey_RIGHT=self.MT.arrowkey_RIGHT,
                arrowkey_LEFT=self.MT.arrowkey_LEFT,
            )
            self.dropdown.canvas_id = self.create_window(
                (self.MT.col_positions[c], ypos),
                window=self.dropdown.window,
                anchor=anchor,
            )
        if kwargs["state"] == "normal":
            self.text_editor.tktext.bind(
                "<<TextModified>>",
                lambda _x: self.dropdown_text_editor_modified(
                    self.dropdown.window,
                    event_dict(
                        name="header_dropdown_modified",
                        sheet=self.PAR.name,
                        value=self.text_editor.get(),
                        loc=c,
                        column=c,
                        boxes=self.MT.get_boxes(),
                        selected=self.MT.selected,
                    ),
                    kwargs["modified_function"],
                ),
            )
            self.update_idletasks()
            try:
                self.after(1, lambda: self.text_editor.tktext.focus())
                self.after(2, self.text_editor.window.scroll_to_bottom())
            except Exception:
                return
            redraw = False
        else:
            self.update_idletasks()
            self.dropdown.window.bind("<FocusOut>", lambda _x: self.close_dropdown_window(c))
            self.dropdown.window.bind("<Escape>", self.close_dropdown_window)
            self.dropdown.window.focus_set()
            redraw = True
        self.dropdown.open = True
        if redraw:
            self.MT.main_table_redraw_grid_and_text(redraw_header=True, redraw_row_index=False, redraw_table=False)

    def close_dropdown_window(self, c=None, selection=None, redraw=True):
        """Close the dropdown window and handle selection changes.

        This method handles the closure of the dropdown window, updates the 
        relevant cell data based on the selected value, and calls any necessary 
        validation or selection functions.

        Args:
            c (int, optional): The column index associated with the dropdown. Defaults to None.
            selection (object, optional): The selected value from the dropdown. Defaults to None.
            redraw (bool, optional): Indicates whether to redraw the grid. Defaults to True.
        """
        if c is not None and selection is not None:
            datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
            kwargs = self.get_cell_kwargs(datacn, key="dropdown")
            pre_edit_value = self.get_cell_data(datacn)
            edited = False
            event_data = event_dict(
                name="end_edit_header",
                sheet=self.PAR.name,
                widget=self,
                cells_header={datacn: pre_edit_value},
                key="??",
                value=selection,
                loc=c,
                column=c,
                boxes=self.MT.get_boxes(),
                selected=self.MT.selected,
            )
            if kwargs["select_function"] is not None:
                kwargs["select_function"](event_data)
            if self.MT.edit_validation_func:
                selection = self.MT.edit_validation_func(event_data)
                if selection is not None:
                    edited = self.set_cell_data_undo(c, datacn=datacn, value=selection, redraw=not redraw)
            else:
                edited = self.set_cell_data_undo(c, datacn=datacn, value=selection, redraw=not redraw)
            if edited:
                try_binding(self.extra_end_edit_cell_func, event_data)
            self.MT.recreate_all_selection_boxes()
        self.focus_set()
        self.hide_text_editor_and_dropdown(redraw=redraw)

    def hide_text_editor_and_dropdown(self, redraw=True):
        """Hide the text editor and dropdown window.

        This method hides both the text editor and the dropdown window. 
        If specified, it also refreshes the main table.

        Args:
            redraw (bool, optional): Indicates whether to refresh the main table. Defaults to True.
        """
        self.hide_text_editor()
        self.hide_dropdown_window()
        if redraw:
            self.MT.refresh()

    def mouseclick_outside_editor_or_dropdown(self, inside=False):
        """Handle mouse click events outside the editor or dropdown.

        This method closes the text editor if it is open and hides the dropdown window if it is visible.
        If the click occurred inside the main table, it triggers a redraw of the table.

        Args:
            inside (bool, optional): Indicates whether the mouse click occurred inside the main table. Defaults to False.

        Returns:
            int or None: The coordinates of the closed dropdown window, or None if it was not open.
        """
        closed_dd_coords = self.dropdown.get_coords()
        if self.text_editor.open:
            self.close_text_editor(new_tk_event("ButtonPress-1"))
        if closed_dd_coords is not None:
            self.hide_dropdown_window()
            if inside:
                self.MT.main_table_redraw_grid_and_text(
                    redraw_header=True,
                    redraw_row_index=False,
                    redraw_table=False,
                )
        return closed_dd_coords

    def mouseclick_outside_editor_or_dropdown_all_canvases(self, inside=False):
        """Handle mouse click events outside the editor or dropdown for all canvases.

        This method calls the mouse click handler for both the main table and the RI canvas,
        and then processes the click for the current canvas.

        Args:
            inside (bool, optional): Indicates whether the mouse click occurred inside the main table. Defaults to False.

        Returns:
            int or None: The coordinates of the closed dropdown window from the current canvas, or None if it was not open.
        """
        self.RI.mouseclick_outside_editor_or_dropdown()
        self.MT.mouseclick_outside_editor_or_dropdown()
        return self.mouseclick_outside_editor_or_dropdown(inside)

    def hide_dropdown_window(self):
        """Hide the dropdown window if it is open.

        This method checks if the dropdown window is currently open.
        If so, it unbinds the focus out event and hides the associated
        canvas element.
        """
        if self.dropdown.open:
            self.dropdown.window.unbind("<FocusOut>")
            self.itemconfig(self.dropdown.canvas_id, state="hidden")
            self.dropdown.open = False

    # internal event use
    def set_cell_data_undo(
        self,
        c=0,
        datacn=None,
        value="",
        cell_resize=True,
        undo=True,
        redraw=True,
        check_input_valid=True,
    ):
        """Set the cell data with undo functionality.

        This method updates the cell data, enabling undo functionality
        if required. It handles cell resizing and validation based on
        input parameters. It returns whether the cell was edited.

        Args:
            c (int): The column index to update.
            datacn (int): The data column number; defaults to None.
            value (object): The value to set in the cell; defaults to an empty string.
            cell_resize (bool): Whether to resize the cell based on the content; defaults to True.
            undo (bool): Whether to push the change to the undo stack; defaults to True.
            redraw (bool): Whether to refresh the view after the change; defaults to True.
            check_input_valid (bool): Whether to validate the input; defaults to True.

        Returns:
            bool: True if the cell was edited, False otherwise.
        """
        if datacn is None:
            datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
        event_data = event_dict(
            name="edit_header",
            sheet=self.PAR.name,
            widget=self,
            cells_header={datacn: self.get_cell_data(datacn)},
            boxes=self.MT.get_boxes(),
            selected=self.MT.selected,
        )
        edited = False
        if isinstance(self.MT._headers, int):
            disprn = self.MT.try_disprn(self.MT._headers)
            edited = self.MT.set_cell_data_undo(
                r=disprn if isinstance(disprn, int) else 0,
                c=c,
                datarn=self.MT._headers,
                datacn=datacn,
                value=value,
                undo=True,
                cell_resize=isinstance(disprn, int),
            )
        else:
            self.fix_header(datacn)
            if not check_input_valid or self.input_valid_for_cell(datacn, value):
                if self.MT.undo_enabled and undo:
                    self.MT.undo_stack.append(pickled_event_dict(event_data))
                self.set_cell_data(datacn=datacn, value=value)
                edited = True
        if edited and cell_resize and self.PAR.ops.cell_auto_resize_enabled:
            if self.height_resizing_enabled:
                self.set_height_of_header_to_text(self.get_valid_cell_data_as_str(datacn, fix=False))
            self.set_col_width_run_binding(c)
        if redraw:
            self.MT.refresh()
        if edited:
            self.MT.sheet_modified(event_data)
        return edited

    def set_cell_data(self, datacn=None, value=""):
        """Set the data for a specified cell.

        This method updates the cell data in the header. If the column 
        corresponds to a checkbox, it converts the value to a boolean.

        Args:
            datacn (int): The data column number; defaults to None.
            value (object): The value to set in the cell; defaults to an empty string.
        """
        if isinstance(self.MT._headers, int):
            self.MT.set_cell_data(datarn=self.MT._headers, datacn=datacn, value=value)
        else:
            self.fix_header(datacn)
            if self.get_cell_kwargs(datacn, key="checkbox"):
                self.MT._headers[datacn] = try_to_bool(value)
            else:
                self.MT._headers[datacn] = value

    def input_valid_for_cell(self, datacn, value, check_readonly=True):
        """Validate the input for a specific cell.

        This method checks if the given value is valid for the cell specified 
        by datacn, considering read-only status, checkbox requirements, 
        existing cell value, and dropdown validation.

        Args:
            datacn (int): The data column number.
            value (object): The value to validate.
            check_readonly (bool): Whether to check if the cell is read-only; 
                defaults to True.

        Returns:
            bool: True if the value is valid for the cell, otherwise False.
        """
        if check_readonly and self.get_cell_kwargs(datacn, key="readonly"):
            return False
        if self.get_cell_kwargs(datacn, key="checkbox"):
            return is_bool_like(value)
        if self.cell_equal_to(datacn, value):
            return False
        kwargs = self.get_cell_kwargs(datacn, key="dropdown")
        if kwargs and kwargs["validate_input"] and value not in kwargs["values"]:
            return False
        return True

    def cell_equal_to(self, datacn, value):
        """Check if the cell value is equal to the given value.

        This method verifies if the value of the cell specified by datacn
        is equal to the provided value. It handles both list and integer 
        header types.

        Args:
            datacn (int): The data column number.
            value (object): The value to compare with the cell's value.

        Returns:
            bool: True if the cell's value equals the given value, otherwise False.
        """
        self.fix_header(datacn)
        if isinstance(self.MT._headers, list):
            return self.MT._headers[datacn] == value
        elif isinstance(self.MT._headers, int):
            return self.MT.cell_equal_to(self.MT._headers, datacn, value)

    def get_cell_data(self, datacn, get_displayed=False, none_to_empty_str=False, redirect_int=False):
        """Retrieve the cell data for the given data column number.

        This method returns the value of the specified cell, with options 
        for formatting and behavior based on input parameters.

        Args:
            datacn (int): The data column number to retrieve the value for.
            get_displayed (bool): If True, return the displayed cell value as a string.
            none_to_empty_str (bool): If True, return an empty string instead of None.
            redirect_int (bool): If True and the headers are an int, call the internal 
                method to get cell data.

        Returns:
            object: The value of the specified cell, or an empty string if conditions are met.
        """
        if get_displayed:
            return self.get_valid_cell_data_as_str(datacn, fix=False)
        if redirect_int and isinstance(self.MT._headers, int):  # internal use
            return self.MT.get_cell_data(self.MT._headers, datacn, none_to_empty_str=True)
        if (
            isinstance(self.MT._headers, int)
            or not self.MT._headers
            or datacn >= len(self.MT._headers)
            or (self.MT._headers[datacn] is None and none_to_empty_str)
        ):
            return ""
        return self.MT._headers[datacn]

    def get_valid_cell_data_as_str(self, datacn, fix=True):
        """Retrieve the valid cell data as a string for the specified data column.

        This method checks for dropdown or checkbox configurations to determine
        the display text. If no valid data is found, it retrieves the data from
        the header or returns a default header value if applicable.

        Args:
            datacn (int): The data column number to retrieve the string value for.
            fix (bool): If True, attempt to fix the header for the data column.

        Returns:
            str: The valid cell data as a string, or a default value if applicable.
        """
        kwargs = self.get_cell_kwargs(datacn, key="dropdown")
        if kwargs:
            if kwargs["text"] is not None:
                return "{}".format(kwargs['text'])
        else:
            kwargs = self.get_cell_kwargs(datacn, key="checkbox")
            if kwargs:
                return "{}".format(kwargs['text'])
        if isinstance(self.MT._headers, int):
            return self.MT.get_valid_cell_data_as_str(self.MT._headers, datacn, get_displayed=True)
        if fix:
            self.fix_header(datacn)
        try:
            value = "" if self.MT._headers[datacn] is None else "{}".format(self.MT._headers[datacn])
        except Exception:
            value = ""
        if not value and self.PAR.ops.show_default_header_for_empty:
            value = get_n2a(datacn, self.PAR.ops.default_header)
        return value

    def get_value_for_empty_cell(self, datacn, c_ops=True):
        """Get the default value for an empty cell based on its configuration.

        This method checks the cell's configuration to determine what value 
        should be returned when the cell is empty. If the cell is a checkbox, 
        it defaults to `False`. If it's a dropdown with validation, it returns 
        the first valid value from the dropdown options.

        Args:
            datacn (int): The data column number to retrieve the default value for.
            c_ops (bool): If True, consider cell operations.

        Returns:
            object: The value to use for the empty cell, which can be 
            False, a valid dropdown value, or an empty string.
        """
        if self.get_cell_kwargs(datacn, key="checkbox", cell=c_ops):
            return False
        kwargs = self.get_cell_kwargs(datacn, key="dropdown", cell=c_ops)
        if kwargs and kwargs["validate_input"] and kwargs["values"]:
            return kwargs["values"][0]
        return ""

    def get_empty_header_seq(self, end, start=0, c_ops=True):
        """Generate a sequence of default values for empty headers.

        This method creates a list of default values for empty headers 
        within the specified range. It retrieves the default value for each 
        header based on its configuration using `get_value_for_empty_cell`.

        Args:
            end (int): The exclusive upper limit for the header index range.
            start (int): The inclusive lower limit for the header index range (default is 0).
            c_ops (bool): If True, consider cell operations when getting values.

        Returns:
            list: A list of default values for empty headers from start to end.
        """
        return [self.get_value_for_empty_cell(datacn, c_ops=c_ops) for datacn in range(start, end)]

    def fix_header(self, datacn=None):
        """Ensure the headers are in the correct format and extend if necessary.

        This method checks the type of the headers and converts them into a 
        list if they are not already. If a `datacn` is provided and exceeds 
        the current length of the headers, the headers are extended with 
        default values.

        Args:
            datacn (int): The index of the column header to check. If provided 
                and out of range, the headers will be extended (default is None).
        """
        if isinstance(self.MT._headers, int):
            return
        if isinstance(self.MT._headers, float):
            self.MT._headers = int(self.MT._headers)
            return
        if not isinstance(self.MT._headers, list):
            try:
                self.MT._headers = list(self.MT._headers)
            except Exception:
                self.MT._headers = []
        if isinstance(datacn, int) and datacn >= len(self.MT._headers):
            self.MT._headers.extend(self.get_empty_header_seq(end=datacn + 1, start=len(self.MT._headers)))

    # displayed indexes
    def set_col_width_run_binding(self, c, width=None, only_if_too_small=True):
        """Set the width of a specified column and trigger a resize event if necessary.

        This method adjusts the width of a specified column and checks if 
        the new width differs from the old width. If it does, a resize 
        event is triggered to notify any relevant listeners.

        Args:
            c (int): The index of the column to adjust.
            width (int or None): The new width for the column (default is None).
            only_if_too_small (bool): If True, the width will only be set if 
                it is smaller than the specified width (default is True).
        """
        old_width = self.MT.col_positions[c + 1] - self.MT.col_positions[c]
        new_width = self.set_col_width(c, width=width, only_if_too_small=only_if_too_small)
        if self.column_width_resize_func is not None and old_width != new_width:
            self.column_width_resize_func(
                event_dict(
                    name="resize",
                    sheet=self.PAR.name,
                    resized_columns={c: {"old_size": old_width, "new_size": new_width}},
                )
            )

    # internal event use
    def click_checkbox(self, c, datacn=None, undo=True, redraw=True):
        """Handle the click event for a checkbox in the specified column.

        This method toggles the checkbox state for the specified column and 
        updates the corresponding cell data. It also triggers relevant events 
        and checks any associated functions.

        Args:
            c (int): The index of the column containing the checkbox.
            datacn (int or None): The index of the data column (default is None).
            undo (bool): If True, enables undo functionality (default is True).
            redraw (bool): If True, refreshes the display after the operation 
                (default is True).
        """
        if datacn is None:
            datacn = c if self.MT.all_columns_displayed else self.MT.displayed_columns[c]
        kwargs = self.get_cell_kwargs(datacn, key="checkbox")
        if kwargs["state"] == "normal":
            pre_edit_value = self.get_cell_data(datacn)
            if isinstance(self.MT._headers, list):
                value = not self.MT._headers[datacn] if isinstance(self.MT._headers[datacn], bool) else False
            elif isinstance(self.MT._headers, int):
                value = (
                    not self.MT.data[self.MT._headers][datacn]
                    if isinstance(self.MT.data[self.MT._headers][datacn], bool)
                    else False
                )
            else:
                value = False
            self.set_cell_data_undo(c, datacn=datacn, value=value, cell_resize=False)
            event_data = event_dict(
                name="end_edit_header",
                sheet=self.PAR.name,
                widget=self,
                cells_header={datacn: pre_edit_value},
                key="??",
                value=value,
                loc=c,
                column=c,
                boxes=self.MT.get_boxes(),
                selected=self.MT.selected,
            )
            if kwargs["check_function"] is not None:
                kwargs["check_function"](event_data)
            try_binding(self.extra_end_edit_cell_func, event_data)
        if redraw:
            self.MT.refresh()

    def get_cell_kwargs(self, datacn, key="dropdown", cell=True):
        """Retrieve the cell options for a specific cell and key.

        This method checks if the given cell (datacn) has associated options 
        for the specified key. If available, it returns the options as a 
        dictionary; otherwise, it returns an empty dictionary.

        Args:
            datacn (int): The index of the data column.
            key (Hashable): The specific option key to retrieve (default is 
                "dropdown").
            cell (bool): If True, checks for cell-specific options (default is 
                True).

        Returns:
            dict: The options associated with the specified cell and key, or 
                an empty dictionary if none exist.
        """
        if cell and datacn in self.cell_options and key in self.cell_options[datacn]:
            return self.cell_options[datacn][key]
        return {}

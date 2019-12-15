from ._tksheet_vars import *
from ._tksheet_other_classes import *

from collections import defaultdict, deque
from itertools import islice, repeat, accumulate, chain
from math import floor, ceil
from tkinter import ttk
import bisect
import csv as csv_module
import io
import pickle
import re
import tkinter as tk
import zlib
# for mac bindings
from platform import system as get_os


class ColumnHeaders(tk.Canvas):
    def __init__(self,
                 parentframe = None,
                 main_canvas = None,
                 row_index_canvas = None,
                 max_colwidth = None,
                 max_header_height = None,
                 default_header = None,
                 header_align = None,
                 header_background = None,
                 header_border_color = None,
                 header_grid_color = None,
                 header_foreground = None,
                 header_select_background = None,
                 header_select_foreground = None,
                 drag_and_drop_color = None,
                 resizing_line_color = None):
        tk.Canvas.__init__(self,parentframe,
                           background = header_background,
                           highlightthickness = 0)
        self.parentframe = parentframe
        self.extra_motion_func = None
        self.extra_b1_press_func = None
        self.extra_b1_motion_func = None
        self.extra_b1_release_func = None
        self.extra_double_b1_func = None
        self.ch_extra_drag_drop_func = None
        self.selection_binding_func = None
        self.shift_selection_binding_func = None
        self.drag_selection_binding_func = None
        self.default_hdr = 1 if default_header.lower() == "letters" else 0
        self.max_cw = float(max_colwidth)
        self.max_header_height = float(max_header_height)
        self.current_height = None    # is set from within MainTable() __init__ or from Sheet parameters
        self.MT = main_canvas         # is set from within MainTable() __init__
        self.RI = row_index_canvas    # is set from within MainTable() __init__
        self.TL = None                # is set from within TopLeftRectangle() __init__
        self.text_color = header_foreground
        self.grid_color = header_grid_color
        self.header_border_color = header_border_color
        self.selected_cells_background = header_select_background
        self.selected_cells_foreground = header_select_foreground
        self.drag_and_drop_color = drag_and_drop_color
        self.resizing_line_color = resizing_line_color
        self.align = header_align
        self.width_resizing_enabled = False
        self.height_resizing_enabled = False
        self.double_click_resizing_enabled = False
        self.col_selection_enabled = False
        self.drag_and_drop_enabled = False
        self.rc_delete_col_enabled = False
        self.rc_insert_col_enabled = False
        self.dragged_col = None
        self.visible_col_dividers = []
        self.col_height_resize_bbox = tuple()
        self.highlighted_cells = {}
        self.rsz_w = None
        self.rsz_h = None
        self.new_col_height = 0
        self.currently_resizing_width = False
        self.currently_resizing_height = False
        self.bind("<Motion>", self.mouse_motion)
        self.bind("<ButtonPress-1>", self.b1_press)
        self.bind("<Shift-ButtonPress-1>",self.shift_b1_press)
        self.bind("<B1-Motion>", self.b1_motion)
        self.bind("<ButtonRelease-1>", self.b1_release)
        self.bind("<Double-Button-1>", self.double_b1)
        
    def basic_bindings(self, onoff = "enable"):
        if onoff == "enable":
            self.bind("<Motion>", self.mouse_motion)
            self.bind("<ButtonPress-1>", self.b1_press)
            self.bind("<B1-Motion>", self.b1_motion)
            self.bind("<ButtonRelease-1>", self.b1_release)
            self.bind("<Double-Button-1>", self.double_b1)
        elif onoff == "disable":
            self.unbind("<Motion>")
            self.unbind("<ButtonPress-1>")
            self.unbind("<B1-Motion>")
            self.unbind("<ButtonRelease-1>")
            self.unbind("<Double-Button-1>")

    def set_height(self, new_height,set_TL = False):
        self.current_height = new_height
        self.config(height = new_height)
        if set_TL:
            self.TL.set_dimensions(new_h = new_height)

    def enable_bindings(self, binding):
        if binding == "column_width_resize":
            self.width_resizing_enabled = True
        if binding == "column_height_resize":
            self.height_resizing_enabled = True
        if binding == "double_click_column_resize":
            self.double_click_resizing_enabled = True
        if binding == "column_select":
            self.col_selection_enabled = True
        if binding == "drag_and_drop":
            self.drag_and_drop_enabled = True
        if binding == "rc_delete_column":
            self.rc_delete_col_enabled = True
            self.ch_rc_popup_menu.entryconfig("Delete Columns", state = "normal")
        if binding == "rc_insert_column":
            self.rc_insert_col_enabled = True
            self.ch_rc_popup_menu.entryconfig("Insert Column", state = "normal")

    def disable_bindings(self, binding):
        if binding == "column_width_resize":
            self.width_resizing_enabled = False
        if binding == "column_height_resize":
            self.height_resizing_enabled = False
        if binding == "double_click_column_resize":
            self.double_click_resizing_enabled = False
        if binding == "column_select":
            self.col_selection_enabled = False
        if binding == "drag_and_drop":
            self.drag_and_drop_enabled = False
        if binding == "rc_delete_column":
            self.rc_delete_col_enabled = False
            self.ch_rc_popup_menu.entryconfig("Delete Columns", state = "disabled")
        if binding == "rc_insert_column":
            self.rc_insert_col_enabled = False
            self.ch_rc_popup_menu.entryconfig("Insert Column", state = "disabled")

    def check_mouse_position_width_resizers(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        ov = None
        for x1, y1, x2, y2 in self.visible_col_dividers:
            if x >= x1 and y >= y1 and x <= x2 and y <= y2:
                ov = self.find_overlapping(x1, y1, x2, y2)
                break
        return ov

    def rc(self, event):
        self.focus_set()
        if self.MT.identify_col(x = event.x, allow_end = False) is None:
            self.MT.deselect("all")
            self.ch_rc_popup_menu.tk_popup(event.x_root, event.y_root)
        elif self.col_selection_enabled and all(v is None for v in (self.RI.rsz_h, self.RI.rsz_w, self.rsz_h, self.rsz_w)):
            c = self.MT.identify_col(x = event.x)
            if c < len(self.MT.col_positions) - 1:
                cols_selected = self.MT.anything_selected(exclude_rows = True, exclude_cells = True)
                if cols_selected:
                    x1 = self.MT.get_min_selected_cell_x()
                    x2 = self.MT.get_max_selected_cell_x()
                else:
                    x1 = None
                    x2 = None
                if all(e is not None for e in (x1, x2)) and c >= x1 and c <= x2:
                    self.ch_rc_popup_menu.tk_popup(event.x_root, event.y_root)
                else:
                    self.select_col(c, redraw = True)
                    self.ch_rc_popup_menu.tk_popup(event.x_root, event.y_root)

    def shift_b1_press(self, event):
        x = event.x
        c = self.MT.identify_col(x = x)
        if self.drag_and_drop_enabled or self.col_selection_enabled and self.rsz_h is None and self.rsz_w is None:
            if c < len(self.MT.col_positions) - 1:
                if c not in self.MT.selected_cols and self.col_selection_enabled:
                    c = int(c)
                    if self.MT.currently_selected and self.MT.currently_selected[0] == "column":
                        min_c = int(self.MT.currently_selected[1])
                        self.MT.sel_C = defaultdict(int)
                        self.MT.sel_R = defaultdict(int)
                        self.MT.selected_cols = set()
                        self.MT.selected_rows = set()
                        if c > min_c:
                            self.MT.selected_cols = set(range(min_c, c + 1))
                            self.MT.selection_boxes = {(0, min_c, len(self.MT.row_positions) - 1, c + 1)}
                        elif c < min_c:
                            self.MT.selected_cols = set(range(c, min_c + 1))
                            self.MT.selection_boxes = {(0, c, len(self.MT.row_positions) - 1, min_c + 1)}
                    else:
                        self.select_col(c)
                    self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
                    if self.shift_selection_binding_func is not None:
                        self.shift_selection_binding_func(("shift_select_columns", tuple(sorted(self.MT.selected_cols))))
                elif c in self.MT.selected_cols:
                    self.dragged_col = c

    def mouse_motion(self, event):
        if not self.currently_resizing_height and not self.currently_resizing_width:
            x = self.canvasx(event.x)
            y = self.canvasy(event.y)
            mouse_over_resize = False
            if self.width_resizing_enabled and not mouse_over_resize:
                ov = self.check_mouse_position_width_resizers(event)
                if ov is not None:
                    for itm in ov:
                        tgs = self.gettags(itm)
                        if "v" == tgs[0]:
                            break
                    c = int(tgs[1])
                    self.rsz_w = c
                    self.config(cursor = "sb_h_double_arrow")
                    mouse_over_resize = True
                else:
                    self.rsz_w = None
            if self.height_resizing_enabled and not mouse_over_resize:
                try:
                    x1, y1, x2, y2 = self.col_height_resize_bbox[0], self.col_height_resize_bbox[1], self.col_height_resize_bbox[2], self.col_height_resize_bbox[3]
                    if x >= x1 and y >= y1 and x <= x2 and y <= y2:
                        self.config(cursor = "sb_v_double_arrow")
                        self.rsz_h = True
                        mouse_over_resize = True
                    else:
                        self.rsz_h = None
                except:
                    self.rsz_h = None
            if not mouse_over_resize:
                self.MT.reset_mouse_motion_creations()
        if self.extra_motion_func is not None:
            self.extra_motion_func(event)
        
    def b1_press(self, event = None):
        self.focus_set()
        self.MT.unbind("<MouseWheel>")
        x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
        if self.check_mouse_position_width_resizers(event) is None:
            self.rsz_w = None
        if self.width_resizing_enabled and self.rsz_w is not None:
            self.currently_resizing_width = True
            x = self.MT.col_positions[self.rsz_w]
            line2x = self.MT.col_positions[self.rsz_w - 1]
            self.create_line(x, 0, x, self.current_height, width = 1, fill = self.resizing_line_color, tag = "rwl")
            self.MT.create_line(x, y1, x, y2, width = 1, fill = self.resizing_line_color, tag = "rwl")
            self.create_line(line2x, 0, line2x, self.current_height,width = 1, fill = self.resizing_line_color, tag = "rwl2")
            self.MT.create_line(line2x, y1, line2x, y2, width = 1, fill = self.resizing_line_color, tag = "rwl2")
        elif self.height_resizing_enabled and self.rsz_w is None and self.rsz_h is not None:
            self.currently_resizing_height = True
            y = event.y
            if y < self.MT.hdr_min_rh:
                y = int(self.MT.hdr_min_rh)
            self.new_col_height = y
            self.create_line(x1, y, x2, y, width = 1, fill = self.resizing_line_color, tag = "rhl")
        elif self.MT.identify_col(x = event.x, allow_end = False) is None:
            self.MT.deselect("all")
        elif self.col_selection_enabled and self.rsz_w is None and self.rsz_h is None:
            c = self.MT.identify_col(x = event.x)
            if c < len(self.MT.col_positions) - 1:
                self.select_col(c, redraw = True)
        if self.extra_b1_press_func is not None:
            self.extra_b1_press_func(event)
    
    def b1_motion(self, event):
        x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
        if self.width_resizing_enabled and self.rsz_w is not None and self.currently_resizing_width:
            x = self.canvasx(event.x)
            size = x - self.MT.col_positions[self.rsz_w - 1]
            if not size <= self.MT.min_cw and size < self.max_cw:
                self.delete("rwl")
                self.MT.delete("rwl")
                self.create_line(x, 0, x, self.current_height, width = 1, fill = self.resizing_line_color, tag = "rwl")
                self.MT.create_line(x, y1, x, y2, width = 1, fill = self.resizing_line_color, tag = "rwl")
        elif self.height_resizing_enabled and self.rsz_h is not None and self.currently_resizing_height:
            evy = event.y
            self.delete("rhl")
            self.MT.delete("rhl")
            if evy > self.current_height:
                y = self.MT.canvasy(evy - self.current_height)
                if evy > self.max_header_height:
                    evy = int(self.max_header_height)
                    y = self.MT.canvasy(evy - self.current_height)
                self.new_col_height = evy
                self.MT.create_line(x1, y, x2, y, width = 1, fill = self.resizing_line_color, tag = "rhl")
            else:
                y = evy
                if y < self.MT.hdr_min_rh:
                    y = int(self.MT.hdr_min_rh)
                self.new_col_height = y
                self.create_line(x1, y, x2, y, width = 1, fill = self.resizing_line_color, tag = "rhl")
        elif self.drag_and_drop_enabled and self.col_selection_enabled and self.MT.selected_cols and self.rsz_h is None and self.rsz_w is None and self.dragged_col is not None:
            x = self.canvasx(event.x)
            if x > 0 and x < self.MT.col_positions[-1]:
                x = event.x
                wend = self.winfo_width() 
                if x >= wend - 0:
                    if x >= wend + 15:
                        self.MT.xview_scroll(2, "units")
                        self.xview_scroll(2, "units")
                    else:
                        self.MT.xview_scroll(1, "units")
                        self.xview_scroll(1, "units")
                    self.MT.main_table_redraw_grid_and_text(redraw_header = True)
                elif x <= 0:
                    if x >= -40:
                        self.MT.xview_scroll(-1, "units")
                        self.xview_scroll(-1, "units")
                    else:
                        self.MT.xview_scroll(-2, "units")
                        self.xview_scroll(-2, "units")
                    self.MT.main_table_redraw_grid_and_text(redraw_header = True)
                rectw = self.MT.col_positions[max(self.MT.selected_cols) + 1] - self.MT.col_positions[min(self.MT.selected_cols)]
                start = self.canvasx(event.x - int(rectw / 2))
                end = self.canvasx(event.x + int(rectw / 2))
                self.delete("dd")
                self.create_rectangle(start, 0, end, self.current_height - 1, fill = self.drag_and_drop_color, outline = self.grid_color, tag = "dd")
                self.tag_raise("dd")
                self.tag_raise("t")
                self.tag_raise("v")
        elif self.MT.drag_selection_enabled and self.col_selection_enabled and self.rsz_h is None and self.rsz_w is None:
            end_col = self.MT.identify_col(x = event.x)
            if end_col < len(self.MT.col_positions) - 1 and len(self.MT.currently_selected) == 2:
                if self.MT.currently_selected[0] == "column":
                    start_col = self.MT.currently_selected[1]
                    self.MT.selected_cols = set()
                    self.MT.selected_rows = set()
                    self.MT.sel_R = defaultdict(int)
                    self.MT.sel_C = defaultdict(int)
                    if end_col >= start_col:
                        self.MT.selected_cols = set(range(start_col, end_col + 1))
                        self.MT.selection_boxes = {(0, start_col, len(self.MT.row_positions) - 1, end_col + 1)}
                    elif end_col < start_col:
                        self.MT.selected_cols = set(range(end_col, start_col + 1))
                        self.MT.selection_boxes = {(0, end_col, len(self.MT.row_positions) - 1, start_col + 1)}
                    if self.drag_selection_binding_func is not None:
                        self.drag_selection_binding_func(("drag_select_columns", tuple(sorted(self.MT.selected_cols))))
                if event.x > self.winfo_width():
                    try:
                        self.MT.xview_scroll(1, "units")
                        self.xview_scroll(1, "units")
                    except:
                        pass
                elif event.x < 0 and self.canvasx(self.winfo_width()) > 0:
                    try:
                        self.xview_scroll(-1, "units")
                        self.MT.xview_scroll(-1, "units")
                    except:
                        pass
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = False)
        if self.extra_b1_motion_func is not None:
            self.extra_b1_motion_func(event)
            
    def b1_release(self, event = None):
        self.MT.bind("<MouseWheel>", self.MT.mousewheel)
        if self.width_resizing_enabled and self.rsz_w is not None and self.currently_resizing_width:
            self.currently_resizing_width = False
            new_col_pos = self.coords("rwl")[0]
            self.delete("rwl", "rwl2")
            self.MT.delete("rwl", "rwl2")
            size = new_col_pos - self.MT.col_positions[self.rsz_w - 1]
            if size < self.MT.min_cw:
                new_row_pos = ceil(self.MT.col_positions[self.rsz_w - 1] + self.MT.min_cw)
            elif size > self.max_cw:
                new_col_pos = floor(self.MT.col_positions[self.rsz_w - 1] + self.max_cw)
            increment = new_col_pos - self.MT.col_positions[self.rsz_w]
            self.MT.col_positions[self.rsz_w + 1:] = [e + increment for e in islice(self.MT.col_positions, self.rsz_w + 1, len(self.MT.col_positions))]
            self.MT.col_positions[self.rsz_w] = new_col_pos
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        elif self.height_resizing_enabled and self.rsz_h is not None and self.currently_resizing_height:
            self.currently_resizing_height = False
            self.delete("rhl")
            self.MT.delete("rhl")
            self.set_height(self.new_col_height,set_TL = True)
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        if self.drag_and_drop_enabled and self.col_selection_enabled and self.MT.selected_cols and self.rsz_h is None and self.rsz_w is None and self.dragged_col is not None:
            self.delete("dd")
            x = event.x
            c = self.MT.identify_col(x = x)
            if c != self.dragged_col and c is not None and c not in self.MT.selected_cols and len(self.MT.selected_cols) != (len(self.MT.col_positions) - 1):
                orig_selected_cols = sorted(self.MT.selected_cols)
                if len(orig_selected_cols) > 1:
                    orig_min = orig_selected_cols[0]
                    orig_max = orig_selected_cols[1]
                    start_idx = bisect.bisect_left(orig_selected_cols, self.dragged_col)
                    forward_gap = get_index_of_gap_in_sorted_integer_seq_forward(orig_selected_cols, start_idx)
                    reverse_gap = get_index_of_gap_in_sorted_integer_seq_reverse(orig_selected_cols, start_idx)
                    if forward_gap is not None:
                        orig_selected_cols[:] = orig_selected_cols[:forward_gap]
                    if reverse_gap is not None:
                        orig_selected_cols[:] = orig_selected_cols[reverse_gap:]
                    if forward_gap is not None or reverse_gap is not None:
                        self.MT.selected_cols = set(orig_selected_cols)
                colsiter = sorted(self.MT.selected_cols)
                rm1start = colsiter[0]
                rm1end = colsiter[-1] + 1
                rm2start = rm1start + (rm1end - rm1start)
                rm2end = rm1end + (rm1end - rm1start)
                totalcols = len(colsiter)
                if self.dragged_col < c and c >= len(self.MT.col_positions) - 1:
                    c -= 1
                if self.ch_extra_drag_drop_func is not None:
                    self.ch_extra_drag_drop_func(self.MT.selected_cols, int(c))
                c_ = int(c)
                if rm1end < c:
                    c += 1
                if self.ch_extra_drag_drop_func is None:
                    if self.MT.all_columns_displayed:
                        if rm1start > c:
                            for rn in range(len(self.MT.data_ref)):
                                try:
                                    self.MT.data_ref[rn][c:c] = self.MT.data_ref[rn][rm1start:rm1end]
                                    self.MT.data_ref[rn][rm2start:rm2end] = []
                                except:
                                    continue
                            if not isinstance(self.MT.my_hdrs, int) and self.MT.my_hdrs:
                                try:
                                    self.MT.my_hdrs[c:c] = self.MT.my_hdrs[rm1start:rm1end]
                                    self.MT.my_hdrs[rm2start:rm2end] = []
                                except:
                                    pass
                        else:
                            for rn in range(len(self.MT.data_ref)):
                                try:
                                    self.MT.data_ref[rn][c:c] = self.MT.data_ref[rn][rm1start:rm1end]
                                    self.MT.data_ref[rn][rm1start:rm1end] = []
                                except:
                                    continue
                            if not isinstance(self.MT.my_hdrs, int) and self.MT.my_hdrs:
                                try:
                                    self.MT.my_hdrs[c:c] = self.MT.my_hdrs[rm1start:rm1end]
                                    self.MT.my_hdrs[rm1start:rm1end] = []
                                except:
                                    pass
                    else:
                        if rm1start > c:
                            self.MT.displayed_columns[c:c] = self.MT.displayed_columns[rm1start:rm1end]
                            self.MT.displayed_columns[rm2start:rm2end] = []
                        else:
                            self.MT.displayed_columns[c:c] = self.MT.displayed_columns[rm1start:rm1end]
                            self.MT.displayed_columns[rm1start:rm1end] = []
                cws = [int(b - a) for a, b in zip(self.MT.col_positions, islice(self.MT.col_positions, 1, len(self.MT.col_positions)))]
                if rm1start > c:
                    cws[c:c] = cws[rm1start:rm1end]
                    cws[rm2start:rm2end] = []
                else:
                    cws[c:c] = cws[rm1start:rm1end]
                    cws[rm1start:rm1end] = []
                self.MT.col_positions = [0] + list(accumulate(width for width in cws))
                if (c_ - 1) + totalcols > len(self.MT.col_positions) - 1:
                    self.MT.selected_cols = set(range(len(self.MT.col_positions) - 1 - totalcols, len(self.MT.col_positions) - 1))
                    self.MT.selection_boxes = {(0, len(self.MT.col_positions) - 1 - totalcols, len(self.MT.row_positions) - 1, len(self.MT.col_positions) - 1)}
                else:
                    if rm1start > c:
                        self.MT.selected_cols = set(range(c_, c_ + totalcols))
                        self.MT.selection_boxes = {(0, c_, len(self.MT.row_positions) - 1, c_ + totalcols)}
                    else:
                        self.MT.selected_cols = set(range(c_ + 1 - totalcols, c_ + 1))
                        self.MT.selection_boxes = {(0, c_ + 1 - totalcols, len(self.MT.row_positions) - 1, c_ + 1)}
                if self.MT.undo_enabled:
                    self.MT.undo_storage.append(zlib.compress(pickle.dumps(("move_cols", min(orig_selected_cols), (min(self.MT.selected_cols), max(self.MT.selected_cols))))))
                self.MT.selected_rows = set()
                self.MT.sel_R = defaultdict(int)
                self.MT.sel_C = defaultdict(int)
                self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        self.dragged_col = None
        self.currently_resizing_width = False
        self.currently_resizing_height = False
        self.rsz_w = None
        self.rsz_h = None
        self.mouse_motion(event)
        if self.extra_b1_release_func is not None:
            self.extra_b1_release_func(event)

    def double_b1(self, event = None):
        self.focus_set()
        if self.double_click_resizing_enabled and self.width_resizing_enabled and self.rsz_w is not None and not self.currently_resizing_width:
            # condition check if trying to resize width:
            col = self.rsz_w - 1
            self.set_col_width(col)
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
            self.mouse_motion(event)
        self.rsz_w = None
        if self.extra_double_b1_func is not None:
            self.extra_double_b1_func(event)

    def highlight_cells(self, c = 0, cells = tuple(), bg = None, fg = None, redraw = False):
        if bg is None and fg is None:
            return
        if cells:
            self.highlighted_cells = {c_: (bg, fg)  for c_ in cells}
        else:
            self.highlighted_cells[c] = (bg, fg)
        if redraw:
            self.MT.main_table_redraw_grid_and_text(True, False)

    def select_col(self, c, redraw = False, keep_other_selections = False):
        c = int(c)
        ignore_keep = False
        if keep_other_selections:
            if c in self.MT.selected_cols:
                self.MT.currently_selected = ("column", c)
            else:
                ignore_keep = True
        if ignore_keep or not keep_other_selections:
            self.MT.currently_selected = ("column", c)
            self.MT.selected_cols = {c}
        self.MT.sel_R = defaultdict(int)
        self.MT.sel_C = defaultdict(int)
        self.MT.selected_rows = set()
        self.MT.selection_boxes = {(0, c, len(self.MT.row_positions) - 1, c + 1)}
        if redraw:
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        if self.selection_binding_func is not None:
            self.selection_binding_func(("select_column", int(c)))

    def add_selection(self, c, redraw = False, run_binding_func = True, set_as_current = True, mod_selection_boxes = True):
        c = int(c)
        if set_as_current:
            self.MT.currently_selected = ("column", c)
        self.MT.selected_rows = set()
        self.MT.sel_R = defaultdict(int)
        self.MT.sel_C = defaultdict(int)
        if mod_selection_boxes:
            for y1, x1, y2, x2 in tuple(self.selection_boxes):
                if x2 - x1 == 1 and y2 - y1 == 1:
                    if r == y1 - 1 or r == y2:
                        if c == x1 - 1 or c == x2:
                            self.selection_boxes.discard((y1, x1, y2, x2))
                            if r == y1 - 1:
                                self.selection_boxes.add((y1 - 1, x1, y2, x2))
                            elif r == y2:
                                self.selection_boxes.add((y1, x1, y2 + 1, x2))
                            elif c == x1 - 1:
                                self.selection_boxes.add((y1, x1 - 1, y2, x2))
                            elif c == x2:
                                self.selection_boxes.add((y1, x1, y2, x2 + 1))
                            break
        self.MT.selection_boxes = {(0, c, len(self.MT.row_positions) - 1, c + 1)}
        self.MT.selected_cols.add(c)
        if redraw:
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        if self.selection_binding_func is not None and run_binding_func:
            self.selection_binding_func(("select_column", int(c)))

    def set_col_width(self, col, width = None, only_set_if_too_small = False):
        if col < 0:
            return
        if width is None:
            if self.MT.all_columns_displayed:
                try:
                    hw = self.MT.GetHdrTextWidth(self.GetLargestWidth(self.MT.my_hdrs[col])) + 10
                except:
                    hw = self.MT.GetHdrTextWidth(str(col)) + 10
                x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
                start_row, end_row = self.MT.get_visible_rows(y1, y2)
                dtw = 0
                for r in islice(self.MT.data_ref, start_row, end_row):
                    try:
                        w = self.MT.GetTextWidth(self.GetLargestWidth(r[col]))
                        if w > dtw:
                            dtw = w
                    except:
                        pass
            else:
                try:
                    hw = self.MT.GetHdrTextWidth(self.GetLargestWidth(self.MT.my_hdrs[self.MT.displayed_columns[col]])) + 10 
                except:
                    hw = self.MT.GetHdrTextWidth(str(col)) + 10
                x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
                start_row,end_row = self.MT.get_visible_rows(y1, y2)
                dtw = 0
                for r in islice(self.MT.data_ref, start_row,end_row):
                    try:
                        w = self.MT.GetTextWidth(self.GetLargestWidth(r[self.MT.displayed_columns[col]]))
                        if w > dtw:
                            dtw = w
                    except:
                        pass 
            dtw += 10
            if dtw > hw:
                width = dtw
            else:
                width = hw
        if width <= self.MT.min_cw:
            width = int(self.MT.min_cw)
        elif width > self.max_cw:
            width = int(self.max_cw)
        if only_set_if_too_small:
            if width <= self.MT.col_positions[col + 1] - self.MT.col_positions[col]:
                return
        new_col_pos = self.MT.col_positions[col] + width
        increment = new_col_pos - self.MT.col_positions[col + 1]
        self.MT.col_positions[col + 2:] = [e + increment for e in islice(self.MT.col_positions, col + 2, len(self.MT.col_positions))]
        self.MT.col_positions[col + 1] = new_col_pos

    def GetLargestWidth(self, cell):
        return max(cell.split("\n"), key = self.MT.GetTextWidth)

    def redraw_grid_and_text(self, last_col_line_pos, x1, x_stop, start_col, end_col):
        try:
            self.configure(scrollregion = (0, 0, last_col_line_pos + 150, self.current_height))
            self.delete("h", "v", "t", "s", "fv")
            self.visible_col_dividers = []
            x = self.MT.col_positions[start_col]
            self.create_line(x, 0, x, self.current_height, fill = self.grid_color, width = 1, tag = "fv")
            self.col_height_resize_bbox = (x1, self.current_height - 4, x_stop, self.current_height)
            yend = self.current_height - 5
            if self.width_resizing_enabled:
                for c in range(start_col + 1, end_col):
                    x = self.MT.col_positions[c]
                    self.visible_col_dividers.append((x - 4, 1, x + 4, yend))
                    self.create_line(x, 0, x, self.current_height, fill = self.grid_color, width = 1, tag = ("v", f"{c}"))
            else:
                for c in range(start_col + 1, end_col):
                    x = self.MT.col_positions[c]
                    self.create_line(x, 0, x, self.current_height, fill = self.grid_color, width = 1, tag = ("v", f"{c}"))
            top = self.canvasy(0)
            if self.MT.hdr_fl_ins + self.MT.hdr_half_txt_h > top:
                incfl = True
            else:
                incfl = False
            c_2 = self.selected_cells_background if self.selected_cells_background.startswith("#") else Color_Map_[self.selected_cells_background]
            if self.MT.all_columns_displayed:
                if self.align == "center":
                    for c in range(start_col, end_col - 1):
                        fc = self.MT.col_positions[c]
                        sc = self.MT.col_positions[c + 1]
                        if c in self.highlighted_cells and (c in self.MT.sel_C or c in self.MT.selected_cols):
                            c_1 = self.highlighted_cells[c][0] if self.highlighted_cells[c][0].startswith("#") else Color_Map_[self.highlighted_cells[c][0]]
                            self.create_rectangle(fc + 1,
                                                  0,
                                                  sc,
                                                  self.current_height - 1,
                                                  fill = (f"#{int((int(c_1[1:3], 16) + int(c_2[1:3], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[3:5], 16) + int(c_2[3:5], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[5:], 16) + int(c_2[5:], 16)) / 2):02X}"),
                                                  outline = "",
                                                  tag = "s")
                            tf = self.selected_cells_foreground if self.highlighted_cells[c][1] is None else self.highlighted_cells[c][1]
                        elif (c in self.MT.sel_C or c in self.MT.selected_cols):
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.selected_cells_background, outline = "", tag = "s")
                            tf = self.selected_cells_foreground
                        elif c in self.highlighted_cells:
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.highlighted_cells[c][0], outline = "", tag = "s")
                            tf = self.text_color if self.highlighted_cells[c][1] is None else self.highlighted_cells[c][1]
                        else:
                            tf = self.text_color
                        if fc + 7 > x_stop:
                            continue
                        mw = sc - fc - 5
                        x = fc + floor(mw / 2)
                        if isinstance(self.MT.my_hdrs, int):
                            try:
                                lns = self.MT.data_ref[self.MT.my_hdrs][c].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        else:
                            try:
                                lns = self.MT.my_hdrs[c].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        y = self.MT.hdr_fl_ins
                        if incfl:
                            fl = lns[0]
                            t = self.create_text(x, y, text = fl, fill = tf, font = self.MT.my_hdr_font, anchor = "center", tag = "t")
                            wd = self.bbox(t)
                            wd = wd[2] - wd[0]
                            if wd > mw:
                                tl = len(fl)
                                slce = tl - floor(tl * (mw / wd))
                                if slce % 2:
                                    slce += 1
                                else:
                                    slce += 2
                                slce = int(slce / 2)
                                fl = fl[slce:tl - slce]
                                self.itemconfig(t, text = fl)
                                wd = self.bbox(t)
                                while wd[2] - wd[0] > mw:
                                    fl = fl[1: - 1]
                                    self.itemconfig(t, text = fl)
                                    wd = self.bbox(t)
                        if len(lns) > 1:
                            stl = int((top - y) / self.MT.hdr_xtra_lines_increment) - 1
                            if stl < 1:
                                stl = 1
                            y += (stl * self.MT.hdr_xtra_lines_increment)
                            if y + self.MT.hdr_half_txt_h < self.current_height:
                                for i in range(stl, len(lns)):
                                    txt = lns[i]
                                    t = self.create_text(x, y, text = txt, fill = tf, font = self.MT.my_hdr_font, anchor = "center", tag = "t")
                                    wd = self.bbox(t)
                                    wd = wd[2] - wd[0]
                                    if wd > mw:
                                        tl = len(txt)
                                        slce = tl - floor(tl * (mw / wd))
                                        if slce % 2:
                                            slce += 1
                                        else:
                                            slce += 2
                                        slce = int(slce / 2)
                                        txt = txt[slce:tl - slce]
                                        self.itemconfig(t, text = txt)
                                        wd = self.bbox(t)
                                        while wd[2] - wd[0] > mw:
                                            txt = txt[1: - 1]
                                            self.itemconfig(t, text = txt)
                                            wd = self.bbox(t)
                                    y += self.MT.hdr_xtra_lines_increment
                                    if y + self.MT.hdr_half_txt_h > self.current_height:
                                        break
                elif self.align == "w":
                    for c in range(start_col, end_col - 1):
                        fc = self.MT.col_positions[c]
                        sc = self.MT.col_positions[c + 1]
                        if c in self.highlighted_cells and (c in self.MT.sel_C or c in self.MT.selected_cols):
                            c_1 = self.highlighted_cells[c][0] if self.highlighted_cells[c][0].startswith("#") else Color_Map_[self.highlighted_cells[c][0]]
                            self.create_rectangle(fc + 1,
                                                  0,
                                                  sc,
                                                  self.current_height - 1,
                                                  fill = (f"#{int((int(c_1[1:3], 16) + int(c_2[1:3], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[3:5], 16) + int(c_2[3:5], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[5:], 16) + int(c_2[5:], 16)) / 2):02X}"),
                                                  outline = "",
                                                  tag = "s")
                            tf = self.selected_cells_foreground if self.highlighted_cells[c][1] is None else self.highlighted_cells[c][1]
                        elif (c in self.MT.sel_C or c in self.MT.selected_cols):
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.selected_cells_background, outline = "", tag = "s")
                            tf = self.selected_cells_foreground
                        elif c in self.highlighted_cells:
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.highlighted_cells[c][0], outline = "", tag = "s")
                            tf = self.text_color if self.highlighted_cells[c][1] is None else self.highlighted_cells[c][1]
                        else:
                            tf = self.text_color
                        mw = sc - fc - 5
                        x = fc + 7
                        if x > x_stop:
                            continue
                        if isinstance(self.MT.my_hdrs, int):
                            try:
                                lns = self.MT.data_ref[self.MT.my_hdrs][c].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        else:
                            try:
                                lns = self.MT.my_hdrs[c].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        y = self.MT.hdr_fl_ins
                        if incfl:
                            fl = lns[0]
                            t = self.create_text(x, y, text = fl, fill = tf, font = self.MT.my_hdr_font, anchor = "w", tag = "t")
                            wd = self.bbox(t)
                            wd = wd[2] - wd[0]
                            if wd > mw:
                                nl = int(len(fl) * (mw / wd)) - 1
                                self.itemconfig(t, text = fl[:nl])
                                wd = self.bbox(t)
                                while wd[2] - wd[0] > mw:
                                    nl -= 1
                                    self.dchars(t, nl)
                                    wd = self.bbox(t)
                        if len(lns) > 1:
                            stl = int((top - y) / self.MT.hdr_xtra_lines_increment) - 1
                            if stl < 1:
                                stl = 1
                            y += (stl * self.MT.hdr_xtra_lines_increment)
                            if y + self.MT.hdr_half_txt_h < self.current_height:
                                for i in range(stl, len(lns)):
                                    txt = lns[i]
                                    t = self.create_text(x, y, text = txt, fill = tf, font = self.MT.my_hdr_font, anchor = "w", tag = "t")
                                    wd = self.bbox(t)
                                    wd = wd[2] - wd[0]
                                    if wd > mw:
                                        nl = int(len(txt) * (mw / wd)) - 1
                                        self.itemconfig(t, text = txt[:nl])
                                        wd = self.bbox(t)
                                        while wd[2] - wd[0] > mw:
                                            nl -= 1
                                            self.dchars(t, nl)
                                            wd = self.bbox(t)
                                    y += self.MT.hdr_xtra_lines_increment
                                    if y + self.MT.hdr_half_txt_h > self.current_height:
                                        break
            else:
                if self.align == "center":
                    for c in range(start_col, end_col - 1):
                        fc = self.MT.col_positions[c]
                        sc = self.MT.col_positions[c + 1]
                        if self.MT.displayed_columns[c] in self.highlighted_cells and (c in self.MT.sel_C or c in self.MT.selected_cols):
                            c_1 = self.highlighted_cells[self.MT.displayed_columns[c]][0] if self.highlighted_cells[self.MT.displayed_columns[c]][0].startswith("#") else Color_Map_[self.highlighted_cells[self.MT.displayed_columns[c]][0]]
                            self.create_rectangle(fc + 1,
                                                  0,
                                                  sc,
                                                  self.current_height - 1,
                                                  fill = (f"#{int((int(c_1[1:3], 16) + int(c_2[1:3], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[3:5], 16) + int(c_2[3:5], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[5:], 16) + int(c_2[5:], 16)) / 2):02X}"),
                                                  outline = "",
                                                  tag = "s")
                            tf = self.selected_cells_foreground if self.highlighted_cells[c][1] is None else self.highlighted_cells[c][1]
                        elif (c in self.MT.sel_C or c in self.MT.selected_cols):
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.selected_cells_background, outline = "", tag = "s")
                            tf = self.selected_cells_foreground
                        elif self.MT.displayed_columns[c] in self.highlighted_cells:
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.highlighted_cells[self.MT.displayed_columns[c]][0], outline = "", tag = "s")
                            tf = self.text_color if self.highlighted_cells[self.MT.displayed_columns[c]][1] is None else self.highlighted_cells[self.MT.displayed_columns[c]][1]
                        else:
                            tf = self.text_color
                        if fc + 7 > x_stop:
                            continue
                        mw = sc - fc - 5
                        x = fc + floor(mw / 2)
                        if isinstance(self.MT.my_hdrs, int):
                            try:
                                lns = self.MT.data_ref[self.MT.my_hdrs][c].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        else:
                            try:
                                lns = self.MT.my_hdrs[self.MT.displayed_columns[c]].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        y = self.MT.hdr_fl_ins
                        if incfl:
                            fl = lns[0]
                            t = self.create_text(x, y, text = fl, fill = tf, font = self.MT.my_hdr_font, anchor = "center", tag = "t")
                            wd = self.bbox(t)
                            wd = wd[2] - wd[0]
                            if wd > mw:
                                tl = len(fl)
                                slce = tl - floor(tl * (mw / wd))
                                if slce % 2:
                                    slce += 1
                                else:
                                    slce += 2
                                slce = int(slce / 2)
                                fl = fl[slce:tl - slce]
                                self.itemconfig(t, text = fl)
                                wd = self.bbox(t)
                                while wd[2] - wd[0] > mw:
                                    fl = fl[1: - 1]
                                    self.itemconfig(t, text = fl)
                                    wd = self.bbox(t)
                        if len(lns) > 1:
                            stl = int((top - y) / self.MT.hdr_xtra_lines_increment) - 1
                            if stl < 1:
                                stl = 1
                            y += (stl * self.MT.hdr_xtra_lines_increment)
                            if y + self.MT.hdr_half_txt_h < self.current_height:
                                for i in range(stl, len(lns)):
                                    txt = lns[i]
                                    t = self.create_text(x, y, text = txt, fill = tf, font = self.MT.my_hdr_font, anchor = "center", tag = "t")
                                    wd = self.bbox(t)
                                    wd = wd[2] - wd[0]
                                    if wd > mw:
                                        tl = len(txt)
                                        slce = tl - floor(tl * (mw / wd))
                                        if slce % 2:
                                            slce += 1
                                        else:
                                            slce += 2
                                        slce = int(slce / 2)
                                        txt = txt[slce:tl - slce]
                                        self.itemconfig(t, text = txt)
                                        wd = self.bbox(t)
                                        while wd[2] - wd[0] > mw:
                                            txt = txt[1: - 1]
                                            self.itemconfig(t, text = txt)
                                            wd = self.bbox(t)
                                    y += self.MT.hdr_xtra_lines_increment
                                    if y + self.MT.hdr_half_txt_h > self.current_height:
                                        break
                elif self.align == "w":
                    for c in range(start_col, end_col - 1):
                        fc = self.MT.col_positions[c]
                        sc = self.MT.col_positions[c + 1]
                        if self.MT.displayed_columns[c] in self.highlighted_cells and (c in self.MT.sel_C or c in self.MT.selected_cols):
                            c_1 = self.highlighted_cells[self.MT.displayed_columns[c]][0] if self.highlighted_cells[self.MT.displayed_columns[c]][0].startswith("#") else Color_Map_[self.highlighted_cells[self.MT.displayed_columns[c]][0]]
                            self.create_rectangle(fc + 1,
                                                  0,
                                                  sc,
                                                  self.current_height - 1,
                                                  fill = (f"#{int((int(c_1[1:3], 16) + int(c_2[1:3], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[3:5], 16) + int(c_2[3:5], 16)) / 2):02X}" +
                                                          f"{int((int(c_1[5:], 16) + int(c_2[5:], 16)) / 2):02X}"),
                                                  outline = "",
                                                  tag = "s")
                            tf = self.selected_cells_foreground if self.highlighted_cells[c][1] is None else self.highlighted_cells[c][1]
                        elif (c in self.MT.sel_C or c in self.MT.selected_cols):
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.selected_cells_background, outline = "", tag = "s")
                            tf = self.selected_cells_foreground
                        elif self.MT.displayed_columns[c] in self.highlighted_cells:
                            self.create_rectangle(fc + 1, 0, sc, self.current_height - 1, fill = self.highlighted_cells[self.MT.displayed_columns[c]][0], outline = "", tag = "s")
                            tf = self.text_color if self.highlighted_cells[self.MT.displayed_columns[c]][1] is None else self.highlighted_cells[self.MT.displayed_columns[c]][1]
                        else:
                            tf = self.text_color
                        mw = sc - fc - 5
                        x = fc + 7
                        if x > x_stop:
                            continue
                        if isinstance(self.MT.my_hdrs, int):
                            try:
                                lns = self.MT.data_ref[self.MT.my_hdrs][c].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        else:
                            try:
                                lns = self.MT.my_hdrs[self.MT.displayed_columns[c]].split("\n")
                            except:
                                lns = (num2alpha(c), ) if self.default_hdr else (f"{c + 1}", )
                        y = self.MT.hdr_fl_ins
                        if incfl:
                            fl = lns[0]
                            t = self.create_text(x, y, text = fl, fill = tf, font = self.MT.my_hdr_font, anchor = "w", tag = "t")
                            wd = self.bbox(t)
                            wd = wd[2] - wd[0]
                            if wd > mw:
                                nl = int(len(fl) * (mw / wd)) - 1
                                self.itemconfig(t, text = fl[:nl])
                                wd = self.bbox(t)
                                while wd[2] - wd[0] > mw:
                                    nl -= 1
                                    self.dchars(t, nl)
                                    wd = self.bbox(t)
                        if len(lns) > 1:
                            stl = int((top - y) / self.MT.hdr_xtra_lines_increment) - 1
                            if stl < 1:
                                stl = 1
                            y += (stl * self.MT.hdr_xtra_lines_increment)
                            if y + self.MT.hdr_half_txt_h < self.current_height:
                                for i in range(stl, len(lns)):
                                    txt = lns[i]
                                    t = self.create_text(x, y, text = txt, fill = tf, font = self.MT.my_hdr_font, anchor = "w", tag = "t")
                                    wd = self.bbox(t)
                                    wd = wd[2] - wd[0]
                                    if wd > mw:
                                        nl = int(len(txt) * (mw / wd)) - 1
                                        self.itemconfig(t, text = txt[:nl])
                                        wd = self.bbox(t)
                                        while wd[2] - wd[0] > mw:
                                            nl -= 1
                                            self.dchars(t, nl)
                                            wd = self.bbox(t)
                                    y += self.MT.hdr_xtra_lines_increment
                                    if y + self.MT.hdr_half_txt_h > self.current_height:
                                        break
            self.create_line(x1, self.current_height - 1, x_stop, self.current_height - 1, fill = self.header_border_color, width = 1, tag = "h")
        except:
            return
        
    def GetCellCoords(self, event = None, r = None, c = None):
        pass

    

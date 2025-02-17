<p align="center" width="100%">
    <img width="33%" src="https://github.com/ragardner/tksheet/assets/26602401/4124c3ce-cf62-4925-9158-c5bdf712765b">
</p>

# <div align="center">tksheet - python tkinter table widget</div>

[![PyPI version shields.io](https://img.shields.io/pypi/v/tksheet.svg)](https://pypi.python.org/pypi/tksheet/) ![python](https://img.shields.io/badge/python-3.8|3.9|3.10|3.11|3.12-blue) [![License: MIT](https://img.shields.io/badge/License-MIT%20-blue.svg)](https://github.com/ragardner/tksheet/blob/master/LICENSE.txt)

[![GitHub Release Date](https://img.shields.io/github/release-date-pre/ragardner/tksheet.svg)](https://github.com/ragardner/tksheet/releases) [![Downloads](https://img.shields.io/pypi/dm/tksheet.svg)](https://pypi.org/project/tksheet/)

|    **Help**       |                                                                  |
|-------------------|------------------------------------------------------------------|
| Versions 6.x.x -> | [Documentation Wiki](https://github.com/ragardner/tksheet/wiki/Version-6) | |
| Versions 7.x.x -> | [Documentation Wiki](https://github.com/ragardner/tksheet/wiki/Version-7) | |
| [Changelog](https://github.com/ragardner/tksheet/blob/master/docs/CHANGELOG.md) | |
| [Questions](https://github.com/ragardner/tksheet/wiki/Version-7#asking-questions) | |
| [Issues](https://github.com/ragardner/tksheet/wiki/Version-7#issues) | |
| [Suggestions](https://github.com/ragardner/tksheet/wiki/Version-7#enhancements-or-suggestions) | |

This library is maintained with the help of **[others](https://github.com/ragardner/tksheet/graphs/contributors)**. If you would like to contribute please read this [help section](https://github.com/ragardner/tksheet/wiki/Version-7#contributing).

## **Changes for versions `7`+:**

- **ALL** `extra_bindings()` event objects have changed, information [here](https://github.com/ragardner/tksheet/wiki/Version-7#bind-specific-table-functionality).
- The bound function for `extra_bindings()` with `"edit_cell"`/`"end_edit_cell"` **no longer** requires a return value and no longer sets the cell to the return value. Use [this](https://github.com/ragardner/tksheet/wiki/Version-7#validate-user-cell-edits) instead.
- `edit_cell_validation` has been removed and replaced with the function `edit_validation()`, information [here](https://github.com/ragardner/tksheet/wiki/Version-7#validate-user-cell-edits).
- Only Python versions >= `3.8` are supported.
- `tksheet` file names have been changed.
- Many other smaller changes, see the [changelog](https://github.com/ragardner/tksheet/blob/master/docs/CHANGELOG.md) for more information.

## **Features**

- Display and modify tabular data
- Stores its display data as a Python list of lists, sublists being rows
- Runs smoothly even with millions of rows/columns
- Edit cells directly
- Cell values can potentially be [any class](https://github.com/ragardner/tksheet/wiki/Version-7#data-formatting), the default is any class with a `__str__` method
- Drag and drop columns and rows
- Multiple line header and index cells
- Expand row heights and column widths
- Change fonts and font size (not for individual cells)
- Change any colors in the sheet
- Dropdowns, check boxes, progress bars
- [Treeview mode](https://github.com/ragardner/tksheet/wiki/Version-7#treeview-mode)
- [Hide rows and/or columns](https://github.com/ragardner/tksheet/wiki/Version-7#example-header-dropdown-boxes-and-row-filtering)
- Left `"w"`, Center `"center"` or Right `"e"` text alignment for any cell/row/column

```python
"""
Versions 7+ have succinct and easy to read syntax:
"""
# set data
sheet["A1"].data = "edited cell A1"

# get data
column_b = sheet["B"].data

# add 2 empty columns and add the change to undo stack
sheet.insert_columns(columns=2, idx=4, undo=True)

# delete columns 0 and 3 and add the change to undo stack
sheet.delete_columns(columns=[0, 3], undo=True)
```

### **light blue theme**

![tksheet light blue theme](https://github.com/user-attachments/assets/f40317d7-8b7f-43c5-9217-a77168b068ed)

### **dark theme**

![tksheet dark theme](https://github.com/user-attachments/assets/288453d6-5ac1-4d45-827f-45b24a3d05ed)

### **treeview mode**

![tksheet treeview](https://github.com/user-attachments/assets/159ab987-7612-4db7-98de-1f30c9680247)




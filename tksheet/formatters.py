try:
    from __future__ import annotations
except SyntaxError:
    # Requires Python 3.7
    pass

from collections.abc import Callable

from .vars import falsy, nonelike, truthy


def is_none_like(o):
    if (isinstance(o, str) and o.lower().replace(" ", "") in nonelike) or o in nonelike:
        return True
    return False


def to_int(o, **kwargs):
    if isinstance(o, int):
        return o
    return int(float(o))


def to_float(o, **kwargs):
    if isinstance(o, float):
        return o
    if isinstance(o, str) and o.endswith("%"):
        return float(o.replace("%", "")) / 100
    return float(o)


def to_bool(val, **kwargs):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.lower()
    else:
        v = val
    if "truthy" in kwargs:
        _truthy = kwargs["truthy"]
    else:
        _truthy = truthy
    if "falsy" in kwargs:
        _falsy = kwargs["falsy"]
    else:
        _falsy = falsy
    if v in _truthy:
        return True
    elif v in _falsy:
        return False
    raise ValueError(f'Cannot map "{val}" to bool.')


def try_to_bool(o, **kwargs):
    try:
        return to_bool(o)
    except Exception:
        return o


def is_bool_like(o, **kwargs):
    try:
        to_bool(o)
        return True
    except Exception:
        return False


def to_str(o, **kwargs):
    return "%s" % o


def float_to_str(v, **kwargs):
    """Convert a number to a string representation.

    This function converts an integer or float to its string representation. 
    It handles special cases for floats to eliminate decimal points when the 
    value is an integer and rounds the float to a specified number of decimal 
    places if provided.

    Args:
        v (int or float): The value to convert.
        **kwargs: Additional keyword arguments.
            - decimals (int): The number of decimal places to round to.

    Returns:
        str: The string representation of the number.

    Raises:
        TypeError: If "decimals" is provided but is not an int.
    """
    if isinstance(v, float):
        if v.is_integer():
            return "%d" % int(v)
        if "decimals" in kwargs:
            if not isinstance(kwargs["decimals"], int):
                raise TypeError("Expected 'decimals' to be an int.")
            if kwargs["decimals"]:
                return "%.*f" % (kwargs['decimals'], round(v, kwargs['decimals']))
            return "%d" % int(round(v, kwargs['decimals']))
    return "%s" % v


def percentage_to_str(v, **kwargs):
    """Convert a number to a percentage string representation.

    This function converts an integer or float to its percentage string representation.
    It multiplies the value by 100 and handles special cases for floats to eliminate 
    decimal points when the value is an integer and rounds the float to a specified 
    number of decimal places if provided.

    Args:
        v (int or float): The value to convert.
        **kwargs: Additional keyword arguments.
            - decimals (int): The number of decimal places to round to.

    Returns:
        str: The string representation of the percentage.

    Raises:
        TypeError: If "decimals" is provided but is not an int.
    """
    x = v
    if isinstance(v, (int, float)):
        x = v * 100
        if isinstance(x, float):
            if x.is_integer():
                return "%d%%" % int(x)
            if "decimals" in kwargs:
                if not isinstance(kwargs["decimals"], int):
                    raise TypeError("Expected 'decimals' to be an int.")
                if kwargs["decimals"]:
                    return "%.*f%%" % (kwargs['decimals'], round(x, kwargs['decimals']))
                return "%d%%" % int(round(x, kwargs['decimals']))
    return "%s%%" % x


def bool_to_str(v, **kwargs):
    return "%s" % v


def int_formatter(
    datatypes=tuple[object] | object,
    format_function=to_int,
    to_str_function=to_str,
    **kwargs,
) -> dict:
    """Create an integer formatter dictionary.

    This function constructs a formatter dictionary specifically for
    integer data types and associated formatting functions.

    Args:
        datatypes (tuple or object): The data types supported; defaults to int.
        format_function (Callable): The function to format the data; 
            defaults to `to_int`.
        to_str_function (Callable): The function to convert data to string; 
            defaults to `to_str`.
        **kwargs: Additional keyword arguments for customization.

    Returns:
        dict: A dictionary containing the integer formatting details.

    """
    return formatter(
        datatypes=datatypes,
        format_function=format_function,
        to_str_function=to_str_function,
        **kwargs,
    )


def float_formatter(
    datatypes=None,
    format_function=to_float,
    to_str_function=float_to_str,
    decimals=2,
    **kwargs
):
    return formatter(
        datatypes=datatypes,
        format_function=format_function,
        to_str_function=to_str_function,
        decimals=decimals,
        **kwargs,
    )


def percentage_formatter(
    datatypes=None,
    format_function=to_float,
    to_str_function=percentage_to_str,
    decimals=2,
    **kwargs
):
    return formatter(
        datatypes=datatypes,
        format_function=format_function,
        to_str_function=to_str_function,
        decimals=decimals,
        **kwargs,
    )


def bool_formatter(
    datatypes=None,
    format_function=to_bool,
    to_str_function=bool_to_str,
    invalid_value="NA",
    truthy_values=truthy,
    falsy_values=falsy,
    **kwargs
):
    return formatter(
        datatypes=datatypes,
        format_function=format_function,
        to_str_function=to_str_function,
        invalid_value=invalid_value,
        truthy_values=truthy_values,
        falsy_values=falsy_values,
        **kwargs,
    )


def formatter(
    datatypes,
    format_function,
    to_str_function=to_str,
    invalid_value="NaN",
    nullable=True,
    pre_format_function=None,
    post_format_function=None,
    clipboard_function=None,
    **kwargs,
):
    """Create a formatter dictionary for data processing.

    This function constructs a dictionary containing various formatting
    and processing functions along with associated configurations.

    Args:
        datatypes (tuple or object): The data types supported.
        format_function (Callable): The function to format the data.
        to_str_function (Callable): The function to convert data to
            string. Defaults to `to_str`.
        invalid_value (object): The value to return for invalid data.
            Defaults to "NaN".
        nullable (bool): Flag indicating if null values are allowed.
            Defaults to True.
        pre_format_function (Callable | None): A function to call before
            formatting.
        post_format_function (Callable | None): A function to call after
            formatting.
        clipboard_function (Callable | None): A function to handle
            clipboard operations.
        **kwargs: Additional keyword arguments for customization.

    Returns:
        dict: A dictionary containing the provided formatting details.

    """
    return {
        **dict(
            datatypes=datatypes,
            format_function=format_function,
            to_str_function=to_str_function,
            invalid_value=invalid_value,
            nullable=nullable,
            pre_format_function=pre_format_function,
            post_format_function=post_format_function,
            clipboard_function=clipboard_function,
        ),
        **kwargs,
    }


def format_data(
    value="",
    datatypes=None,
    nullable=True,
    pre_format_function=None,
    format_function=to_int,
    post_format_function=None,
    **kwargs
):
    """Format data according to specified functions and types.

    This function applies pre-formatting, formatting, and
    post-formatting to a value based on specified functions and type
    constraints.

    Args:
        value (object): The value to format; defaults to an empty
            string.
        datatypes (tuple or object): The expected data types for the
            value; defaults to int.
        nullable (bool): Indicates if the value can be null; defaults to
            True.
        pre_format_function (Callable): A function to apply before
            formatting.
        format_function (Callable): The function used for formatting;
            defaults to `to_int`.
        post_format_function (Callable): A function to apply after
            formatting.
        **kwargs: Additional keyword arguments for formatting functions.

    Returns:
        object: The formatted value, potentially modified by the
            formatting functions.
    """
    if pre_format_function:
        value = pre_format_function(value)
    if nullable and is_none_like(value):
        value = None
    else:
        try:
            value = format_function(value, **kwargs)
        except Exception:
            pass
    if post_format_function and isinstance(value, datatypes):
        value = post_format_function(value)
    return value


def data_to_str(
    value="",
    datatypes=None,
    nullable=True,
    invalid_value="NaN",
    to_str_function=None,
    **kwargs
):
    """Convert data to a string representation.

    This function converts a value to a string if it is of the expected
    data type and not null. It returns an invalid value if the type
    check fails or an empty string if the value is None and nullable.

    Args:
        value (object): The value to convert; defaults to an empty string.
        datatypes (tuple or object): The expected data types for the value; 
            defaults to int.
        nullable (bool): Indicates if the value can be null; defaults to True.
        invalid_value (object): The value to return if the type check fails; 
            defaults to "NaN".
        to_str_function (Callable): A function to convert the value to a string.
        **kwargs: Additional keyword arguments for the string conversion function.

    Returns:
        str: The string representation of the value, or the invalid value.
    """
    if not isinstance(value, datatypes):
        return invalid_value
    if value is None and nullable:
        return ""
    return to_str_function(value, **kwargs)


def get_data_with_valid_check(value="", datatypes=tuple(), invalid_value="NA"):
    """Check if the value is of the expected data type.

    This function returns the value if it is of the expected type(s),
    otherwise, it returns a specified invalid value.

    Args:
        value (object): The value to check; defaults to an empty string.
        datatypes (tuple or object): The expected data types for the value; 
            defaults to an empty tuple.
        invalid_value (object): The value to return if the type check fails; 
            defaults to "NA".

    Returns:
        object: The original value if valid, or the invalid value.
    """
    if isinstance(value, datatypes):
        return value
    return invalid_value


def get_clipboard_data(value="", clipboard_function=None, **kwargs):
    """Retrieve data from the clipboard or return the original value.

    This function checks if a clipboard function is provided and uses it 
    to retrieve data from the clipboard. If no function is provided, it 
    returns the original value if it is of a valid type (str, int, float, bool).
    If the value is of an unexpected type, it attempts to convert it to a 
    string representation.

    Args:
        value (object): The value to return if no clipboard function is used; 
            defaults to an empty string.
        clipboard_function (callable or None): A function to retrieve clipboard 
            data; defaults to None.
        **kwargs: Additional keyword arguments to pass to the clipboard function 
            or data conversion functions.

    Returns:
        object: The clipboard data or the original value.

    """
    if clipboard_function is not None:
        return clipboard_function(value, **kwargs)
    if isinstance(value, (str, int, float, bool)):
        return value
    return data_to_str(value, **kwargs)


class Formatter(object):
    """A class to format and validate data values.

    Args:
        value (object): The initial value to format.
        datatypes (tuple[object]): Accepted data types for the value.
        object (type): The object type to be used; defaults to int.
        format_function (callable): Function to format the value;
            defaults to to_int.
        to_str_function (callable): Function to convert the value to
            string; defaults to to_str.
        nullable (bool): Indicates if the value can be None; defaults to
            True.
        invalid_value (str): Value returned if the data is invalid;
            defaults to "NaN".
        pre_format_function (callable or None): Function applied before
            formatting; defaults to None.
        post_format_function (callable or None): Function applied after
            formatting; defaults to None.
        clipboard_function (callable or None): Function to retrieve
            clipboard data; defaults to None.
        **kwargs: Additional keyword arguments for formatting functions.
    """

    def __init__(
        self,
        value="",
        datatypes=(),
        object=int,
        format_function=None,
        to_str_function=None,
        nullable=True,
        invalid_value="NaN",
        pre_format_function=None,
        post_format_function=None,
        clipboard_function=None,
        **kwargs,
    ):
        if nullable:
            if isinstance(datatypes, (list, tuple)):
                datatypes = tuple({type_ for type_ in datatypes} | {type(None)})
            else:
                datatypes = (datatypes, type(None))
        elif isinstance(datatypes, (list, tuple)) and type(None) in datatypes:
            raise TypeError("Non-nullable cells cannot have NoneType as a datatype.")
        elif datatypes is type(None):
            raise TypeError("Non-nullable cells cannot have NoneType as a datatype.")
        self.kwargs = kwargs
        self.valid_datatypes = datatypes
        self.format_function = format_function or to_int
        self.to_str_function = to_str_function or to_str
        self.nullable = nullable
        self.invalid_value = invalid_value
        self.pre_format_function = pre_format_function
        self.post_format_function = post_format_function
        self.clipboard_function = clipboard_function
        try:
            self.value = self.format_data(value)
        except Exception:
            self.value = "%s" % value

    def __str__(self):
        if not self.valid():
            return self.invalid_value
        if self.value is None and self.nullable:
            return ""
        return self.to_str_function(self.value, **self.kwargs)

    def valid(self, value=None):
        if value is None:
            value = self.value
        if isinstance(value, self.valid_datatypes):
            return True
        return False

    def format_data(self, value):
        if self.pre_format_function:
            value = self.pre_format_function(value)
        value = None if (self.nullable and is_none_like(value)) else self.format_function(value, **self.kwargs)
        if self.post_format_function and self.valid(value):
            value = self.post_format_function(value)
        return value

    def get_data_with_valid_check(self):
        if self.valid():
            return self.value
        return self.invalid_value

    def get_clipboard_data(self):
        if self.clipboard_function is not None:
            return self.clipboard_function(self.value, **self.kwargs)
        if isinstance(self.value, (int, float, bool)):
            return self.value
        return self.__str__()

    def __eq__(self, __value):
        try:
            if hasattr(__value, "value"):
                return self.value == __value.value
        except Exception:
            pass
        if isinstance(__value, str):
            try:
                return self.value == self.format_data(__value)
            except Exception:
                pass
        return self.value == __value

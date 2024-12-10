"""Type stubs for pandas library."""

from typing import Any, Dict, List, Optional, Union

class DataFrame:
    """DataFrame class."""

    def __init__(
        self,
        data: Optional[Any] = None,
        index: Optional[Any] = None,
        columns: Optional[Any] = None,
        dtype: Optional[Any] = None,
        copy: bool = False,
    ) -> None: ...
    def to_html(
        self,
        buf: Optional[Any] = None,
        columns: Optional[List[str]] = None,
        col_space: Optional[Union[str, int, Dict[str, Union[str, int]]]] = None,
        header: bool = True,
        index: bool = True,
        na_rep: str = "NaN",
        formatters: Optional[Any] = None,
        float_format: Optional[Any] = None,
        sparsify: Optional[bool] = None,
        index_names: bool = True,
        justify: Optional[str] = None,
        max_rows: Optional[int] = None,
        max_cols: Optional[int] = None,
        show_dimensions: bool = False,
        decimal: str = ".",
        bold_rows: bool = True,
        classes: Optional[Union[str, List[str]]] = None,
        escape: bool = True,
        notebook: bool = False,
        border: Optional[int] = None,
        table_id: Optional[str] = None,
        render_links: bool = False,
        encoding: Optional[str] = None,
    ) -> str: ...

def read_excel(
    io: Union[str, Any],
    sheet_name: Optional[Union[str, int, List[Union[str, int]]]] = 0,
    header: Optional[Union[int, List[int]]] = 0,
    names: Optional[List[str]] = None,
    index_col: Optional[Union[int, List[int]]] = None,
    usecols: Optional[Union[int, str, List[Union[int, str]]]] = None,
    squeeze: bool = False,
    dtype: Optional[Any] = None,
    engine: Optional[str] = None,
    converters: Optional[Dict[Union[int, str], Any]] = None,
    true_values: Optional[List[str]] = None,
    false_values: Optional[List[str]] = None,
    skiprows: Optional[Union[int, List[int]]] = None,
    nrows: Optional[int] = None,
    na_values: Optional[Any] = None,
    keep_default_na: bool = True,
    na_filter: bool = True,
    verbose: bool = False,
    parse_dates: bool = False,
    date_parser: Optional[Any] = None,
    thousands: Optional[str] = None,
    comment: Optional[str] = None,
    skipfooter: int = 0,
    convert_float: bool = True,
    mangle_dupe_cols: bool = True,
    **kwargs: Any,
) -> Union[DataFrame, Dict[str, DataFrame]]: ...

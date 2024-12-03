import numpy as np
import datetime as dt
import pandas as pd

try:
    import xarray as xr
except ImportError:
    print(
        "Xarray is required, to install run 'pip.main(['install', '--user', 'xarray'])' "
    )
from pyam.core import IamDataFrame
from pyam.utils import META_IDX, IAMC_IDX


def read_netcdf(path):
    """Read timeseries or year-based data and meta-indicators from netCDF

    Parameters
    ----------
    path : :class:`pathlib.Path` or file-like object
        Scenario data file in netCDF format.

    Returns
    ----------
    IamDataFrame with meta indicators if available

    """

    _ds = xr.open_dataset(path)
    NETCDF_IDX = ["time", "model", "scenario", "region"]
    _list_variables = [i for i in _ds.to_dict()["data_vars"].keys()]
    _meta = []

    # Check if the time coordinate is years (integers) or date time-format
    is_year_based = all(
        isinstance(x, (int, np.integer)) for x in _ds.coords["time"].values
    )
    is_datetime = all(
        isinstance(x, (dt.date, dt.time, np.datetime64))
        for x in _ds.coords["time"].values
    )

    # Check if the xarray dataset has the correct coordinates, then get column names
    if is_year_based:
        _list_cols = IAMC_IDX + ["year", "value"]
    elif is_datetime:
        _list_cols = IAMC_IDX + ["time", "value"]
    else:
        raise TypeError(
            "Time coordinate needs to be integer (year-based) or datetime (timeseries), neither was given."
        )

    # read `data` table
    dfs = []
    for _var in _list_variables:
        # Check dimensions, if exactly as in META_IDX is a meta indicator
        # if exactly as in IAMC_IDX is a variable
        if set(_ds[_var].dims) == set(META_IDX):
            _meta.append(_var)
        elif set(_ds[_var].dims) == set(NETCDF_IDX):
            # convert the data into the IamDataframe format
            # if year-based data, get the time coordinate as "year"
            if is_year_based:
                _tmp = (
                    _ds[_var]
                    .to_dataframe()
                    .reset_index(drop=False)
                    .rename(columns={"time": "year", _var: "value"})
                )
            # if timeseries, keep the time coordinate as "time"
            elif is_datetime:
                _tmp = (
                    _ds[_var]
                    .to_dataframe()
                    .reset_index(drop=False)
                    .rename(columns={_var: "value"})
                )

            _tmp["variable"] = _ds[_var].long_name
            _tmp["unit"] = _ds[_var].unit
            dfs.append(_tmp)
        else:
            raise TypeError(
                f"Cannot define {_var}, different indices from META_IDX and IAMC_IDX."
            )
    _full_df = pd.concat(dfs).reset_index(drop=True)

    return IamDataFrame(
        _full_df,
        meta=_ds[_meta].to_dataframe() if _meta else None,
    )

import pandas as pd
import os
import lzma
import tarfile

from .utils import download_file, is_valid_archive
from .interp import DFInterpolator
from .logger import getLogger


def _safe_extractall(tar, path):
    """``tar.extractall`` with the 'data' filter where the interpreter has it.

    Python 3.12 deprecated extracting without an explicit filter and 3.14 made
    'data' the default; passing it explicitly keeps behaviour identical across
    3.9-3.14 and avoids the DeprecationWarning.
    """
    try:
        tar.extractall(path, filter="data")
    except TypeError:  # Python < 3.11.4 has no 'filter' keyword
        tar.extractall(path)


class Grid(object):
    """Generalized model grid manager object

    This is the base class for model grids, defined as a set of
    simulated or computed numbers as a function of a few regularly gridded
    parameters.  The canonical example for which this was developed
    is grids of stellar evolution models. This object manages all of the following:

    * Downloading and unpacking raw grids from remote URLs
        (usually as many files in multiple folders),
    * Re-formatting full grid into a single dataframe with multi-level index,
      and writing grid to disk in binary (HDF5) format.
    * Defining a `DFInterpolator` object that allows for fast linear interpolation in this grid.

    `Grid` itself is the base class for two other more specific base classes implemented in
    **isochrones**, each of which is subclassed for specific cases: `StellarModelGrid`
    and `BolometricCorrectionGrid`.

    Arbitrary keywords may be passed, and will be stored in the `.kwargs` attribute.

    The key attributes are

    * `.df`: the grid data as a single dataframe, and
    * `.interp`: `DFInterpolator` object of the grid data.

    To subclass this, please see `StellarModelGrid` and `BolometricCorrectionGrid`
    as examples for the various methods that need to be implemented.

    """

    index_cols = None
    is_full = False
    bounds = tuple()

    def __init__(self, **kwargs):

        if hasattr(self, "default_kwargs"):
            self.kwargs = self.default_kwargs.copy()
        else:
            self.kwargs = {}
        self.kwargs.update(kwargs)

        self._df = None
        self._df_orig = None
        self._interp = None
        self._interp_orig = None
        self._limits = dict(self.bounds)

    def get_limits(self, prop):
        if prop not in self._limits:
            self._limits[prop] = self.df[prop].min(), self.df[prop].max()
        return self._limits[prop]

    @property
    def datadir(self):
        raise NotImplementedError

    def get_hdf_filename(self, **kwargs):
        raise NotImplementedError

    @property
    def hdf_filename(self):
        return self.get_hdf_filename()

    def get_tarball_url(self, **kwargs):
        raise NotImplementedError

    def get_tarball_file(self, **kwargs):
        raise NotImplementedError

    def download_tarball(self, clobber=False, **kwargs):
        if not os.path.exists(self.datadir):
            os.makedirs(self.datadir, exist_ok=True)
        tarball = self.get_tarball_file(**kwargs)

        if os.path.exists(tarball) and not clobber:
            if is_valid_archive(tarball):
                getLogger().info("{} exists; not downloading.".format(tarball))
                return tarball
            # A stale URL (e.g. the pre-2024 waps.cfa.harvard.edu paths) used to
            # leave an HTML error page cached here.  Throw it away and retry.
            getLogger().warning(
                "{} is not a valid tarball (likely a cached download error); re-downloading.".format(
                    tarball
                )
            )
            os.remove(tarball)

        url = self.get_tarball_url(**kwargs)
        getLogger().info("Downloading {} to {} ...".format(url, tarball))
        download_file(url, tarball, clobber=True)

        if not is_valid_archive(tarball):
            os.remove(tarball)
            raise RuntimeError(
                "Download from {} did not produce a valid tarball. "
                "The MIST grids are served from https://mist.science -- check that "
                "this URL is still correct.".format(url)
            )
        return tarball

    def extract_tarball(self, _attempt=0, **kwargs):
        tarball = self.get_tarball_file(**kwargs)
        if not os.path.exists(tarball) or not is_valid_archive(tarball):
            self.download_tarball(**kwargs)

        try:
            with tarfile.open(tarball) as tar:
                getLogger().info("Extracting {}...".format(tarball))
                _safe_extractall(tar, self.datadir)
        except (EOFError, tarfile.TarError, lzma.LZMAError) as e:
            if _attempt >= 1:
                raise RuntimeError(
                    "{} is still unreadable after re-downloading ({}).".format(tarball, e)
                ) from e
            getLogger().error("{} corrupted ({}); deleting and re-downloading.".format(tarball, e))
            os.remove(tarball)
            self.extract_tarball(_attempt=_attempt + 1, **kwargs)

    def read_hdf(self, orig=False):
        h5file = self.hdf_filename
        try:
            path = "orig" if orig else "df"
            df = pd.read_hdf(h5file, path)
        except (FileNotFoundError, KeyError):
            df = self.write_hdf(orig=orig)
        return df

    def write_hdf(self, orig=False):
        df = self.get_df(orig=orig)
        h5file = self.hdf_filename
        path = "orig" if orig else "df"
        df.to_hdf(h5file, key=path)
        getLogger().info("{} written to {}.".format(path, h5file))
        return df

    @property
    def df(self):
        if self._df is None:
            self._df = self.get_df()
        return self._df

    @property
    def df_orig(self):
        if self._df_orig is None:
            self._df_orig = self.read_hdf(orig=True)
        return self._df_orig

    @property
    def interp(self):
        if self._interp is None:
            filename = getattr(self, "interp_grid_npz_filename", None)
            self._interp = DFInterpolator(self.df, filename=filename, is_full=self.is_full)
        return self._interp

    @property
    def interp_orig(self):
        if self._interp_orig is None:
            filename = getattr(self, "interp_grid_orig_npz_filename", None)
            self._interp_orig = DFInterpolator(self.df_orig, filename=filename, is_full=self.is_full)
        return self._interp_orig

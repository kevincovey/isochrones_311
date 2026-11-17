import os
import lzma
import tarfile

import requests

import numpy as np
import numba as nb
from math import log10

from .logger import getLogger

#: Chunk size (bytes) used when streaming downloads to disk.
DOWNLOAD_CHUNK_SIZE = 1 << 20  # 1 MiB

#: Default (connect, read) timeout in seconds for grid downloads.
DOWNLOAD_TIMEOUT = (30, 300)


def band_pairs(bands):
    return [(bands[i], bands[-1]) for i in range(len(bands) - 1)]


def is_valid_archive(path):
    """True if ``path`` looks like a readable (xz-compressed) tar archive.

    The MIST grids are served as ``.txz`` files.  When a URL has moved, the web
    server happily returns a small HTML error page with a 200 or 404 status,
    which used to get cached on disk under the tarball's name and then fail
    later with a confusing ``tarfile.ReadError``.  Checking the magic number and
    asking ``tarfile`` to open the file catches that immediately.
    """
    try:
        if os.path.getsize(path) < 128:
            return False
        with open(path, "rb") as fin:
            magic = fin.read(6)
        # xz magic number; MIST tarballs are always .txz
        if magic[:6] != b"\xfd7zXZ\x00":
            return False
        with tarfile.open(path) as tar:
            tar.next()
    except (OSError, tarfile.TarError, lzma.LZMAError, EOFError):
        return False
    return True


def download_file(url, path=None, clobber=False, timeout=DOWNLOAD_TIMEOUT):
    """Stream ``url`` to a local file, raising on any HTTP error.

    The download goes to a ``.part`` file that is only moved into place once the
    whole body has arrived, so an interrupted or failed download never leaves a
    truncated file behind that would be mistaken for a valid cached grid.

    Parameters
    ----------
    url : str
        Remote URL to fetch.
    path : str, optional
        Local path to download to.  Defaults to the URL's basename in the
        current working directory.
    clobber : bool
        If False (default) and ``path`` already exists, do nothing.
    timeout : float or (float, float)
        Passed through to :func:`requests.get`.
    """
    if path is None:
        local_filename = os.path.join(os.getcwd(), url.split("/")[-1])
    else:
        local_filename = path

    if os.path.exists(local_filename) and not clobber:
        getLogger().info("{} exists; not downloading.".format(local_filename))
        return local_filename

    directory = os.path.dirname(os.path.abspath(local_filename))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    partial_filename = local_filename + ".part"
    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            # Without this, an HTML "404 Not Found" page gets written to disk
            # and cached under the tarball's name.
            r.raise_for_status()
            with open(partial_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
        os.replace(partial_filename, local_filename)
    except BaseException:
        if os.path.exists(partial_filename):
            try:
                os.remove(partial_filename)
            except OSError:
                pass
        raise

    return local_filename


def addmags(*mags):
    """
    mags is either list of magnitudes or list of (mag, err) pairs
    """
    tot = 0
    uncs = []
    for mag in mags:
        try:
            tot += 10 ** (-0.4 * mag)
        except:
            m, dm = mag
            f = 10 ** (-0.4 * m)
            tot += f
            unc = f * (1 - 10 ** (-0.4 * dm))
            uncs.append(unc)

    totmag = -2.5 * np.log10(tot)
    if len(uncs) > 0:
        f_unc = np.sqrt(np.array([u ** 2 for u in uncs]).sum())
        return totmag, -2.5 * np.log10(1 - f_unc / tot)
    else:
        return totmag


@nb.jit(nopython=True)
def fast_addmags(mags):
    """
    mags is list of magnitudes
    """
    tot = 0
    for mag in mags:
        tot += 10 ** (-0.4 * mag)
    return -2.5 * log10(tot)


def distance(pos0, pos1):
    """distance between two positions defined by (separation, PA)
    """
    r0, pa0 = pos0
    # getLogger().debug('r0={}, pa0={} (from {})'.format(r0, pa0, self))
    ra0 = r0 * np.sin(pa0 * np.pi / 180)
    dec0 = r0 * np.cos(pa0 * np.pi / 180)

    r1, pa1 = pos1
    # getLogger().debug('r1={}, pa1={} (from {})'.format(r0, pa0, other))
    ra1 = r1 * np.sin(pa1 * np.pi / 180)
    dec1 = r1 * np.cos(pa1 * np.pi / 180)

    dra = ra1 - ra0
    ddec = dec1 - dec0
    return np.sqrt(dra ** 2 + ddec ** 2)


@nb.jit(nopython=True)
def trapz(y, x):
    n = len(y)
    tot = 0

    for i in range(n - 1):
        i2 = i + 1
        tot = tot + 0.5 * (y[i] + y[i2]) * (x[i2] - x[i])

    return tot


@nb.jit(nopython=True)
def polyval(p, x):
    N = len(p)
    result = 0
    for i in range(N):
        result += p[i] * x ** (N - 1 - i)
    return result

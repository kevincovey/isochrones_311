# Installing `isochrones_311` alongside StarStream (and MIST v2.5)

A verified, copy-paste sequence for building a clean Python 3.11 conda
environment that runs:

* **[isochrones_311](https://github.com/kevincovey/isochrones_311)** — this fork, updated for
  Python 3.11 / numpy 2.x / pandas 3.x, with MIST downloads pointed at
  `https://mist.science`
* **[StarStream](https://github.com/ybillchen/StarStream)** — stellar-stream detection
  (needs `agama`)
* optionally **[isochrones-v2p5](https://github.com/DavidMoiseNataf/isochrones-v2p5)** — MIST v2.5
  and BaSTI extensions with [α/Fe] as a parameter

Tested on macOS 15 (Apple silicon) with conda 26.1.1: Python 3.11.18,
numpy 2.4.6, pandas 3.1.1, scipy 1.17.1, numba 0.68.1, astropy 8.0.2.

---

## 0. Prerequisites

* **conda** (Miniforge, Miniconda or Anaconda).
* **A C++ compiler**, only for `agama`. macOS: `xcode-select --install`.
  Linux: `gcc`/`g++` from your distribution.

Everything else is installed below.

---

## 1. Create the environment

Installs the full scientific stack plus `gsl` and `eigen`, which `agama`
compiles against. All from conda-forge, so the binaries are mutually
consistent.

```bash
conda create -y -n isochrones311 -c conda-forge python=3.11 numpy scipy pandas numba pytables astropy matplotlib emcee corner astroquery configobj tqdm requests asciitree pip setuptools wheel pytest flaky gsl eigen
```

```bash
conda activate isochrones311
```

> `setuptools` and `wheel` are needed explicitly because `agama` is built
> with `--no-build-isolation` in the next step.

---

## 2. Install `agama` (StarStream's compiled dependency)

`agama` has no conda-forge package and no wheels — it compiles from source,
and its installer asks interactive questions that fail under `pip`. The flags
below are all required:

* `--no-build-isolation` — so the build can see the numpy already installed
* `--config-settings="--build-option=--yes"` — agama's own flag for answering
  its prompts automatically
* `CPATH` / `LIBRARY_PATH` — so it finds the conda `gsl` and `eigen` headers
* `DYLD_FALLBACK_LIBRARY_PATH` — so agama's *configure-time test programs* can
  load `libgsl` at runtime; without it the build reports
  "GSL library (required) is not found" even though GSL is installed

**macOS:**

```bash
CPATH="$CONDA_PREFIX/include" LIBRARY_PATH="$CONDA_PREFIX/lib" DYLD_FALLBACK_LIBRARY_PATH="$CONDA_PREFIX/lib" pip install --no-build-isolation --config-settings="--build-option=--yes" agama
```

**Linux** (same, with `LD_LIBRARY_PATH` instead):

```bash
CPATH="$CONDA_PREFIX/include" LIBRARY_PATH="$CONDA_PREFIX/lib" LD_LIBRARY_PATH="$CONDA_PREFIX/lib" pip install --no-build-isolation --config-settings="--build-option=--yes" agama
```

This takes a few minutes. Check it:

```bash
python -c "import agama; print('agama', agama.__version__)"
```

---

## 3. Install StarStream

> **Do not use `pip install git+https://github.com/ybillchen/StarStream.git`.**
> Upstream's `setup.py` declares
> `packages = find_packages(where="StarStream")`, which searches *inside* the
> package directory and therefore finds nothing. pip reports success, but the
> wheel contains only metadata — no code — and `import StarStream` then fails
> with `ModuleNotFoundError`. Clone and fix the one line first:

Clone into `StarStream-src`, **not** `StarStream`: a directory named
`StarStream` next to where you run python shadows the installed package as an
empty namespace package, and imports then fail in confusing ways.

```bash
git clone https://github.com/ybillchen/StarStream.git StarStream-src
```

```bash
cd StarStream-src && sed -i.bak 's|packages = find_packages(where="StarStream")|packages = find_packages(include=["StarStream", "StarStream.*"])|' setup.py && cd ..
```

```bash
pip install -e ./StarStream-src
```

```bash
python -c "import StarStream; print('StarStream', StarStream.__version__, 'OK')"
```

If that prints a version, the fix took. If it raises `ModuleNotFoundError` or
`AttributeError: ... has no attribute '__version__'`, check that
`StarStream-src/StarStream.egg-info/top_level.txt` contains `StarStream`
rather than being empty, and that you are not sitting in a directory that
contains a folder called `StarStream`.

---

## 4. Install this `isochrones` fork

```bash
pip install "git+https://github.com/kevincovey/isochrones_311.git"
```

```bash
python -c "import isochrones; print('isochrones', isochrones.__version__)"
```

To work on the code instead, clone and install editable:

```bash
git clone https://github.com/kevincovey/isochrones_311.git
```

```bash
pip install -e ./isochrones_311
```

> Do not `pip install isochrones` from PyPI into this environment. The
> released 2.1 pins `numpy<2` and `pandas<2` and will not run here.

---

## 5. Choose where model grids live (optional)

Grids are large (a few GB for MIST v1.2; ~7 GB more for v2.5 isochrones).
They default to `~/.isochrones`; point `$ISOCHRONES` somewhere else if you
want them on another disk. Put this in your shell profile so it is always set.

```bash
export ISOCHRONES=/path/to/big/disk/.isochrones
```

---

## 6. Verify

The first call downloads the MIST v1.2 isochrone grid (~660 MB) and the
bolometric-correction tables, then builds an HDF5 + `.npz` cache. Measured
from an empty data directory: **about 2 minutes**, and ~4.5 GB on disk.
Later calls take seconds.

```bash
python -c "
from isochrones.mist import MIST_Isochrone
mist = MIST_Isochrone()
iso = mist.isochrone(age=10.0, feh=-1.0)
print('rows:', len(iso))
print('G range: %.2f .. %.2f' % (iso.G_mag.min(), iso.G_mag.max()))
"
```

The tests are not shipped in a usable form by the wheel, so run them from a
clone. Expect **26 passed, 1 skipped** (the skip is a deliberately disabled
Gaia-query test; `test_AV` may add a second skip if NED is throttling).

```bash
git clone https://github.com/kevincovey/isochrones_311.git /tmp/iso311-tests && pytest /tmp/iso311-tests/isochrones/tests -q
```

---

## 7. Optional: MIST v2.5 and BaSTI (`isochrones-v2p5`)

These extensions are *additive*: they are copied in beside the stock modules
and overwrite nothing.

```bash
git clone https://github.com/DavidMoiseNataf/isochrones-v2p5.git
```

```bash
SP=$(python -c "import isochrones, os; print(os.path.dirname(isochrones.__file__))") && cp isochrones-v2p5/mist/*_v2p5.py "$SP/mist/" && cp -r isochrones-v2p5/basti "$SP/basti"
```

Download MIST v2.5 data — bolometric corrections for the systems you need,
plus the isochrone grid (`full_isos`, ~7 GB):

```bash
python isochrones-v2p5/download_mist_v25.py --what bc --bc-systems UBVRIplus
```

```bash
python isochrones-v2p5/download_mist_v25.py --what full_isos
```

Then:

```bash
python -c "
from isochrones.mist.isochrone_v2p5 import get_ichrone_v2p5_iso
ic = get_ichrone_v2p5_iso(bands=['G','BP','RP'], afe=0.0)
iso = ic.isochrone(10.0, -1.0)
print('MIST v2.5 rows:', len(iso))
"
```

Add `--bc-systems ALL` for every photometric system, and
`python isochrones-v2p5/download_mist_v25.py --what tracks` for the EEP tracks
(very large; only needed for the evolution-track interpolator).
BaSTI needs its own download — see `isochrones-v2p5/readme_basti.md`.

Note that `isochrones-v2p5` is installed by copying files into the installed
package, so **re-run the copy step in step 7 after upgrading `isochrones`**.

---

## 8. Optional: MultiNest

`StarModel.fit()` uses MultiNest when available and emcee otherwise; emcee
works out of the box, so this is only needed if you want nested sampling.

```bash
conda install -y -c conda-forge multinest pymultinest
```

---

## Notes and gotchas

* **MIST moved.** Grids now come from `https://mist.science`; the old
  `waps.cfa.harvard.edu/MIST` host redirects for data tarballs but the
  bolometric-correction paths changed, so the pre-2024 BC URLs 404. This fork
  uses the current paths and validates every download, so a failed fetch
  raises immediately instead of caching an HTML error page as a `.txz`.
  Override the host with `$MIST_URL_BASE` if you need a mirror.
* **If an older install left a corrupt tarball** in `$ISOCHRONES`, this fork
  detects it and re-downloads automatically — no manual cleanup needed.
* **`agama` is the only hard part.** It is a StarStream dependency, unrelated
  to isochrones. If the build fails, read the error: it usually names the
  missing library, and `gsl`/`eigen` from conda-forge (step 1) covers the
  common cases.
* **The two StarStream gotchas are both upstream**, not in this fork: the
  `setup.py` packaging bug in step 3, and `agama` needing conda's GSL plus the
  flags in step 2. `import StarStream` pulls in `agama` via `spray.py`, so
  agama must be working before StarStream will import at all.
* **MIST v2.5 bolometric corrections span [Fe/H] = −3.0 … +0.5**, while the
  v2.5 model grid goes down to −4.0. Queries below −3.0 fall off the BC grid
  and return NaN magnitudes.
* **Always fetch v2.5 data with `download_mist_v25.py`**, never by letting
  `isochrones` auto-download it. The v2.5 EEP tracks live under
  `data/tarballs_v2.5/eeps/` with integer-coded names
  (`..._feh_m100_afe_p0_...`), whereas `MISTEvolutionTrackGridV2p5` inherits
  the v1.2-style URL (`..._feh_m1.00_afe_p0.0_...`), which 404s. The
  downloader knows the real paths and rewrites the extracted directories into
  the v1.2-style layout the grid classes expect. If an auto-download is ever
  triggered, this fork raises a clear error rather than caching the 404 page.
* **Rebuilding v2.5 caches.** If you edit `models_v2p5.py`, delete all three
  caches (`mist_v2.5_*.h5`, `full_grid_v2.5_*.npz`, `dm_deep_v2.5_*.h5`) —
  see the header of that file.

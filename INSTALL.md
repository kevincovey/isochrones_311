# Installing `isochrones_311` alongside StarStream (and MIST v2.5)

A verified, copy-paste sequence for building a clean Python 3.11 conda
environment that runs:

* **[isochrones_311](https://github.com/kevincovey/isochrones_311)** — this fork, updated for
  Python 3.11 / numpy 2.x / pandas 3.x, with MIST downloads pointed at
  `https://mist.science`
* **[StarStream-src](https://github.com/kevincovey/StarStream-src)** — our revised fork of
  [StarStream](https://github.com/ybillchen/StarStream) for stellar-stream detection
  (needs `agama`), installed from the **`ngc6569-cluster-analysis`** branch
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

## 3. Install StarStream (our revised fork)

We install from our own fork, **[kevincovey/StarStream-src](https://github.com/kevincovey/StarStream-src)**,
and specifically from the **`ngc6569-cluster-analysis`** branch. Relative to
upstream that branch carries:

* the `setup.py` packaging fix described below, already applied
* memory-chunked KDE evaluation in `StarStream/pdf.py`. Upstream builds one
  `(N_tracer, N_star, 6)` temporary array, which reaches tens of GB for a
  field of ~10^6 stars and kills the process; the chunked version gives
  bitwise-identical results in bounded memory
* a fix for `GaiaBackgroundPDF` accepting `dx`, `dmu`, `dcolor` and `dmag`
  and then silently overwriting all four with hard-coded values
* worked examples on real Gaia DR3 data, including `examples/NGC6569.ipynb`

> **The branch is not optional.** Our fork's `main` branch is still a
> byte-for-byte copy of upstream, packaging bug included. If you clone and
> forget to switch branches, `pip` will report a *successful* install, the
> built wheel will contain metadata but no Python code, and `import
> StarStream` will fail with `ModuleNotFoundError`. Step 3.7 below checks for
> exactly this.

### Why not just `pip install git+...`?

> Upstream's `setup.py` declares `packages = find_packages(where="StarStream")`,
> which searches *inside* the package directory and therefore finds nothing.
> Our branch replaces it with
> `find_packages(include=["StarStream", "StarStream.*"])`, so the one-line
> `sed` patch older versions of this guide told you to apply by hand is no
> longer needed — it is committed. We still clone rather than
> `pip install git+...` because you will want the `examples/` notebooks and
> the ability to edit the code.

### 3.1 Clone the repository

Run this from wherever you keep source code (e.g. `~/python`):

```bash
git clone https://github.com/kevincovey/StarStream-src.git
```

This creates a new folder called `StarStream-src` containing the code. You do
not need a GitHub account and you do not need to be logged in — the
repository is public, so cloning works anonymously.

**Keep the folder name `StarStream-src`.** Do not rename it to
`StarStream`: a folder named exactly `StarStream` sitting next to where you
start python will shadow the installed package as an empty namespace package,
and your imports will fail in confusing ways. Cloning this fork gives you the
right name automatically.

### 3.2 Move into the folder

```bash
cd StarStream-src
```

Every `git` command in the next few steps has to be run from *inside* this
folder. Git works on "the repository I am currently standing in", so running
these from elsewhere will report `not a git repository`.

### 3.3 See which branches exist

A repository can hold several parallel versions of the code, called
*branches*. List them:

```bash
git branch -a
```

You will see something like:

```
* main
  remotes/origin/HEAD -> origin/main
  remotes/origin/main
  remotes/origin/ngc6569-cluster-analysis
```

Reading that output:

* the `*` marks the branch you are **currently on**. A fresh clone always
  starts on the project's default branch, which here is `main`.
* lines beginning `remotes/origin/` are branches that exist **on GitHub**.
  `origin` is git's default nickname for "the place I cloned from".
* `remotes/origin/ngc6569-cluster-analysis` is the one we want. It has no
  local copy yet, which is why it only appears in the `remotes/` list.

### 3.4 Switch to the `ngc6569-cluster-analysis` branch

```bash
git checkout ngc6569-cluster-analysis
```

Expected output — two lines, which may appear in either order:

```
Switched to a new branch 'ngc6569-cluster-analysis'
branch 'ngc6569-cluster-analysis' set up to track 'origin/ngc6569-cluster-analysis'.
```

Git noticed that a branch of this name exists on GitHub, made you a local
copy, and switched your files over to it. The contents of the folder on disk
have now physically changed to the revised version.

`git switch ngc6569-cluster-analysis` does exactly the same thing; `switch` is
the newer spelling and `checkout` is the one you will see in older
documentation. Either is fine.

### 3.5 Confirm you are on the right branch

```bash
git status
```

The first line must read:

```
On branch ngc6569-cluster-analysis
```

And check you have the expected commit:

```bash
git log --oneline -1
```

which should print:

```
3c9ac3b Add NGC 6569 cluster analysis and fix PDF evaluation for large fields
```

> **One-step alternative.** Once you know the branch name, you can clone and
> select it in a single command, skipping 3.2 through 3.5:
>
> ```bash
> git clone --branch ngc6569-cluster-analysis https://github.com/kevincovey/StarStream-src.git
> ```

### 3.6 Install it, editable

Step back out of the repository folder and install:

```bash
cd ..
```

```bash
pip install -e ./StarStream-src
```

Make sure the `isochrones311` environment is still active first — your prompt
should start with `(isochrones311)`. If not, run `conda activate isochrones311`.

The `-e` flag means *editable*: pip does not copy the code into
`site-packages`, it just records a pointer to your `StarStream-src` folder.
Two consequences worth understanding:

* edits you make to the files take effect the next time you start python, with
  no reinstall
* **switching git branches changes the code python imports**, immediately.
  The install follows the folder, not the branch you installed from

### 3.7 Verify

```bash
python -c "import StarStream; print('StarStream', StarStream.__version__, 'OK')"
```

Expected: `StarStream 0.1.0 OK`.

Then confirm you are running the *revised* code rather than an upstream copy,
by checking for a function signature that only exists on our branch:

```bash
python -c "import inspect, StarStream.pdf as P; print('revised build:', 'max_elements' in inspect.signature(P.KernelPDF.eval_pdf).parameters)"
```

Expected: `revised build: True`. If it prints `False`, you have upstream's
code — go back to step 3.4, then rerun `pip install -e ./StarStream-src`.

Finally, run the test suite from inside the clone:

```bash
cd StarStream-src && pytest tests/ -q && cd ..
```

Expect **3 passed**.

### Troubleshooting

If `import StarStream` raises `ModuleNotFoundError`, or
`AttributeError: ... has no attribute '__version__'`:

* check `git status` reports `On branch ngc6569-cluster-analysis` (step 3.5) —
  this is by far the most common cause
* check `StarStream-src/StarStream.egg-info/top_level.txt` contains
  `StarStream` rather than being empty
* check you are not sitting in a directory that contains a folder called
  `StarStream`

### Keeping up to date

```bash
cd StarStream-src && git pull && cd ..
```

`git pull` fetches new commits for the branch you are currently on. Because
the install is editable, there is nothing to reinstall afterwards.

### Running the example notebooks

The notebooks in `examples/` need a Jupyter kernel pointing at this
environment. Register one:

```bash
python -m ipykernel install --user --name isochrones311 --display-name "Python (isochrones311)"
```

Then pick **Python (isochrones311)** from Jupyter's kernel menu. If a notebook
is saved with a different kernel, Jupyter may silently start that other
environment instead — and if the other environment has upstream StarStream
installed, you will be running the unrevised code without noticing.

> **The Gaia data files are not in the repository.** `examples/NGC6569.ipynb`
> reads a 1.1 GB VOTable that exceeds GitHub's 100 MB file limit, so it is
> gitignored. The notebook records the exact ADQL query in a markdown cell —
> run it at the [Gaia archive](https://gea.esac.esa.int/archive/) and save the
> result as `examples/data/NGC6569.vot`.

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

> **`age` is log10(age/yr), not Gyr.** The `10.0` above is log10(10 Gyr), so
> it happens to read like an age in Gyr — a coincidence that is easy to
> copy wrongly. For a 12.8 Gyr cluster pass `np.log10(12.8e9)` = 10.107, not
> `12.8`. An off-grid age returns an **empty** DataFrame rather than raising,
> and the resulting NaNs surface much later as a confusing error from
> whatever consumes the isochrone.

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
* **The StarStream gotchas are upstream's**, not this isochrones fork's. The
  `setup.py` packaging bug is already fixed on our
  `ngc6569-cluster-analysis` branch, but it is still present on upstream
  `main` *and* on our fork's `main` — which is why step 3.4 matters. The
  other is `agama` needing conda's GSL plus the flags in step 2.
  `import StarStream` pulls in `agama` via `spray.py`, so agama must be
  working before StarStream will import at all.
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

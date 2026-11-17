from setuptools import setup, find_packages
import os, sys
import builtins


def readme():
    with open("README.rst") as f:
        return f.read()


# Hackishly inject a constant into builtins to enable importing of the
# package before the library is built.
builtins.__ISOCHRONES_SETUP__ = True
import isochrones

version = isochrones.__version__

# Publish the library to PyPI.
if "publish" in sys.argv[-1]:
    os.system("python -m build && python -m twine upload dist/*")
    sys.exit()

# Push a new tag to GitHub.
if "tag" in sys.argv:
    os.system("git tag -a {0} -m 'version {0}'".format(version))
    os.system("git push --tags")
    sys.exit()

setup(
    name="isochrones",
    version=version,
    description="Defines objects for interpolating stellar model grids.",
    long_description=readme(),
    author="Timothy D. Morton",
    author_email="tim.morton@gmail.com",
    url="https://github.com/timothydmorton/isochrones",
    packages=find_packages(),
    package_data={"isochrones": ["data/*", "tests/star*/*.ini"]},
    scripts=[
        "scripts/starfit",
        "scripts/batch_starfit",
        "scripts/starmodel-select",
        "scripts/starfit-summarize",
        "scripts/isochrones-dartmouth_write_tri",
        "scripts/mist-initialize.py",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
    python_requires=">=3.9",
    # Upper bounds on numpy/pandas were removed: the package is tested against
    # numpy 2.x and pandas 3.x so it can share an environment with packages
    # such as StarStream, which track current numpy/astropy.
    install_requires=[
        "numpy>=1.20",
        "pandas>=1.1",
        "scipy>=1.5",
        "numba>=0.56",
        "astropy>=4.0",
        "tables>=3.6",
        "emcee>=3.0",
        "matplotlib>=3.3",
        "requests>=2.20",
        "corner",
        "astroquery",
        "configobj",
        "asciitree",
        "tqdm",
    ],
    extras_require={
        # MultiNest sampling needs the MultiNest C library installed separately,
        # so it is no longer a hard requirement; emcee sampling works without it.
        "multinest": ["pymultinest"],
        "test": ["pytest", "flaky"],
        "plots": ["holoviews"],
    },
    zip_safe=False,
)

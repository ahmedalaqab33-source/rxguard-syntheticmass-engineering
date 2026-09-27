# Observed environment

Local verification and tests: Windows, Python 3.14.7, DuckDB 1.5.5. Runtime dependency: DuckDB only. Python standard-library modules provide CLI parsing, JSON, hashing, filesystem handling, and unittest.

The original virtual environment also contains Polars and PyArrow, but the released execution path does not import them. They are not added as dependencies. R/RStudio, R packages, notebooks, and standalone SQL files were not identified in the canonical analytical branch; SQL lives inside Python scripts.

`requirements.txt` pins the observed DuckDB version. `pyproject.toml` declares Python >=3.11; the GitHub workflow targets Python 3.11, while the completed local checks use 3.14.7. Cross-platform CI is only verified when an actual successful workflow run is recorded. The original environment is not represented as an independently reconstructed lockfile.

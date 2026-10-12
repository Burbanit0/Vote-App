"""Where the engine runs: CPython on the server, or Pyodide in a browser (EXP-023)."""

import sys

# Pyodide reports itself as "emscripten" and cannot start threads: there, the workers run
# inline and the Monte Carlo runs sequentially.
THREADS = sys.platform != "emscripten"

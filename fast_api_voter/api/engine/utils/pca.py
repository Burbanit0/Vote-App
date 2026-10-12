"""Principal axes whose sign does not depend on the LAPACK build."""

import numpy as np


def orient_axes(axes: np.ndarray) -> np.ndarray:
    """A copy of `axes` (one axis per row) with each row signed so that its largest weight
    is positive.

    numpy's SVD leaves each singular vector's sign to the LAPACK build: the same votes drew
    Polis's map mirrored in CPython and in Pyodide (EXP-023). Weights within 1e-9 of the
    largest count as tied and the first of them decides, because polarized votes and
    two-candidate profiles tie exactly, and a build's last-bit rounding must not pick
    the sign. Only the sign is fixed: when the first two singular values are (nearly)
    equal, a build may still return the plane rotated.
    """
    out = np.array(axes, dtype=float)
    for row in out:
        magnitude = np.abs(row)
        lead = int(np.flatnonzero(magnitude >= magnitude.max() - 1e-9)[0])
        if row[lead] < 0:
            row *= -1.0
    return out

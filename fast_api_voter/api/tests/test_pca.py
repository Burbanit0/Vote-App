"""orient_axes: a principal axis's sign must not depend on the LAPACK build (EXP-023)."""

import numpy as np

from api.engine.utils.pca import orient_axes


def test_an_axis_and_its_mirror_get_the_same_sign():
    axis = np.array([[0.6, -0.8, 0.0], [0.1, 0.2, -0.97]])
    oriented = orient_axes(axis)
    np.testing.assert_array_equal(oriented, orient_axes(-axis))
    assert oriented[0, 1] > 0 and oriented[1, 2] > 0  # each row's largest weight


# A two-candidate profile's first axis is (1/√2, -1/√2): the two weights tie, and two
# builds can round either one a last bit larger. The first tied weight decides, so the
# same axis, returned mirrored and rounded the other way, gets the same sign.
def test_a_tie_one_rounding_apart_does_not_flip_the_sign():
    x = 1 / np.sqrt(2)
    bigger = np.nextafter(x, 1.0)
    one_build = orient_axes(np.array([[x, -bigger]]))
    other_build = orient_axes(np.array([[-bigger, x]]))
    np.testing.assert_allclose(one_build, other_build, atol=1e-15)


def test_a_zero_axis_is_left_as_is():
    np.testing.assert_array_equal(orient_axes(np.zeros((1, 3))), np.zeros((1, 3)))


# Polity's map falls back to principal components when a run's latent structure does
# not reproduce its census: a mirrored SVD must give it the same axes.
def test_polity_pca_fallback_does_not_take_its_axes_signs_from_lapack(monkeypatch):
    from api.domain.polity import run_projection

    year_zero = np.random.default_rng(7).normal(size=(50, 6))
    _, reference = run_projection._pca(year_zero)
    svd = np.linalg.svd

    def mirrored(a, full_matrices=True):
        u, s, vt = svd(a, full_matrices=full_matrices)
        return -u, s, -vt

    monkeypatch.setattr(np.linalg, "svd", mirrored)
    np.testing.assert_allclose(run_projection._pca(year_zero)[1], reference)

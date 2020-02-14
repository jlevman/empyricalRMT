import pytest

from empyricalRMT.rmt.construct import generate_eigs
from empyricalRMT.rmt.eigenvalues import Eigenvalues


@pytest.mark.fast
def test_levelvariance() -> None:
    eigs = Eigenvalues(generate_eigs(2000))
    unfolded = eigs.unfold(smoother="poly", degree=11)
    unfolded.plot_level_variance(min_L=2, max_L=50, c_iters=50000, show_progress=True)

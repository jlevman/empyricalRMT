import numpy as np
import time

from numpy import ndarray
from scipy.integrate import quad
from typing import Any, Union
from typing_extensions import Literal

from empyricalRMT.rmt.unfold import Unfolded
from empyricalRMT.utils import eprint


MatrixKind = Union[
    Literal["goe"], Literal["gue"], Literal["uniform"], Literal["poisson"]
]


def generate_eigs(
    matsize: int,
    mean: float = 0,
    sd: float = 1,
    kind: MatrixKind = "goe",
    log: bool = False,
) -> ndarray:
    """Generate a random matrix as specified by arguments, and compute and return
    the eigenvalues.

    Parameters
    ----------
    matsize: int
        The width (or height) of a the square matrix that will be generated.
    mean: float
        If `kind` is "goe", the mean of the normal distribution used to generate
        the normally-distributed values.
    sd: float
        If `kind` is "goe", the s.d. of the normal distribution used to generate
        the normally-distributed values.
    kind: "goe" | "gue" | "poisson" | "uniform"
        The kind of matrix to generate.
    """
    if kind == "poisson":
        M = _generate_poisson(matsize)
    elif kind == "uniform":
        raise Exception("UNIMPLEMENTED!")
    elif kind == "gue":
        size = [matsize, matsize]
        A = np.random.standard_normal(size) + 1j * np.random.standard_normal(size)
        M = (A + A.conjugate().T) / 2
    elif kind == "goe":
        M = _generate_GOE_matrix(matsize, mean, sd)
    else:
        kinds = ["goe", "gue", "poisson", "uniform"]
        raise ValueError(f"`kind` must be one of {kinds}")

    if log:
        print(f"\n{time.strftime('%H:%M:%S (%b%d)')} -- computing eigenvalues...")
    eigs = np.linalg.eigvalsh(M)
    if log:
        print(f"{time.strftime('%H:%M:%S')} -- computed eigenvalues.")
    return eigs


def goe_unfolded(matsize: int) -> Unfolded:
    N = matsize

    def explicit(E: float) -> Any:
        """
        See the section on Asymptotic Level Densities for the closed form
        function below.

        Abul-Magd, A. A., & Abul-Magd, A. Y. (2014). Unfolding of the spectrum
        for chaotic and mixed systems. Physica A: Statistical Mechanics and its
        Applications, 396, 185-194, section A
        """
        if np.abs(E) <= 2 * np.sqrt(N):
            return (
                0.5
                + (E / (4 * N * np.pi)) * np.sqrt(4 * N - E * E)
                + (1 / np.pi) * np.arctan(E / np.sqrt(4 * N - E * E))
            )
        if E < -2 * np.sqrt(N):
            return 0
        if E > 2 * np.sqrt(N):
            return 1

        raise ValueError("Unreachable!")

    N = matsize
    M = _generate_GOE_matrix(N, 0, 1)
    eigs = np.linalg.eigvalsh(M)

    unfolded = np.empty([N])
    for i in range(N):
        # multiply N here to prevent overflow issues
        unfolded[i] = N * explicit(eigs[i])

    return Unfolded(originals=eigs, unfolded=unfolded)


def fast_poisson_eigs(matsize: int = 1000, sub_matsize: int = 100) -> ndarray:
    """Use independence and fact that eigvalsh is bottleneck to more quickly generate
    eigenvalues. E.g. if matsize == 1024, sub_matsize == 100, generate 10 (100x100)
    matrices and one (24x24) matrix, can concatenate the resultant eigenvalues.
    Parameters
    ----------
    matsize: int
        the desired size of the square matrix, or number of eigenvalues
    sub_matsize: int
        the size of the smaller matrices to use to speed eigenvalue calculation
    """
    if matsize < 100:
        return generate_eigs(matsize, kind="goe")
    if sub_matsize >= matsize:
        raise ValueError("Submatrices must be smaller in order to speed calculation.")
    n_submats = int(matsize / sub_matsize)
    last_matsize = matsize % sub_matsize
    eigs_submats = np.empty([n_submats, sub_matsize])
    for i in range(n_submats):
        M = _generate_GOE_matrix(size=sub_matsize)
        sub_eigs = np.linalg.eigvalsh(M)
        eigs_submats[i, :] = sub_eigs
    eigs_remain = np.linalg.eigvalsh(_generate_GOE_matrix(size=last_matsize))
    eigs = list(eigs_submats.flatten()) + list(eigs_remain)
    eigs = np.sort(eigs)
    return eigs


def generate_uniform(
    matsize: int = 1000, lower: float = 0, upper: float = 1
) -> ndarray:
    raise NotImplementedError


def _almost_identity(size: int = 100) -> ndarray:
    E = np.random.standard_normal(size * size).reshape(size, size)
    E = (E + E.T) / np.sqrt(2)
    M = np.ma.identity(size)
    return M + E


def _random_1vector(size: int = 100) -> ndarray:
    vals = np.random.standard_normal([size, 1])
    return vals * vals.T


def _generate_GOE_matrix(
    size: int = 100, mean: float = 0, sd: float = 1, seed: int = None
) -> ndarray:
    if seed is not None:
        np.random.seed(seed)
    if mean != 0 or sd != 1:
        M = np.random.normal(mean, sd, [size, size])
    else:
        M = np.random.standard_normal([size, size])
    return (M + M.T) / np.sqrt(2)


def _generate_poisson(size: int = 100) -> ndarray:
    return np.diag(np.random.standard_normal(size))


def _generate_random_matrix(size: int = 100) -> ndarray:
    norm_means = np.abs(np.random.normal(10.0, 2.0, size=size * size))
    norm_sds = np.abs(np.random.normal(3.0, 0.5, size=size * size))
    # exp_rates = np.abs(np.random.normal(size=size*size))
    M = np.empty([size, size])
    eprint("Initialized matrix distribution data")

    # TODO: generate NaNs and Infs

    it = np.nditer(M, flags=["f_index"], op_flags=["readwrite"])
    while not it.finished:
        i = it.index
        # original formulation
        # it[0] = np.random.normal(norm_means[i], norm_sds[i], 1) +\
        #     np.random.exponential(exp_rates[i], 1)

        # independent random normals
        it[0] = np.random.normal(norm_means[i], norm_sds[i], 1)

        # one random normal
        it[0] = np.random.normal(0, 1, 1)
        it.iternext()
    it.close()
    eprint("Filled matrix")
    return M

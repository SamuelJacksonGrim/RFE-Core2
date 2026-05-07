"""
interference/differential.py

Differential perturbation — controlled noise injection into latent vectors.

Three perturbation modes
------------------------
  gaussian     Isotropic Gaussian noise. Classic ambiguity injection.
  rotational   Rotates the vector by a small random angle in a random plane.
               Preserves magnitude, perturbs direction — semantic drift
               without amplitude collapse.
  directional  Noise projected perpendicular to the vector. Pushes the
               vector off its trajectory without pulling it toward origin.
               Good for generating near-neighbors that are semantically
               adjacent but not identical.

All modes return a unit-normalized vector.
"""

import numpy as np


def inject_ambiguity(
    vec: np.ndarray,
    scale: float = 0.1,
    mode: str = "gaussian",
    rng: np.random.Generator = None,
) -> np.ndarray:
    """
    Inject controlled noise into a vector.

    Parameters
    ----------
    vec : np.ndarray, shape (dim,)
    scale : float
        Noise magnitude. Larger = more perturbation.
    mode : str
        "gaussian"     — isotropic Gaussian noise
        "rotational"   — small-angle rotation in a random plane
        "directional"  — perpendicular projection noise
    rng : np.random.Generator or None
        Seeded RNG for reproducibility. Defaults to a fresh Generator.

    Returns
    -------
    np.ndarray, shape (dim,), L2-normalized
    """
    if rng is None:
        rng = np.random.default_rng()

    if mode == "gaussian":
        return _gaussian(vec, scale, rng)
    if mode == "rotational":
        return _rotational(vec, scale, rng)
    if mode == "directional":
        return _directional(vec, scale, rng)

    raise ValueError(f"Unknown mode: '{mode}'. Use 'gaussian', 'rotational', or 'directional'.")


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------

def _gaussian(vec: np.ndarray, scale: float, rng: np.random.Generator) -> np.ndarray:
    """Isotropic Gaussian noise. Simple, general-purpose."""
    noise = rng.normal(0.0, scale, size=vec.shape).astype(vec.dtype)
    out   = vec + noise
    norm  = np.linalg.norm(out)
    return out / (norm + 1e-8)


def _rotational(vec: np.ndarray, scale: float, rng: np.random.Generator) -> np.ndarray:
    """
    Rotate `vec` by a small angle in a random 2D plane.

    Picks a random unit vector orthogonal to `vec` as the second axis,
    then applies a Givens-style rotation by `scale` radians (approximately).

    Preserves magnitude, perturbs only direction.
    """
    dim   = vec.shape[0]
    v_norm = np.linalg.norm(vec)
    if v_norm < 1e-8:
        return _gaussian(vec, scale, rng)

    unit = vec / v_norm

    # Random vector, orthogonalized against unit via Gram-Schmidt
    rand  = rng.normal(0.0, 1.0, size=dim).astype(vec.dtype)
    rand -= rand.dot(unit) * unit
    rand_norm = np.linalg.norm(rand)
    if rand_norm < 1e-8:
        return _gaussian(vec, scale, rng)
    rand /= rand_norm

    # Rotation in the (unit, rand) plane
    angle = scale  # scale acts as the rotation angle in radians
    rotated = np.cos(angle) * unit + np.sin(angle) * rand

    out = rotated * v_norm
    return out / (np.linalg.norm(out) + 1e-8)


def _directional(vec: np.ndarray, scale: float, rng: np.random.Generator) -> np.ndarray:
    """
    Add noise strictly perpendicular to `vec`.

    Projects a random noise vector onto the null space of `vec`,
    ensuring the perturbation does not amplify or collapse the original
    direction — only shifts it laterally in the embedding space.
    """
    v_norm = np.linalg.norm(vec)
    if v_norm < 1e-8:
        return _gaussian(vec, scale, rng)

    unit  = vec / v_norm
    noise = rng.normal(0.0, scale, size=vec.shape).astype(vec.dtype)

    # Remove component parallel to vec
    noise -= noise.dot(unit) * unit

    out = vec + noise
    return out / (np.linalg.norm(out) + 1e-8)

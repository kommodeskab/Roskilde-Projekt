import numpy as np

def triangulate_positions(D, x1, x2, x3):
    """
    Fast, vectorized triangulation from distances to 3 known devices.
    
    Parameters:
    - D: (N, 3) array of distances from each point to the 3 devices
    - x1, x2, x3: tuples or arrays with (x, y) positions of the 3 devices

    Returns:
    - positions: (N, 2) array of estimated (x, y) positions
    """
    
    # D can contain NaNs. We handle them by substituting them with the largest number in that column
    max_distances = np.nanmax(D, axis=0)
    D = np.where(np.isnan(D), max_distances, D) 
    
    p1 = np.array(x1)
    p2 = np.array(x2)
    p3 = np.array(x3)

    # Differences in coordinates
    ex = p2 - p1  # (2,)
    ey = p3 - p1  # (2,)

    # Coefficient matrix A (2x2)
    A = np.vstack([ex, ey])  # (2, 2)

    # Precompute squared distances
    d1_sq = D[:, 0] ** 2
    d2_sq = D[:, 1] ** 2
    d3_sq = D[:, 2] ** 2

    # Precompute constants
    p1_sq = np.dot(p1, p1)
    p2_sq = np.dot(p2, p2)
    p3_sq = np.dot(p3, p3)

    b1 = 0.5 * (d1_sq - d2_sq + p2_sq - p1_sq)
    b2 = 0.5 * (d1_sq - d3_sq + p3_sq - p1_sq)
    B = np.stack([b1, b2], axis=1)  # (N, 2)

    # Solve for positions
    A_inv = np.linalg.pinv(A)  # (2, 2)
    positions = B @ A_inv.T  # (N, 2)

    return positions
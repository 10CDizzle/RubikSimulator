import numpy as np

def simple_solver(state):
    x, y, z = state.shape
    # Reset to a "solved" state: face colors by layers
    solved = np.zeros((x, y, z), dtype=int)

    # Simple model: each layer along z has the same color
    for i in range(z):
        solved[:, :, i] = i % 6  # Wrap colors around 0-5
    
    return solved

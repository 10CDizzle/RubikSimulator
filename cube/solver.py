import numpy as np

# Attempt to import the kociemba library
try:
    import kociemba
    solver_available = True
except ImportError:
    solver_available = False
    print("-----------------------------------------------------------")
    print("Warning: 'kociemba' library not found.")
    print("Please install it: pip install kociemba")
    print("Falling back to placeholder solver behavior.")
    print("-----------------------------------------------------------")

# Define the mapping from your color indices (0-5) to Kociemba face letters
# Ensure this matches the color assignment in cube.py:
# 0:U (White), 1:D (Yellow), 2:L (Orange), 3:R (Red), 4:F (Green), 5:B (Blue)
COLOR_MAP = {
    0: 'U',
    1: 'D',
    2: 'L',
    3: 'R',
    4: 'F',
    5: 'B'
}

def _convert_state_to_kociemba_string(state):
    """
    Converts the 3D numpy array state representation into the specific
    facelet string format required by the 'kociemba' library.
    Expected format: U1..U9, R1..R9, F1..F9, D1..D9, L1..L9, B1..B9

    Args:
        state: A (3, 3, 3) numpy array representing the cube state.

    Returns:
        A 54-character string representing the cube state for Kociemba.

    Raises:
        ValueError: If the input state is not a 3x3x3 cube.
        KeyError: If a color index in the state is not in COLOR_MAP.
    """
    if state.shape != (3, 3, 3):
        raise ValueError(f"Kociemba solver only supports 3x3x3 cubes. Input shape was {state.shape}")

    n = 2 # Max index for 3x3x3

    # Order: U, R, F, D, L, B (as defined by Kociemba library)
    # The indexing extracts facelets row-by-row for each face based on
    # the numpy array structure and standard cube viewing orientation.
    # U face (Y=n): Top row (z=0), Mid row (z=1), Bot row (z=2)
    u_face = state[:, n, ::-1].flatten() # Read rows from back (z=0) to front (z=2)

    # R face (X=n): Top row (y=n), Mid row (y=1), Bot row (y=0)
    r_face = state[n, ::-1, :].flatten() # Read rows from top (y=n) to bottom (y=0)

    # F face (Z=n): Top row (y=n), Mid row (y=1), Bot row (y=0)
    f_face = state[:, ::-1, n].flatten() # Read rows from top (y=n) to bottom (y=0)

    # D face (Y=0): Top row (z=0), Mid row (z=1), Bot row (z=2)
    d_face = state[:, 0, ::-1].flatten() # Read rows from back (z=0) to front (z=2)

    # L face (X=0): Top row (y=n), Mid row (y=1), Bot row (y=0)
    l_face = state[0, ::-1, :].flatten() # Read rows from top (y=n) to bottom (y=0)

    # B face (Z=0): Top row (y=n), Mid row (y=1), Bot row (y=0)
    b_face = state[:, ::-1, 0].flatten() # Read rows from top (y=n) to bottom (y=0)

    # Combine faces in URFDLB order
    facelet_indices = np.concatenate([u_face, r_face, f_face, d_face, l_face, b_face])

    # Map color indices to face letters
    try:
        kociemba_string = "".join([COLOR_MAP[color_index] for color_index in facelet_indices])
    except KeyError as e:
        raise KeyError(f"Invalid color index {e} found in cube state. Ensure state uses indices {list(COLOR_MAP.keys())}.")

    if len(kociemba_string) != 54:
         raise ValueError(f"Internal error: Generated Kociemba string length is {len(kociemba_string)}, expected 54.")

    return kociemba_string


def calculate_solve_steps(current_state):
    """
    Calculates the sequence of moves required to solve the cube using the
    Kociemba algorithm.

    Args:
        current_state: A NumPy array representing the cube's current color state.
                       Should be shape (3, 3, 3) for Kociemba.

    Returns:
        A list of strings, where each string represents a move in standard
        cube notation (e.g., 'U', "R'", 'F2'). Returns an empty list if
        solving fails or the Kociemba library is unavailable.
    """
    if not solver_available:
        print("Kociemba solver not available. Returning empty solution.")
        # Optionally return a dummy sequence for testing animation:
        # return ['R', 'U', "R'", "U'"]
        return []

    if current_state.shape != (3, 3, 3):
        print(f"Error: Kociemba solver requires a 3x3x3 cube state, got {current_state.shape}.")
        return []

    try:
        print("Converting state to Kociemba string...")
        kociemba_input_string = _convert_state_to_kociemba_string(current_state)
        print(f"Kociemba input: {kociemba_input_string}")

        print("Solving with Kociemba...")
        solution_string = kociemba.solve(kociemba_input_string)
        print(f"Kociemba output: {solution_string}")

        # Kociemba returns a space-separated string of moves
        solution_moves = solution_string.split()
        print(f"Solution steps: {solution_moves}")
        return solution_moves

    except ValueError as e:
        # Catches errors from _convert_state_to_kociemba_string or Kociemba itself (e.g., invalid state)
        print(f"Error during solving process: {e}")
        return []
    except KeyError as e:
        # Catches errors from color mapping
        print(f"Error during state conversion: {e}")
        return []
    except Exception as e:
        # Catch any other unexpected errors from the kociemba library
        print(f"An unexpected error occurred while using the Kociemba solver: {e}")
        # You might want to log the full traceback here for debugging
        # import traceback
        # traceback.print_exc()
        return []

# Note: The old simple_solver function is removed as it's replaced by calculate_solve_steps.

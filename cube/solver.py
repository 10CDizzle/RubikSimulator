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

# In solver.py

# Ensure this map is correct and matches cube.py init:
# 0:U (White, Y=n), 1:D (Yellow, Y=0), 2:L (Orange, X=0),
# 3:R (Red, X=n),   4:F (Green, Z=n),  5:B (Blue, Z=0)
COLOR_MAP = {
    0: 'U', 1: 'D', 2: 'L', 3: 'R', 4: 'F', 5: 'B'
}

def _convert_state_to_kociemba_string(state):
    """
    Converts the 3D numpy array state representation into the specific
    facelet string format required by the 'kociemba' library.
    (Corrected logic based on debug output analysis)
    """
    if state.shape != (3, 3, 3):
        raise ValueError(f"Kociemba solver only supports 3x3x3 cubes. Input shape was {state.shape}")

    n = 2 # Max index for 3x3x3

    # Kociemba order: URFDLB
    # Map Kociemba facelet indices (1-9) directly to state[x, y, z] coordinates.
    # Based on cube.py: X=L/R, Y=D/U, Z=B/F

    try:
        # U Face (Y=n=2): View from top. Rows along Z (0,1,2), Cols along X (0,1,2).
        # Kociemba U1..U9: state[0,n,0], state[1,n,0], state[2,n,0], state[0,n,1]...
        u_facelets = [
            state[0, n, 0], state[1, n, 0], state[2, n, 0], # U1-3 (Back row, L->R)
            state[0, n, 1], state[1, n, 1], state[2, n, 1], # U4-6 (Middle row, L->R)
            state[0, n, 2], state[1, n, 2], state[2, n, 2]  # U7-9 (Front row, L->R)
        ] # This mapping seems logically correct, the error might be elsewhere if this still fails.

        # R Face (X=n=2): View from right. Rows along Y (2,1,0), Cols along Z (0,1,2).
        # Kociemba R1..R9: state[n,2,0], state[n,2,1], state[n,2,2], state[n,1,0]...
        r_facelets = [
            state[n, 2, 0], state[n, 2, 1], state[n, 2, 2], # R1-3 (Top row, B->F)
            state[n, 1, 0], state[n, 1, 1], state[n, 1, 2], # R4-6 (Middle row, B->F)
            state[n, 0, 0], state[n, 0, 1], state[n, 0, 2]  # R7-9 (Bottom row, B->F)
        ] # This mapping also seems logically correct.

        # F Face (Z=n=2): View from front. Rows along Y (2,1,0), Cols along X (0,1,2).
        # Kociemba F1..F9: state[0,2,n], state[1,2,n], state[2,2,n], state[0,1,n]...
        f_facelets = [
            state[0, 2, n], state[1, 2, n], state[2, 2, n], # F1-3 (Top row, L->R)
            state[0, 1, n], state[1, 1, n], state[2, 1, n], # F4-6 (Middle row, L->R)
            state[0, 0, n], state[1, 0, n], state[2, 0, n]  # F7-9 (Bottom row, L->R)
        ] # Correct based on debug output.

        # D Face (Y=0): View from bottom. Rows along Z (2,1,0), Cols along X (0,1,2).
        # Kociemba D1..D9: state[0,0,2], state[1,0,2], state[2,0,2], state[0,0,1]...
        d_facelets = [
            state[0, 0, 2], state[1, 0, 2], state[2, 0, 2], # D1-3 (Front row, L->R)
            state[0, 0, 1], state[1, 0, 1], state[2, 0, 1], # D4-6 (Middle row, L->R)
            state[0, 0, 0], state[1, 0, 0], state[2, 0, 0]  # D7-9 (Back row, L->R)
        ] # This mapping seems logically correct.

        # L Face (X=0): View from left. Rows along Y (2,1,0), Cols along Z (2,1,0).
        # Kociemba L1..L9: state[0,2,2], state[0,2,1], state[0,2,0], state[0,1,2]...
        l_facelets = [
            state[0, 2, 2], state[0, 2, 1], state[0, 2, 0], # L1-3 (Top row, F->B)
            state[0, 1, 2], state[0, 1, 1], state[0, 1, 0], # L4-6 (Middle row, F->B)
            state[0, 0, 2], state[0, 0, 1], state[0, 0, 0]  # L7-9 (Bottom row, F->B)
        ] # This mapping seems logically correct.

        # B Face (Z=0): View from back. Rows along Y (2,1,0), Cols along X (2,1,0).
        # Kociemba B1..B9: state[2,2,0], state[1,2,0], state[0,2,0], state[2,1,0]...
        b_facelets = [
            state[2, 2, 0], state[1, 2, 0], state[0, 2, 0], # B1-3 (Top row, R->L)
            state[2, 1, 0], state[1, 1, 0], state[0, 1, 0], # B4-6 (Middle row, R->L)
            state[2, 0, 0], state[1, 0, 0], state[0, 0, 0]  # B7-9 (Bottom row, R->L)
        ] # Correct based on debug output.

        # --- Re-enable DEBUGGING if needed ---
        print("DEBUG U:", [COLOR_MAP[c] for c in u_facelets])
        print("DEBUG R:", [COLOR_MAP[c] for c in r_facelets])
        print("DEBUG F:", [COLOR_MAP[c] for c in f_facelets])
        print("DEBUG D:", [COLOR_MAP[c] for c in d_facelets])
        print("DEBUG L:", [COLOR_MAP[c] for c in l_facelets])
        print("DEBUG B:", [COLOR_MAP[c] for c in b_facelets])
        # --- End Debugging ---

        # Combine facelets in URFDLB order
        all_facelets = u_facelets + r_facelets + f_facelets + d_facelets + l_facelets + b_facelets

        # Map color indices to face letters
        kociemba_string = "".join([COLOR_MAP[color_index] for color_index in all_facelets])

    except KeyError as e:
        raise KeyError(f"Invalid color index {e} found in cube state. Ensure state uses indices {list(COLOR_MAP.keys())}.")
    except IndexError as e:
        raise IndexError(f"Indexing error during state conversion: {e}. Check state shape and conversion logic.")

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

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

# The global 'n' is no longer needed here as the conversion logic has changed.
# n = 2 # Max index for 3x3x3

def _convert_state_to_kociemba_string(cube_faces: dict[str, np.ndarray]) -> str:
    """
    Converts the cube's face dictionary (from RubiksCube.faces)
    into the facelet string format required by the 'kociemba' library.
    This function is specific to 3x3x3 cubes.

    Args:
        cube_faces: A dictionary where keys are face names ('U', 'R', 'F', 'D', 'L', 'B')
                    and values are 3x3 NumPy arrays of color indices.

    Returns:
        A 54-character string for the Kociemba solver.

    Raises:
        ValueError: If faces are missing, not 3x3, or Kociemba string is not 54 chars.
        KeyError: If an invalid color index is encountered.
        TypeError: If input types are incorrect.
    """
    if not isinstance(cube_faces, dict):
        raise TypeError(f"Expected cube_faces to be a dict, got {type(cube_faces)}")

    # Kociemba order: URFDLB
    kociemba_face_order = ['U', 'R', 'F', 'D', 'L', 'B']
    all_facelets_chars = []

    for face_char in kociemba_face_order:
        if face_char not in cube_faces:
            raise ValueError(f"Missing face '{face_char}' in input for Kociemba conversion.")
        
        face_array = cube_faces[face_char]
        
        if not isinstance(face_array, np.ndarray):
            raise TypeError(f"Face '{face_char}' is not a NumPy array, got {type(face_array)}")
        if face_array.shape != (3, 3):
            raise ValueError(f"Kociemba solver only supports 3x3x3 cubes. Face '{face_char}' had shape {face_array.shape}, expected (3,3).")

        # Flatten the face array (row-major) and map color indices to Kociemba face letters
        for color_index in face_array.flat: # .flat is an iterator
            try:
                all_facelets_chars.append(COLOR_MAP[int(color_index)])
            except KeyError:
                raise KeyError(f"Invalid color index {int(color_index)} (from original value {color_index}) on face '{face_char}'. Valid indices: {list(COLOR_MAP.keys())}.")
            except (ValueError, TypeError) as e: # Handles if color_index cannot be int()
                raise TypeError(f"Color index '{color_index}' on face '{face_char}' could not be converted to int: {e}")
    
    kociemba_string = "".join(all_facelets_chars)

    if len(kociemba_string) != 54:
         # This should ideally not happen if all prior checks pass for a 3x3 cube.
         raise ValueError(f"Internal error: Generated Kociemba string length is {len(kociemba_string)}, expected 54. This indicates an issue with face processing logic.")

    return kociemba_string




def calculate_solve_steps(current_faces_state: dict[str, np.ndarray]):
    """
    Calculates the sequence of moves required to solve the cube using the
    Kociemba algorithm. Only works for 3x3x3 cubes.

    Args:
        current_faces_state: A dictionary where keys are face names ('U', 'D', ...)
                             and values are 3x3 NumPy arrays of color indices.

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

    # Size and shape checks are now handled by _convert_state_to_kociemba_string

    try:
        print("Converting face state to Kociemba string for Kociemba solver...")
        kociemba_input_string = _convert_state_to_kociemba_string(current_faces_state)
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

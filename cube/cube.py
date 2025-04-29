# In c:\Users\Chris\Documents\GitHub\RubikSimulator\cube\cube.py

import numpy as np
# Import solver functions - calculate_solve_steps might need adjustment
# if it relies solely on the string state now.
from .solver import calculate_solve_steps, _convert_state_to_kociemba_string

class RubiksCube:
    """
    Represents a Rubik's Cube of size n x n x n.
    Uses a 3D NumPy array state[x, y, z] where indices represent colors.
    Axes: X (L->R), Y (D->U), Z (B->F)
    Colors: 0:U(Y=n-1), 1:D(Y=0), 2:L(X=0), 3:R(X=n-1), 4:F(Z=n-1), 5:B(Z=0)
    """

    def __init__(self, size=3):
        if not isinstance(size, int) or size < 2:
            raise ValueError("Cube size must be an integer >= 2.")
        self.size = size
        self.n_max = size - 1 # Maximum index

        # Initialize state array (e.g., -1 for interior, 0-5 for surface colors)
        self.state = np.full((size, size, size), -1, dtype=int)

        # --- Initialize Solved State ---
        # Assign face colors ONLY to the surface layers
        self.state[:, self.n_max, :] = 0  # Top face (U): White
        self.state[:, 0, :] = 1           # Bottom face (D): Yellow
        self.state[0, :, :] = 2           # Left face (L): Orange
        self.state[self.n_max, :, :] = 3  # Right face (R): Red
        self.state[:, :, self.n_max] = 4  # Front face (F): Green
        self.state[:, :, 0] = 5           # Back face (B): Blue

        # Correct centers for odd-sized cubes (overwritten by broad assignments)
        if size % 2 != 0:
            center = size // 2
            self.state[center, self.n_max, center] = 0 # U center
            self.state[center, 0, center] = 1           # D center
            self.state[0, center, center] = 2           # L center
            self.state[self.n_max, center, center] = 3  # R center
            self.state[center, center, self.n_max] = 4  # F center
            self.state[center, center, 0] = 5           # B center
        # --- End Solved State Init ---

        self.solution_moves = []

    def apply_move(self, move):
        """
        Applies a single outer-layer move (e.g., 'U', 'R'', 'F2')
        to the cube's state for size n.
        Does not currently support slice or wide moves (M, E, S, Uw, etc.).
        """
        if not move or not isinstance(move, str):
            print("Warning: Invalid move format.")
            return

        face_char = move[0]
        direction = 1 # Clockwise
        num_rotations = 1 # 90 degrees clockwise

        if len(move) > 1:
            if move[1] == "'":
                direction = -1 # Counter-clockwise
                num_rotations = 3 # Equivalent to 3 clockwise 90-degree turns
            elif move[1] == '2':
                direction = 2 # Double turn
                num_rotations = 2 # Equivalent to 2 clockwise 90-degree turns
            # Add support for other modifiers like 'w' or numbers for layers later if needed

        n = self.n_max # Use max index

        # --- Rotate Face Layer ---
        # Determine the slice indices and rotation axis/direction for np.rot90
        if face_char == 'U':   layer_slice, axes_rot = (slice(None), n, slice(None)), (0, 2)
        elif face_char == 'D': layer_slice, axes_rot = (slice(None), 0, slice(None)), (0, 2)
        elif face_char == 'L': layer_slice, axes_rot = (0, slice(None), slice(None)), (1, 2)
        elif face_char == 'R': layer_slice, axes_rot = (n, slice(None), slice(None)), (1, 2)
        elif face_char == 'F': layer_slice, axes_rot = (slice(None), slice(None), n), (0, 1)
        elif face_char == 'B': layer_slice, axes_rot = (slice(None), slice(None), 0), (0, 1)
        else:
            print(f"Warning: Unknown move face '{face_char}'. Ignoring.")
            return

        # Determine k for np.rot90 based on face and direction
        # (This requires careful mapping of axes and desired rotation)
        k = direction
        if face_char in ('U', 'R', 'F'):
             k = -direction # U, R, F need negative k for clockwise visual rotation
        if face_char in ('D', 'L', 'B'):
             k = direction

        # Apply the rotation to the face layer
        original_face = self.state[layer_slice].copy()
        rotated_face = np.rot90(original_face, k=k, axes=axes_rot)
        self.state[layer_slice] = rotated_face

        # --- Rotate Adjacent Side Pieces (Edges/Corners in the slice) ---
        # This requires generalized slicing based on 'n'
        # Apply the cycle swap logic 'num_rotations' times
        temp_state = self.state.copy() # Use a copy to read from for swaps
        for _ in range(num_rotations):
            current_state = temp_state.copy() # State before this specific 90-deg turn
            if face_char == 'U': # Y=n plane rotation (Affects R[?,n,?], F[?,n,n], L[0,n,?], B[?,n,0])
                temp_state[n, n, :] = current_state[:, n, n]     # F top col -> R top row
                temp_state[:, n, n] = current_state[0, n, ::-1] # L top row (rev) -> F top col
                temp_state[0, n, :] = current_state[:, n, 0]     # B top col -> L top row
                temp_state[:, n, 0] = current_state[n, n, ::-1] # Original R top row (rev) -> B top col
            elif face_char == 'D': # Y=0 plane rotation (Affects R[?,0,?], B[?,0,0], L[0,0,?], F[?,0,n])
                temp_state[n, 0, :] = current_state[:, 0, 0][::-1] # B bottom col (rev) -> R bottom row
                temp_state[:, 0, 0] = current_state[0, 0, :]     # L bottom row -> B bottom col
                temp_state[0, 0, :] = current_state[:, 0, n][::-1] # F bottom col (rev) -> L bottom row
                temp_state[:, 0, n] = current_state[n, 0, :]     # Original R bottom row -> F bottom col
            elif face_char == 'L': # X=0 plane rotation (Affects U[0,n,?], B[0,?,0], D[0,0,?], F[0,?,n])
                temp_state[0, :, n] = current_state[0, n, ::-1] # U left edge (rev) -> F left col
                temp_state[0, n, :] = current_state[0, :, 0]     # B left col -> U left edge
                temp_state[0, :, 0] = current_state[0, 0, ::-1] # D left edge (rev) -> B left col
                temp_state[0, 0, :] = current_state[0, :, n]     # Original F left col -> D left edge
            elif face_char == 'R': # X=n plane rotation (Affects U[n,n,?], F[n,?,n], D[n,0,?], B[n,?,0])
                temp_state[n, :, n] = current_state[n, 0, :]     # D right edge -> F right col
                temp_state[n, 0, :] = current_state[n, :, 0][::-1] # B right col (rev) -> D right edge
                temp_state[n, :, 0] = current_state[n, n, :]     # U right edge -> B right col
                temp_state[n, n, :] = current_state[n, :, n][::-1] # Original F right col (rev) -> U right edge
            elif face_char == 'F': # Z=n plane rotation (Affects U[?,n,n], R[n,?,n], D[?,0,n], L[0,?,n])
                temp_state[:, n, n] = current_state[0, ::-1, n] # L front col (rev) -> U bottom edge
                temp_state[0, :, n] = current_state[:, 0, n]     # D top edge -> L front col
                temp_state[:, 0, n] = current_state[n, ::-1, n] # R front col (rev) -> D top edge
                temp_state[n, :, n] = current_state[:, n, n]     # Original U bottom edge -> R front col
            elif face_char == 'B': # Z=0 plane rotation (Affects U[?,n,0], L[0,?,0], D[?,0,0], R[n,?,0])
                temp_state[:, n, 0] = current_state[n, :, 0]     # R back col -> U top edge
                temp_state[n, :, 0] = current_state[:, 0, 0][::-1] # D bottom edge (rev) -> R back col
                temp_state[:, 0, 0] = current_state[0, ::-1, 0] # L back col (rev) -> D bottom edge
                temp_state[0, :, 0] = current_state[:, n, 0]     # Original U top edge -> L back col

        self.state = temp_state # Assign the final state after all rotations

    def scramble(self, num_moves=None):
        """Applies a series of random outer-layer moves."""
        if num_moves is None:
            # Scale scramble length roughly with size (e.g., 3x3=20, 4x4=40, 5x5=60)
             num_moves = self.size * self.size * 2 + 5 # Heuristic

        moves = ['U', 'D', 'L', 'R', 'F', 'B']
        modifiers = ['', "'", '2']
        scramble_sequence = []
        last_move_face = None

        print(f"Scrambling size {self.size} cube with {num_moves} moves...")
        for _ in range(num_moves):
            while True:
                move_face = np.random.choice(moves)
                if move_face != last_move_face: # Avoid R R', R R2 etc.
                    break
            modifier = np.random.choice(modifiers)
            move = move_face + modifier
            self.apply_move(move)
            scramble_sequence.append(move)
            last_move_face = move_face

        print(f"Scrambled with: {' '.join(scramble_sequence)}")
        self.solution_moves = []
        return scramble_sequence

    def get_solve_steps(self):
        """
        Calculates solve steps. Currently only supports 3x3 using Kociemba.
        """
        if self.size == 3:
            print("Attempting Kociemba solve for 3x3...")
            try:
                # Need the conversion function back if using Kociemba
                kociemba_string = _convert_state_to_kociemba_string(self.state.copy())
                print("DEBUG: State string passed to solver:", kociemba_string)
                # Pass the string state directly to the solver function
                self.solution_moves = calculate_solve_steps(kociemba_string) # Assuming solver takes string
            except NameError:
                 print("Error: _convert_state_to_kociemba_string function not found.")
                 self.solution_moves = []
            except Exception as e:
                print(f"Error during 3x3 solving: {e}")
                self.solution_moves = []
        else:
            print(f"Solving not implemented for cube size {self.size}.")
            self.solution_moves = [] # No solver for n!=3 implemented

        return self.solution_moves.copy()

    def is_solved(self):
        """Checks if the cube is in the solved state for size n."""
        n = self.n_max
        try:
            # Check each face: all facelets must match the color of a reference piece on that face
            # For odd cubes, the center is the reference. For even, any piece can be reference.
            ref_u = self.state[n//2, n, n//2] # Reference color for U face
            if not np.all(self.state[:, n, :] == ref_u): return False
            ref_d = self.state[n//2, 0, n//2] # Reference color for D face
            if not np.all(self.state[:, 0, :] == ref_d): return False
            ref_l = self.state[0, n//2, n//2] # Reference color for L face
            if not np.all(self.state[0, :, :] == ref_l): return False
            ref_r = self.state[n, n//2, n//2] # Reference color for R face
            if not np.all(self.state[n, :, :] == ref_r): return False
            ref_f = self.state[n//2, n//2, n] # Reference color for F face
            if not np.all(self.state[:, :, n] == ref_f): return False
            ref_b = self.state[n//2, n//2, 0] # Reference color for B face
            if not np.all(self.state[:, :, 0] == ref_b): return False
        except IndexError:
             print("Error checking solved state: Index out of bounds.")
             return False
        return True

# Example Usage (can be run standalone for testing)
if __name__ == '__main__':

    # --- Test 3x3 ---
    print("--- Testing 3x3 ---")
    my_cube_3x3 = RubiksCube(size=3)
    print("Initial State (Top Face):\n", my_cube_3x3.state[:, my_cube_3x3.n_max, :])
    print("Is solved:", my_cube_3x3.is_solved())

    print("\nApplying move U...")
    my_cube_3x3.apply_move('U')
    print("State after U (Top Face):\n", my_cube_3x3.state[:, my_cube_3x3.n_max, :])
    print("State after U (Front Face):\n", my_cube_3x3.state[:, :, my_cube_3x3.n_max])

    print("\nApplying move R'...")
    my_cube_3x3.apply_move("R'")
    print("State after R' (Right Face):\n", my_cube_3x3.state[my_cube_3x3.n_max, :, :])

    print("\nScrambling 3x3...")
    my_cube_3x3.scramble(5)
    print("Is solved:", my_cube_3x3.is_solved())

    print("\nGetting 3x3 solve steps...")
    steps = my_cube_3x3.get_solve_steps()
    print(f"Calculated steps: {steps}")

    # --- Test 4x4 ---
    print("\n\n--- Testing 4x4 ---")
    my_cube_4x4 = RubiksCube(size=4)
    print("Initial State (Top Face):\n", my_cube_4x4.state[:, my_cube_4x4.n_max, :])
    print("Is solved:", my_cube_4x4.is_solved())

    print("\nApplying move F...")
    my_cube_4x4.apply_move('F')
    print("State after F (Front Face):\n", my_cube_4x4.state[:, :, my_cube_4x4.n_max])
    print("State after F (Top Face):\n", my_cube_4x4.state[:, my_cube_4x4.n_max, :])
    print("Is solved:", my_cube_4x4.is_solved())

    print("\nScrambling 4x4...")
    my_cube_4x4.scramble(5)

    print("\nGetting 4x4 solve steps...")
    steps_4x4 = my_cube_4x4.get_solve_steps() # Should indicate not implemented
    print(f"Calculated steps: {steps_4x4}")

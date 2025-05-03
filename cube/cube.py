# c:\Users\Chris\Documents\GitHub\RubikSimulator\cube\cube.py
import numpy as np
import random
from typing import Dict, List, Tuple, Optional
from collections import Counter # Import Counter

# Import the solver function
from . import solver # Use relative import assuming solver.py is in the same directory

# Consistent color mapping (matches solver.py)
# 0:U (White, Y=n), 1:D (Yellow, Y=0), 2:L (Orange, X=0),
# 3:R (Red, X=n),   4:F (Green, Z=n),  5:B (Blue, Z=0)
# Using descriptive names for clarity
COLOR_MAP_INT_TO_CHAR = {
    0: 'U', 1: 'D', 2: 'L', 3: 'R', 4: 'F', 5: 'B'
}
COLOR_MAP_CHAR_TO_INT = {v: k for k, v in COLOR_MAP_INT_TO_CHAR.items()}

# Standard face names
FACE_NAMES = ['U', 'D', 'L', 'R', 'F', 'B']

class RubiksCube:
    """
    Represents a 3x3x3 Rubik's Cube and handles state manipulation through moves.

    The cube state is stored internally as a dictionary of 6 NumPy arrays,
    each representing the colors of the facelets on one face.

    Provides methods for applying moves, scrambling, resetting, checking if solved,
    retrieving the state in different formats, and getting solve steps.
    """

    def __init__(self, size: int = 3):
        """
        Initializes the Rubik's Cube.

        Args:
            size: The dimension of the cube (e.g., 3 for a 3x3x3).
                  Currently, only size 3 is fully supported due to solver integration.
        """
        if size != 3:
            # While the face-based representation could handle NxN,
            # the solver integration and get_state_for_solver are hardcoded for 3x3.
            raise ValueError("Currently only supports 3x3x3 cubes due to solver compatibility.")
        self.size = size
        self.n = size - 1  # Max index (e.g., 2 for 3x3)
        self.faces: Dict[str, np.ndarray] = self._create_solved_faces()

        # --- Print color counts on initialization ---
        print("--- Initial Cube State Color Counts ---")
        all_colors = []
        for face_array in self.faces.values():
            all_colors.extend(face_array.flatten()) # Add all colors from the face

        color_counts = Counter(all_colors)
        expected_count = size * size # e.g., 9 for a 3x3

        for color_index in range(len(FACE_NAMES)): # Iterate 0 through 5
            count = color_counts.get(color_index, 0)
            color_char = COLOR_MAP_INT_TO_CHAR.get(color_index, '?')
            print(f"Color {color_char} ({color_index}): {count} squares (Expected: {expected_count})")
            if count != expected_count:
                 print(f"  WARNING: Unexpected count for color {color_char}!")
        print("---------------------------------------")
        # --- End Print Section ---


    def _create_solved_faces(self) -> Dict[str, np.ndarray]:
        """Creates the face dictionary representing a solved cube."""
        return {
            face: np.full((self.size, self.size), COLOR_MAP_CHAR_TO_INT[face], dtype=int)
            for face in FACE_NAMES
        }

    def reset(self) -> None:
        """Resets the cube to the solved state."""
        self.faces = self._create_solved_faces()

    def get_state_faces(self) -> Dict[str, np.ndarray]:
        """
        Returns the current state as a dictionary of faces (deep copy).

        Returns:
            A dictionary where keys are face names ('U', 'D', 'L', 'R', 'F', 'B')
            and values are NxN NumPy arrays of color indices.
        """
        return {face: arr.copy() for face, arr in self.faces.items()}

    def get_state_for_solver(self) -> np.ndarray:
        """
        Constructs the 3D numpy array representation from the face data,
        matching the specific format expected by the Kociemba solver's
        _convert_state_to_kociemba_string function in solver.py.

        Returns:
            A 3x3x3 NumPy array representing the cube state for the solver.

        Raises:
            ValueError: If the cube size is not 3x3x3.
        """
        if self.size != 3:
             raise ValueError("Solver state generation only supported for 3x3x3 cubes.")

        state_3d = np.full((self.size, self.size, self.size), -1, dtype=int)
        n = self.n

        # --- Map Facelets ---
        # U Face (Y=n)
        for x in range(self.size):
            for z in range(self.size):
                state_3d[x, n, z] = self.faces['U'][z, x]
        # R Face (X=n)
        for y in range(self.size):
            for z in range(self.size):
                state_3d[n, y, z] = self.faces['R'][n - y, z]
        # F Face (Z=n)
        for x in range(self.size):
            for y in range(self.size):
                state_3d[x, y, n] = self.faces['F'][n - y, x]
        # D Face (Y=0)
        for x in range(self.size):
            for z in range(self.size):
                state_3d[x, 0, z] = self.faces['D'][n - z, x]
        # L Face (X=0)
        for y in range(self.size):
            for z in range(self.size):
                state_3d[0, y, z] = self.faces['L'][n - y, n - z]
        # B Face (Z=0)
        for x in range(self.size):
            for y in range(self.size):
                state_3d[x, y, 0] = self.faces['B'][n - y, n - x]

        if np.any(state_3d == -1):
             print("Warning: Some positions in the solver state array were not assigned.")

        return state_3d

    def apply_move(self, move_str: str) -> None:
        """
        Applies a sequence of moves specified in standard cube notation.

        Args:
            move_str: A string containing space-separated moves (e.g., "R U R' U2 F").

        Note:
            This method updates the internal logical state of the cube *instantly*.
            For visual animation, this should typically be called *after* the animation in the viewer is complete.
        """
        moves = move_str.strip().split()
        for move in moves:
            self._apply_single_move(move)

    def _apply_single_move(self, move: str) -> None:
        """Applies a single move notation (e.g., 'U', "R'", 'F2')."""
        # --- Internal state update ---
        # This function performs the logical manipulation of the face arrays.
        # It does not handle visual animation.
        if not move:
            return

        # --- Parse Move ---
        # Determine face, direction (1=CW, -1=CCW, 2=180), and rotation counts
        face_char = move[0].upper()
        if face_char not in FACE_NAMES:
            raise ValueError(f"Invalid move face: {face_char} in move '{move}'")

        if len(move) == 1:
            direction = 1
        elif len(move) == 2:
            if move[1] == "'":
                direction = -1
            elif move[1] == '2':
                direction = 2
            else:
                raise ValueError(f"Invalid move modifier: {move[1]} in move '{move}'")
        else:
             raise ValueError(f"Invalid move format: {move}")

        # --- Perform Rotation ---
        self._rotate_cube(face_char, direction)

    def _rotate_cube(self, face_char: str, direction: int) -> None:
        """
        Rotates the specified face and updates adjacent facelets.

        Args:
            face_char: The face to rotate ('U', 'D', 'L', 'R', 'F', 'B').
            direction: The direction and amount (1: CW 90, -1: CCW 90, 2: 180).

        This method directly manipulates the `self.faces` numpy arrays.
        """
        if direction == 1:
            rot_count_face = -1 # np.rot90 is CCW
            rot_count_sides = 1 # CW cycle
        elif direction == -1:
            rot_count_face = 1
            rot_count_sides = 3 # 3 CW cycles = 1 CCW cycle
        elif direction == 2:
            rot_count_face = -2
            rot_count_sides = 2
        else:
            raise ValueError(f"Internal error: Invalid direction {direction}")

        # 1. Rotate the face itself
        self.faces[face_char] = np.rot90(self.faces[face_char], k=rot_count_face)

        # 2. Cycle the adjacent side facelets
        n = self.n
        for _ in range(rot_count_sides): # Apply CW cycle 'rot_count_sides' times
            if face_char == 'U': # CW Cycle: F[0,:] -> R[0,:] -> B[0,:] -> L[0,:] -> F[0,:]
                temp = self.faces['F'][0, :].copy()
                self.faces['F'][0, :] = self.faces['L'][0, :]
                self.faces['L'][0, :] = self.faces['B'][0, :]
                self.faces['B'][0, :] = self.faces['R'][0, :]
                self.faces['R'][0, :] = temp
            elif face_char == 'D': # CW Cycle: F[n,:] -> L[n,:] -> B[n,:] -> R[n,:] -> F[n,:]
                temp = self.faces['F'][n, :].copy()
                self.faces['F'][n, :] = self.faces['R'][n, :]
                self.faces['R'][n, :] = self.faces['B'][n, :]
                self.faces['B'][n, :] = self.faces['L'][n, :]
                self.faces['L'][n, :] = temp
            elif face_char == 'L': # CW Cycle: U[:,0] -> B[::-1,n] -> D[:,0] -> F[:,0] -> U[:,0]
                # U left col -> F left col -> D left col -> B left col (reversed) -> U left col
                temp = self.faces['U'][:, 0].copy()
                self.faces['U'][:, 0] = self.faces['F'][:, 0]
                self.faces['F'][:, 0] = self.faces['D'][:, 0]
                # B face: [n-y, n-x]. Col n means n-x=n -> x=0 (Left col relative to B view)
                self.faces['D'][:, 0] = self.faces['B'][::-1, n]
                self.faces['B'][::-1, n] = temp
            elif face_char == 'R': # CW Cycle: U[:,n] -> F[:,n] -> D[:,n] -> B[::-1,0] -> U[:,n]
                # U right col -> B right col (reversed) -> D right col -> F right col -> U right col
                temp = self.faces['U'][:, n].copy()
                # B face: [n-y, n-x]. Col 0 means n-x=0 -> x=n (Right col relative to B view)
                self.faces['U'][:, n] = self.faces['B'][::-1, 0]
                self.faces['B'][::-1, 0] = self.faces['D'][:, n]
                self.faces['D'][:, n] = self.faces['F'][:, n]
                self.faces['F'][:, n] = temp
            elif face_char == 'F': # CW Cycle: U[n,:] -> R[:,0] -> D[0,::-1] -> L[::-1,0] -> U[n,:]
                # U bottom row -> R back col -> D front row (reversed) -> L front col (reversed) -> U bottom row
                temp = self.faces['U'][n, :].copy()
                # L face: [n-y, n-z]. Col 0 means n-z=0 -> z=n (Front col relative to L view)
                self.faces['U'][n, :] = self.faces['L'][::-1, 0]
                # D face: [n-z, x]. Row 0 means n-z=0 -> z=n (Front row relative to D view)
                self.faces['L'][:, 0] = self.faces['D'][0, ::-1]
                # R face: [n-y, z]. Col 0 means z=0 (Back col relative to R view)
                self.faces['D'][0, :] = self.faces['R'][:, 0]
                self.faces['R'][:, 0] = temp
            elif face_char == 'B': # CW Cycle: U[0,:] -> L[::-1,n] -> D[n,:] -> R[:,n] -> U[0,:]
                # U top row -> R front col -> D back row (reversed) -> L back col (reversed) -> U top row
                temp = self.faces['U'][0, :].copy()
                # R face: [n-y, z]. Col n means z=n (Front col relative to R view)
                self.faces['U'][0, :] = self.faces['R'][:, n]
                # D face: [n-z, x]. Row n means n-z=n -> z=0 (Back row relative to D view)
                self.faces['R'][:, n] = self.faces['D'][n, ::-1]
                # L face: [n-y, n-z]. Col n means n-z=n -> z=0 (Back col relative to L view)
                self.faces['D'][n, :] = self.faces['L'][::-1, n]
                self.faces['L'][:, n] = temp[::-1] # Reverse U top row going to L back col


    def scramble(self, num_moves: int = 25, seed: Optional[int] = None) -> str:
        """
        Applies a random sequence of moves to scramble the cube.

        Args:
            num_moves: The number of random moves to apply.
            seed: An optional random seed for reproducible scrambles.

        Returns:
            The scramble sequence string that was applied.
        """
        if seed is not None:
            random.seed(seed)

        modifiers = ['', "'", '2']
        scramble_sequence = []
        last_move_face = None

        for _ in range(num_moves):
            possible_faces = [f for f in FACE_NAMES if f != last_move_face]
            move_face = random.choice(possible_faces)
            modifier = random.choice(modifiers)
            scramble_sequence.append(move_face + modifier)
            last_move_face = move_face

        scramble_str = " ".join(scramble_sequence)
        self.apply_move(scramble_str)
        return scramble_str

    def is_solved(self) -> bool:
        """Checks if the cube is currently in the solved state."""
        solved_faces = self._create_solved_faces()
        for face in FACE_NAMES:
            if not np.array_equal(self.faces[face], solved_faces[face]):
                return False
        return True

    # --- Added Method ---
    def get_solve_steps(self) -> List[str]:
        """
        Calculates the solving steps for the current cube state using the integrated solver.

        Returns:
            A list of move strings (e.g., ['R', 'U', "R'"]) representing the
            solution, or an empty list if the solver is unavailable or fails.
        """
        print("Requesting solve steps...")
        try:
            # Get the state in the format the solver expects
            solver_state = self.get_state_for_solver()
            # Call the solver function
            solution = solver.calculate_solve_steps(solver_state)
            return solution
        except Exception as e:
            # Catch potential errors during state generation or solving
            print(f"Error getting solve steps: {e}")
            return []
    # --- End Added Method ---

    def __str__(self) -> str:
        """Provides a simple text representation of the cube's faces."""
        output = []
        indent = " " * (self.size * 2 + 1)

        def format_face(face_char):
            arr = self.faces[face_char]
            lines = []
            for row in arr:
                lines.append(" ".join(COLOR_MAP_INT_TO_CHAR.get(i, '?') for i in row))
            return lines

        u_lines = format_face('U')
        for line in u_lines: output.append(indent + line)
        output.append("")

        l_lines = format_face('L')
        f_lines = format_face('F')
        r_lines = format_face('R')
        b_lines = format_face('B')
        for i in range(self.size):
            output.append(f"{l_lines[i]}  {f_lines[i]}  {r_lines[i]}  {b_lines[i]}")
        output.append("")

        d_lines = format_face('D')
        for line in d_lines: output.append(indent + line)

        return "\n".join(output)

    def __repr__(self) -> str:
        """Representation of the object."""
        return f"RubiksCube(size={self.size}, state_hash={hash(self.faces_to_string())})"

    def faces_to_string(self) -> str:
        """Converts the face state to a single string (useful for hashing/comparison)."""
        return "".join(self.faces[face].tobytes().hex() for face in FACE_NAMES)

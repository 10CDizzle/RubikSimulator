import numpy as np
# Assuming simple_solver (or another solver) can return a list of moves
# from cube.solver import simple_solver # Keep this if your solver is here
from .solver import calculate_solve_steps # Placeholder for a function that returns move list

class RubiksCube:
    def __init__(self, size=3):
        # Standard cube is 3x3x3
        self.size = size
        self.x, self.y, self.z = size, size, size # Keep for compatibility if needed elsewhere

        # Initialize solved state (example: U=0(W), D=1(Y), L=2(O), R=3(R), F=4(G), B=5(B))
        # This setup makes rotations easier to visualize initially
        self.state = np.zeros((size, size, size), dtype=int)
        # Assign colors based on a solved state convention
        # Top face (Y=size-1): White (0)
        self.state[:, size-1, :] = 0
        # Bottom face (Y=0): Yellow (1)
        self.state[:, 0, :] = 1
        # Left face (X=0): Orange (2)
        self.state[0, :, :] = 2
        # Right face (X=size-1): Red (3)
        self.state[size-1, :, :] = 3
        # Front face (Z=size-1): Green (4)
        self.state[:, :, size-1] = 4
        # Back face (Z=0): Blue (5)
        self.state[:, :, 0] = 5

        self.solution_moves = [] # Stores the sequence of moves from a solver

        # You might want to add a scramble method here
        # self.scramble()

    # --- SCRAMBLE METHOD IMPLEMENTATION ---
    def scramble(self, num_moves=20):
        """Applies a series of random moves to scramble the cube."""
        # Ensure size is 3 for standard moves; adjust if supporting NxN scrambling
        if self.size != 3:
            print("Warning: Scramble currently uses standard 3x3 moves.")
            # Potentially add logic here for larger cubes (wide moves, etc.)

        moves = ['U', 'D', 'L', 'R', 'F', 'B']
        modifiers = ['', "'", '2']
        scramble_sequence = []
        last_move_face = None # Optional: Prevent trivial sequences like R R'

        print(f"Scrambling with {num_moves} moves...")
        for _ in range(num_moves):
            while True:
                move_face = np.random.choice(moves)
                # Optional: Avoid immediately undoing the last move (e.g., R R')
                # or repeating the same face (e.g., R R2). More sophisticated
                # scramble generators exist, but this is a simple improvement.
                if move_face != last_move_face:
                    break
            modifier = np.random.choice(modifiers)
            move = move_face + modifier
            self.apply_move(move)
            scramble_sequence.append(move)
            last_move_face = move_face # Store the face used

        print(f"Scrambled with: {' '.join(scramble_sequence)}")
        # Clear any previous solution moves after scrambling
        self.solution_moves = []
        # Return the sequence if needed elsewhere
        return scramble_sequence
    # --- END SCRAMBLE METHOD ---

    def get_solve_steps(self):
        """
        Calculates and returns the steps needed to solve the cube
        from its current state.
        """
        # This should call your actual solver algorithm, which returns a list of moves
        try:
            # Pass the current state to the solver
            # Ensure state is copied if the solver modifies it in-place
            self.solution_moves = calculate_solve_steps(self.state.copy())
        # except NameError: # This shouldn't happen with the import at the top
        #      print("Warning: Solver function 'calculate_solve_steps' not found. Returning empty list.")
        #      self.solution_moves = []
        except Exception as e:
            # Catch errors from the solver itself (e.g., invalid state, Kociemba not found)
            print(f"Error during solving: {e}")
            self.solution_moves = []

        # Return a copy so internal list isn't modified externally
        return self.solution_moves.copy()

    def apply_move(self, move):
        """
        Applies a single move (e.g., 'U', 'R'', 'F2') to the cube's state.
        *** IMPORTANT: This implementation only rotates the face layer. ***
        A full implementation needs to rotate adjacent side pieces as well.
        """
        if not move or self.size != 3: # Basic check, move application needs size awareness
             if self.size != 3:
                 print(f"Warning: apply_move currently only supports 3x3 logic.")
             return

        face = move[0]
        direction = 1 # Default: Clockwise (interpreted by np.rot90 k)
        if len(move) > 1:
            if move[1] == "'":
                direction = -1 # Counter-clockwise
            elif move[1] == '2':
                direction = 2 # Double turn

        # --- Apply rotation based on face ---
        n = self.size - 1 # Max index (which is 2 for size 3)

        # Store the current state to handle side piece rotations
        original_state = self.state.copy()

        # Rotate the face layer itself
        if face == 'U': # Up face (Y = n)
            layer_indices = (slice(None), n, slice(None)) # All X, Y=n, All Z
            k_rot = -direction # Rotation direction for np.rot90
        elif face == 'D': # Down face (Y = 0)
            layer_indices = (slice(None), 0, slice(None)) # All X, Y=0, All Z
            k_rot = direction
        elif face == 'L': # Left face (X = 0)
            layer_indices = (0, slice(None), slice(None)) # X=0, All Y, All Z
            k_rot = direction
        elif face == 'R': # Right face (X = n)
            layer_indices = (n, slice(None), slice(None)) # X=n, All Y, All Z
            k_rot = -direction
        elif face == 'F': # Front face (Z = n)
            layer_indices = (slice(None), slice(None), n) # All X, All Y, Z=n
            k_rot = -direction
        elif face == 'B': # Back face (Z = 0)
            layer_indices = (slice(None), slice(None), 0) # All X, All Y, Z=0
            k_rot = direction
        else:
            print(f"Warning: Unknown move '{move}' ignored.")
            return

        # Apply face rotation
        face_layer = original_state[layer_indices]
        rotated_face_layer = np.rot90(face_layer, k=k_rot)
        self.state[layer_indices] = rotated_face_layer

        # --- Rotate adjacent side pieces ---
        # This requires careful slicing and assignment based on the move
        # Example for 'U' move (rotating the top layer around Y axis):
        # The sides affected are F, R, B, L layers at Y=n
        if face == 'U':
            for _ in range(direction % 4): # Apply rotation 1, 2, or 3 times
                temp_slice = original_state[n, n, :].copy() # Store R face's top row
                self.state[n, n, :] = original_state[:, n, n] # F face's top col -> R face's top row
                self.state[:, n, n] = original_state[0, n, ::-1] # L face's top row (reversed) -> F face's top col
                self.state[0, n, :] = original_state[:, n, 0] # B face's top col -> L face's top row
                self.state[:, n, 0] = temp_slice[::-1] # Original R face's top row (reversed) -> B face's top col
        elif face == 'D':
             for _ in range(direction % 4):
                temp_slice = original_state[n, 0, :].copy() # Store R face's bottom row
                self.state[n, 0, :] = original_state[:, 0, 0][::-1] # B face's bottom col (reversed) -> R face's bottom row
                self.state[:, 0, 0] = original_state[0, 0, :] # L face's bottom row -> B face's bottom col
                self.state[0, 0, :] = original_state[:, 0, n][::-1] # F face's bottom col (reversed) -> L face's bottom row
                self.state[:, 0, n] = temp_slice # Original R face's bottom row -> F face's bottom col
        elif face == 'L':
             for _ in range(direction % 4):
                temp_slice = original_state[0, :, n].copy() # Store F face's left col
                self.state[0, :, n] = original_state[0, n, ::-1] # U face's left edge (reversed) -> F face's left col
                self.state[0, n, :] = original_state[0, :, 0] # B face's left col -> U face's left edge
                self.state[0, :, 0] = original_state[0, 0, ::-1] # D face's left edge (reversed) -> B face's left col
                self.state[0, 0, :] = temp_slice # Original F face's left col -> D face's left edge
        elif face == 'R':
             for _ in range(direction % 4):
                temp_slice = original_state[n, :, n].copy() # Store F face's right col
                self.state[n, :, n] = original_state[n, 0, :] # D face's right edge -> F face's right col
                self.state[n, 0, :] = original_state[n, :, 0][::-1] # B face's right col (reversed) -> D face's right edge
                self.state[n, :, 0] = original_state[n, n, :] # U face's right edge -> B face's right col
                self.state[n, n, :] = temp_slice[::-1] # Original F face's right col (reversed) -> U face's right edge
        elif face == 'F':
             for _ in range(direction % 4):
                temp_slice = original_state[n, :, n].copy() # Store R face's front col
                self.state[n, :, n] = original_state[:, n, n] # U face's bottom edge -> R face's front col
                self.state[:, n, n] = original_state[0, ::-1, n] # L face's front col (reversed) -> U face's bottom edge
                self.state[0, :, n] = original_state[:, 0, n] # D face's top edge -> L face's front col
                self.state[:, 0, n] = temp_slice[::-1] # Original R face's front col (reversed) -> D face's top edge
        elif face == 'B':
             for _ in range(direction % 4):
                temp_slice = original_state[n, :, 0].copy() # Store R face's back col
                self.state[n, :, 0] = original_state[:, 0, 0][::-1] # D face's bottom edge (reversed) -> R face's back col
                self.state[:, 0, 0] = original_state[0, :, 0] # L face's back col -> D face's bottom edge
                self.state[0, :, 0] = original_state[:, n, 0][::-1] # U face's top edge (reversed) -> L face's back col
                self.state[:, n, 0] = temp_slice # Original R face's back col -> U face's top edge


    # Optional: Add a method to check if solved
    def is_solved(self):
        """Checks if the cube is in the solved state."""
        if self.size != 3: # is_solved logic assumes 3x3 structure
            print("Warning: is_solved check currently assumes 3x3.")
            return False # Or implement NxN solve check

        n = self.size - 1
        # Check each face - compare all elements on the face to the center element
        center_u = self.state[1, n, 1] # Assuming center piece exists
        center_d = self.state[1, 0, 1]
        center_l = self.state[0, 1, 1]
        center_r = self.state[n, 1, 1]
        center_f = self.state[1, 1, n]
        center_b = self.state[1, 1, 0]

        if not np.all(self.state[:, n, :] == center_u): return False # Top
        if not np.all(self.state[:, 0, :] == center_d): return False # Bottom
        if not np.all(self.state[0, :, :] == center_l): return False # Left
        if not np.all(self.state[n, :, :] == center_r): return False # Right
        if not np.all(self.state[:, :, n] == center_f): return False # Front
        if not np.all(self.state[:, :, 0] == center_b): return False # Back
        return True


# Example Usage (can be run standalone for testing)
if __name__ == '__main__':
    # Use the actual solver now if available, otherwise use a dummy for testing apply_move
    try:
        from .solver import calculate_solve_steps as actual_solver
    except ImportError:
        print("Running cube.py standalone: Using dummy solver for tests.")
        def actual_solver(state):
            print("Dummy solver called, returning sample moves.")
            return ['U', 'R', "F'", 'B2', 'L']

    my_cube = RubiksCube(size=3)
    print("Initial State (Example - Top Face Y=2):")
    print(my_cube.state[:, 2, :]) # Print top face

    print("\nApplying move U...")
    my_cube.apply_move('U')
    print("State after U (Top Face Y=2):")
    print(my_cube.state[:, 2, :])
    print("Front face Z=2:")
    print(my_cube.state[:, :, 2])


    print("\nApplying move R'...")
    my_cube.apply_move("R'")
    print("State after R' (Right Face X=2):")
    print(my_cube.state[2, :, :])
    print("Top face Y=2:")
    print(my_cube.state[:, 2, :])


    print("\nApplying move F2...")
    my_cube.apply_move("F2")
    print("State after F2 (Front Face Z=2):")
    print(my_cube.state[:, :, 2])
    print("Top face Y=2:")
    print(my_cube.state[:, 2, :])


    print("\nScrambling cube...")
    my_cube.scramble(5)
    print("State after scramble (Top Face Y=2):")
    print(my_cube.state[:, 2, :])
    print("Is solved:", my_cube.is_solved())

    print("\nGetting solve steps (using actual/dummy solver)...")
    # Use the imported solver
    steps = my_cube.get_solve_steps()
    print(f"Calculated steps: {steps}")

    # Apply the first step from the solution
    if steps:
        print(f"\nApplying first solve step: {steps[0]}")
        my_cube.apply_move(steps[0])
        print("State after first solve step (Top Face Y=2):")
        print(my_cube.state[:, 2, :])

    print("\nTesting solve check on solved cube:")
    solved_cube = RubiksCube(size=3)
    print("Is solved:", solved_cube.is_solved())

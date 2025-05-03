# c:\Users\Chris\Documents\GitHub\RubikSimulator\main.py
from ursina import Ursina, invoke, camera, print_on_screen, held_keys, mouse
import sys, math
import os

# Ensure the parent directory is in the Python path
# to allow imports like 'from cube.cube import RubiksCube'
script_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(script_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import from sibling directories
try:
    from cube.cube import RubiksCube
    from ui.viewer import RubiksCubeViewer
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    print("Please ensure cube/ and ui/ directories are accessible and contain cube.py and viewer.py respectively.", file=sys.stderr)
    sys.exit(1)

# --- Application Setup ---
app = Ursina(title="Rubik's Cube Simulator")

# --- Model and Viewer Initialization ---
try:
    cube_model = RubiksCube(size=3)
    viewer = RubiksCubeViewer(cube_model)
except Exception as e:
    print(f"Error initializing cube model or viewer: {e}", file=sys.stderr)
    sys.exit(1)

# --- Initial State (Optional Scramble) ---
print("Applying initial scramble...")
# scramble_seq = cube_model.scramble(20) # Apply scramble to model
# print(f"Scramble Applied: {scramble_seq}")
# viewer.update_colors() # Update viewer to match scrambled state
# print("Initial state set.")
# print("Initial Logical State:")
# print(cube_model)

# --- Camera Setup ---
camera.position = (10, 12, -20) # Adjusted for better view
camera.look_at(viewer.parent_entity)
camera.fov = 40

# --- Animation and State Update Logic ---
current_move_index = 0
moves_to_apply = []
is_processing_moves = False
DEFAULT_ANIMATION_DURATION = 0.25 # Slightly slower, potentially smoother animation

def process_next_move():
    """Processes the next move in the `moves_to_apply` list."""
    global current_move_index, is_processing_moves
    if current_move_index < len(moves_to_apply):
        move = moves_to_apply[current_move_index]
        print(f"Animating: {move}")

        # --- Core Logic ---
        # a) Start animation (visual)
        viewer.animate_move(move, duration=DEFAULT_ANIMATION_DURATION)

        # b) Schedule logical update *after* animation
        #    Use invoke with a slight delay after animation finishes
        invoke(cube_model.apply_move, move, delay=DEFAULT_ANIMATION_DURATION + 0.02)

        # c) Schedule the next step in the sequence
        #    Use invoke with a slightly longer delay to allow state update and prevent overlap
        invoke(process_next_move, delay=DEFAULT_ANIMATION_DURATION + 0.05)
        # --- End Core Logic ---

        current_move_index += 1
    else:
        print("Finished applying sequence.")
        print("Final logical state:")
        print(cube_model)
        # Optional: Force color update if needed, though should be correct if logic is sound
        # invoke(viewer.update_colors, delay=0.1) # Add small delay if needed
        is_processing_moves = False
        moves_to_apply.clear() # Clear the list for the next sequence

def apply_sequence(sequence_str: str):
    """Starts the process of applying a sequence of moves."""
    global moves_to_apply, current_move_index, is_processing_moves
    if viewer.is_animating or is_processing_moves:
        print("Cannot start new sequence while animation/processing is active.")
        return
    moves_to_apply = sequence_str.strip().split()
    if not moves_to_apply:
        return
    current_move_index = 0
    is_processing_moves = True
    print(f"Starting sequence: {sequence_str}")
    process_next_move() # Start the first move

# --- Input Handling ---
instruction_text = print_on_screen(
    "Keys: U, D, L, R, F, B | Shift: Inverse (') | Ctrl: Double (2)\n"
    "S: Solve | X: Example Seq | C: Scramble | Esc: Quit",
    position=(-0.85, 0.48),
    scale=0.9,
    origin=(-0.5, 0.5) # Align text top-left
)

def input(key):
    """Handles keyboard input for cube manipulation and other actions."""
    global is_processing_moves

    # Always allow quitting
    if key == 'escape':
        quit()

    # Ignore input if an animation sequence is currently running
    if viewer.is_animating or is_processing_moves:
        print(f"Input '{key}' ignored: Animation/Processing in progress.")
        return

    move = None
    base_key = key.replace(' shift', '').replace(' control', '')
    is_shift = 'shift' in key
    is_ctrl = 'control' in key

    # Map keys to faces
    key_face_map = {
        'u': 'U', 'd': 'D', 'l': 'L', 'r': 'R', 'f': 'F', 'b': 'B'
    }

    if base_key in key_face_map:
        face = key_face_map[base_key]
        if is_shift:
            move = f"{face}'"
        elif is_ctrl:
            move = f"{face}2"
        else:
            move = face
    elif key == 's': # Solve
        if not cube_model.is_solved():
            print("Requesting solve steps...")
            solution = cube_model.get_solve_steps()
            if solution:
                print(f"Solver returned {len(solution)} moves.")
                apply_sequence(" ".join(solution))
            else:
                print("Solver failed or returned no steps.")
        else:
            print("Cube already solved.")
        return # Don't treat 's' as a move to apply immediately
    elif key == 'x': # Example Sequence (e.g., Sexy Move)
        apply_sequence("R U R' U R U2 R'")
        return
    elif key == 'c': # Scramble
        print("Scrambling...")
        scramble_seq = cube_model.scramble(20) # Apply scramble to model directly
        print(f"Applied Scramble: {scramble_seq}")
        viewer.update_colors() # Update viewer instantly after scramble
        print("Scramble complete. Logical State:")
        print(cube_model)
        return # Scramble is instant, no animation sequence needed here

    # If a valid move was generated, apply it using the sequence processor
    if move:
        apply_sequence(move)

def update():
    """Ursina update function, called every frame."""
    if mouse.left: # Check if the left mouse button is held down
        # Prevent dragging during animation/processing
        if viewer.is_animating or is_processing_moves:
            return

        # Rotate the parent entity based on mouse movement
        # Adjust sensitivity as needed
        sensitivity = 150
        viewer.parent_entity.rotation_y += mouse.delta[0] * sensitivity
        viewer.parent_entity.rotation_x -= mouse.delta[1] * sensitivity

# --- Run Application ---
if __name__ == '__main__':
    print("Starting Rubik's Cube Simulator...")
    app.run()
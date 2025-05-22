# c:\Users\Chris\Documents\GitHub\RubikSimulator\main.py
from ursina import Ursina, invoke, camera, print_on_screen, held_keys, mouse, destroy, Text
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

# --- Cube Size Configuration ---
MIN_CUBE_SIZE = 2
MAX_CUBE_SIZE = 20 # Adjust as needed, larger cubes can impact performance
current_cube_size = 3

# --- Model and Viewer Initialization ---
try:
    cube_model = RubiksCube(size=current_cube_size)
    viewer = RubiksCubeViewer(cube_model)
except Exception as e:
    print(f"Error initializing cube model or viewer: {e}", file=sys.stderr)
    sys.exit(1)

# --- Initial State (Optional Scramble) ---
# print("Applying initial scramble...")
# scramble_seq = cube_model.scramble(20) # Apply scramble to model
# print(f"Scramble Applied: {scramble_seq}")
# viewer.update_colors() # Update viewer to match scrambled state
# print("Initial state set.")
# print("Initial Logical State:")
# print(cube_model)

# --- Camera Setup ---
# Define a base position for a 3x3 cube, which is our reference
REFERENCE_CAMERA_POSITION_3X3 = (10, 12, -20)
REFERENCE_CUBE_SIZE_FOR_CAMERA = 3.0 # Use float for accurate scaling
camera.position = REFERENCE_CAMERA_POSITION_3X3
camera.look_at(viewer.parent_entity if hasattr(viewer, 'parent_entity') else viewer)
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
instruction_text_entity = Text(origin=(-0.5, 0.5), position=(-0.85, 0.48), scale=0.9)

def _update_instruction_text():
    """Updates the on-screen instruction text with current cube size."""
    global instruction_text_entity, current_cube_size
    text_content = (
        f"Size: {current_cube_size}x{current_cube_size}x{current_cube_size} (INS/DEL to change)\n"
        "Mouse: Right-click on facelet quadrant to rotate. Left-drag to rotate cube.\n"
        "S: Solve (3x3 only) | X: Example Seq | C: Scramble | Esc: Quit"
    )
    if instruction_text_entity:
        instruction_text_entity.text = text_content
    else: # Should not happen after init, but as a fallback
        print("Error: instruction_text_entity not initialized.")


def input(key):
    """Handles keyboard input for cube manipulation and other actions."""
    global is_processing_moves

    # Always allow quitting
    if key == 'escape':
        quit()

    # Ignore input if an animation sequence is currently running
    # or if cube size change is happening (though size change itself checks this)
    if viewer.is_animating or is_processing_moves:
        print(f"Input '{key}' ignored: Animation/Processing in progress.")
        return

    # Handle cube size changes
    if key == 'insert':
        _attempt_change_cube_size(current_cube_size + 1)
        return
    if key == 'delete':
        _attempt_change_cube_size(current_cube_size - 1)
        return

    # Keyboard commands that are not direct face moves
    if key == 's': # Solve
        if not cube_model.is_solved(): # Check if already solved
            print("Requesting solve steps...")
            solution = cube_model.get_solve_steps() # This now checks for 3x3 internally
            if solution: # Will be empty if not 3x3 or if solver fails
                if cube_model.size == 3: # Only apply if it's a 3x3
                    print(f"Solver returned {len(solution)} moves for 3x3 cube.")
                    apply_sequence(" ".join(solution))
                # Message for non-3x3 is handled in cube_model.get_solve_steps
            else:
                if cube_model.size == 3: # Only print "failed" if it was a 3x3 attempt
                    print("Solver failed or returned no steps for 3x3 cube.")
        else:
            print("Cube already solved.")
        return
    elif key == 'x': # Example Sequence (e.g., Sexy Move)
        apply_sequence("R U R' U R U2 R'") # This sequence is generic
        return
    elif key == 'c': # Scramble
        print("Scrambling...")
        # Scramble logic is now more robust for NxN in cube_model
        scramble_seq = cube_model.scramble(num_moves=max(5, current_cube_size * 7)) # More moves for bigger cubes
        print(f"Applied Scramble: {scramble_seq}")
        viewer.update_colors() # Update viewer instantly after scramble
        print("Scramble complete. Logical State:")
        print(cube_model)
        return
    
    # Handle mouse clicks for face rotation
    if key == 'right mouse down':
        if viewer and not viewer.is_animating and not is_processing_moves:
            move = viewer.get_move_from_current_hover()
            if move:
                print(f"Mouse click triggered move: {move}")
                apply_sequence(move)
        return

def _attempt_change_cube_size(new_size: int):
    """
    Attempts to change the cube size.
    Re-initializes the cube model and viewer.
    """
    global cube_model, viewer, current_cube_size, is_processing_moves

    if viewer.is_animating or is_processing_moves:
        print("Cannot change cube size: Animation/Processing in progress.")
        return

    if not (MIN_CUBE_SIZE <= new_size <= MAX_CUBE_SIZE):
        print(f"Cannot change size: {new_size}x{new_size}x{new_size} is out of allowed range ({MIN_CUBE_SIZE}-{MAX_CUBE_SIZE}).")
        return

    print(f"Changing cube size from {current_cube_size}x{current_cube_size}x{current_cube_size} to {new_size}x{new_size}x{new_size}...")

    # Destroy the old viewer's Ursina entities
    if viewer and hasattr(viewer, 'parent_entity') and viewer.parent_entity:
        destroy(viewer.parent_entity)
    elif viewer and isinstance(viewer, Ursina.Entity): # If viewer itself is the main entity
        destroy(viewer)


    current_cube_size = new_size
    try:
        cube_model = RubiksCube(size=current_cube_size) # Create new logical model
        viewer = RubiksCubeViewer(cube_model)           # Create new visual representation
    except Exception as e:
        print(f"CRITICAL ERROR re-initializing cube/viewer for size {new_size}: {e}", file=sys.stderr)
        # Attempt to revert or handle gracefully
        print("Attempting to revert to previous size or a default size...")
        # For simplicity, exiting here, but a real app might try to recover
        # current_cube_size = 3 # or previous_valid_size
        # cube_model = RubiksCube(size=current_cube_size)
        # viewer = RubiksCubeViewer(cube_model)
        sys.exit(f"Failed to re-initialize cube for size {new_size}. Exiting.")

    # Adjust camera position for the new cube size to ensure it's in view
    # Scale the camera distance based on the cube size relative to the reference 3x3 setup
    scale_factor = current_cube_size / REFERENCE_CUBE_SIZE_FOR_CAMERA

    new_cam_x = REFERENCE_CAMERA_POSITION_3X3[0] * scale_factor
    new_cam_y = REFERENCE_CAMERA_POSITION_3X3[1] * scale_factor
    new_cam_z = REFERENCE_CAMERA_POSITION_3X3[2] * scale_factor # More negative z means further away

    camera.position = (new_cam_x, new_cam_y, new_cam_z)
    
    # Ensure the camera is looking at the new cube
    camera.look_at(viewer.parent_entity if hasattr(viewer, 'parent_entity') else viewer)
    
    _update_instruction_text() # Update UI
    print(f"Cube size changed to {current_cube_size}x{current_cube_size}x{current_cube_size}.")


def update():
    """Ursina update function, called every frame."""
    # Update hover highlights first
    if viewer: # viewer might be briefly None during size change
        viewer.update_hover_highlight()

    if mouse.left: # Check if the left mouse button is held down
        # Allow cube rotation even during animation, but not processing a sequence (is_processing_moves)

        # Rotate the parent entity based on mouse movement
        # Adjust sensitivity as needed
        sensitivity = 150
        target_entity = viewer.parent_entity if hasattr(viewer, 'parent_entity') else viewer
        if target_entity:
            target_entity.rotation_y += mouse.delta[0] * sensitivity
            target_entity.rotation_x -= mouse.delta[1] * sensitivity


# --- Run Application ---
if __name__ == '__main__':
    print("Starting Rubik's Cube Simulator...")
    _update_instruction_text() # Initial call to set the instruction text
    app.run()

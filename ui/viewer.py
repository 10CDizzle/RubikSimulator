# c:\Users\Chris\Documents\GitHub\RubikSimulator\ui\viewer.py
from ursina import Entity, color, Quad, load_model, Vec3, scene, destroy, invoke, Sequence, Func, Wait, curve
import numpy as np # Keep numpy for state checking if needed
import sys
from typing import TYPE_CHECKING # Import for type hinting

# Import your cube class for type hinting (avoids circular import issues)
if TYPE_CHECKING:
    from cube.cube import RubiksCube

# Map integer color indices (expected from the model's state array) to Ursina colors
# Ensure indices 0-5 match the RubiksCube model's color assignment convention
INT_COLOR_MAP = {
    0: color.white,  # U face color
    1: color.yellow, # D face color
    2: color.orange, # L face color
    3: color.red,    # R face color
    4: color.green,  # F face color
    5: color.blue,   # B face color
    -1: color.black # Optional: Color for potential interior pieces if needed
}

# Import the constant directly from the cube module
from cube.cube import FACE_NAMES

class RubiksCubeViewer:
    def __init__(self, cube_model: 'RubiksCube'): # Use type hint
        """
        Initializes the viewer for a Rubik's Cube model.

        Args:
            cube_model: An instance of the RubiksCube class.
        """
        self.cube_model = cube_model

        # --- Updated Checks ---
        # Check if the cube_model has the required attributes and methods
        if not hasattr(cube_model, 'size'):
            raise AttributeError("cube_model must have a 'size' attribute.")
        if not hasattr(cube_model, 'get_state_for_solver') or not callable(cube_model.get_state_for_solver):
             raise AttributeError("cube_model must have a callable 'get_state_for_solver' method.")
        # We will check the shape of the returned state in update_colors

        self.parent_entity = Entity(model=None, name="CubeParent")
        # Store facelets keyed by their logical position and orientation
        # (x, y, z, axis_index, direction) -> Entity
        self.facelets = {}
        # Store backing pieces keyed by their logical position
        # (x, y, z) -> Entity
        self.backing_pieces = {}
        self._initial_update_done = False # Flag to print state only once
        self.is_animating = False # Flag to prevent concurrent animations
        self.create_visualization()
        self.update_colors() # Initial color update

    def create_visualization(self):
        """Creates the Ursina entities representing the Rubik's Cube of size n."""

        # Clear previous visualization if any
        for piece in self.backing_pieces.values():
            if piece: destroy(piece)
        for facelet in self.facelets.values():
            if facelet: destroy(facelet)
        self.backing_pieces = {} # Reset dictionary
        self.facelets.clear()

        size = self.cube_model.size # Get size 'n' from the model
        if size < 2:
            print("Warning: Cube size must be at least 2.", file=sys.stderr)
            return
        n = size - 1 # Max index
        offset = (size - 1) / 2.0 # Center the cube visually

        # --- Model Loading (remains the same) ---
        try:
            piece_model = load_model('rubik_piece.obj', use_deepcopy=True)
            piece_scale = 1.0
        except Exception:
            print("Warning: 'rubik_piece.obj' not found. Using default 'cube' model.")
            piece_model = 'cube'
            piece_scale = 1.0
            
        # --- Face Info: Maps normal vector to visual properties ---
        # axis: 0=X, 1=Y, 2=Z
        # dir: 1=Positive face (R, U, F), -1=Negative face (L, D, B)
        face_info = {
            Vec3(0, 1, 0): {'name': 'U', 'offset': Vec3(0, 0.501, 0), 'rotation': Vec3(-90, 0, 0), 'axis': 1, 'dir': 1},  # Up (+Y)
            Vec3(0,-1, 0): {'name': 'D', 'offset': Vec3(0,-0.501, 0), 'rotation': Vec3(90, 0, 0),   'axis': 1, 'dir': -1}, # Down (-Y)
            Vec3(1, 0, 0): {'name': 'R', 'offset': Vec3(0.501, 0, 0), 'rotation': Vec3(0, 90, 0),   'axis': 0, 'dir': 1},  # Right (+X)
            Vec3(-1,0, 0): {'name': 'L', 'offset': Vec3(-0.501,0, 0), 'rotation': Vec3(0,-90, 0),  'axis': 0, 'dir': -1}, # Left (-X)
            Vec3(0, 0, 1): {'name': 'F', 'offset': Vec3(0, 0, 0.501), 'rotation': Vec3(0, 0, 0),    'axis': 2, 'dir': 1},  # Front (+Z)
            Vec3(0, 0,-1): {'name': 'B', 'offset': Vec3(0, 0,-0.501), 'rotation': Vec3(0, 180, 0), 'axis': 2, 'dir': -1}, # Back (-Z)
        }

        # Iterate through all n*n*n potential cubie positions
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    pos_x = x - offset
                    pos_y = y - offset
                    pos_z = z - offset
                    is_internal = (0 < x < n and 0 < y < n and 0 < z < n)

                    # Create backing piece (dark grey cube) if it's not internal
                    if not is_internal:
                        piece = Entity(
                            model=piece_model,
                            color=color.dark_gray,
                            position=(pos_x, pos_y, pos_z),
                            scale=piece_scale,
                            parent=self.parent_entity,
                            name=f"piece_{x}_{y}_{z}",
                            # Store logical coordinates for easy lookup
                            logic_coords=(x, y, z)
                        )
                        self.backing_pieces[(x, y, z)] = piece
                    # Create facelets (colored quads) for exterior faces
                    for normal, info in face_info.items():
                        is_exterior = False
                        if info['axis'] == 1 and info['dir'] == 1 and y == n: is_exterior = True    # Top face
                        elif info['axis'] == 1 and info['dir'] == -1 and y == 0: is_exterior = True # Bottom face
                        elif info['axis'] == 0 and info['dir'] == 1 and x == n: is_exterior = True  # Right face
                        elif info['axis'] == 0 and info['dir'] == -1 and x == 0: is_exterior = True # Left face
                        elif info['axis'] == 2 and info['dir'] == 1 and z == n: is_exterior = True  # Front face
                        elif info['axis'] == 2 and info['dir'] == -1 and z == 0: is_exterior = True # Back face

                        if is_exterior:
                            try:
                                facelet_key = (x, y, z, info['axis'], info['dir'])
                                facelet = Entity(
                                    model=Quad(scale=(0.9, 0.9)),
                                    color=color.light_gray, # Default color
                                    position=Vec3(pos_x, pos_y, pos_z) + info['offset'],
                                    rotation=info['rotation'], # Rotation to face outwards
                                    parent=self.parent_entity, # Parent to the main cube entity
                                    double_sided=False,
                                    name=f"facelet_{info['name']}_{x}_{y}_{z}",
                                    # Store logical coordinates and face info for easy lookup
                                    logic_key=facelet_key
                                )
                                facelet.world_parent = self.parent_entity
                                self.facelets[facelet_key] = facelet
                            except Exception as e:
                                print(f"Error creating facelet for key {facelet_key}: {e}", file=sys.stderr)

        expected_facelets = 6 * size * size
        if len(self.facelets) != expected_facelets:
             print(f"Warning: Created {len(self.facelets)} facelet entities, expected {expected_facelets}.", file=sys.stderr)

        expected_backing = size**3 - (size-2)**3 if size > 1 else size**3
        if len(self.backing_pieces) != expected_backing:
             print(f"Warning: Created {len(self.backing_pieces)} backing piece entities, expected {expected_backing}.", file=sys.stderr)

    def update_colors(self):
        """Updates facelet colors based on the cube_model's state."""
        # try: # Removed top-level try/except to let errors propagate if needed
            # --- Updated State Retrieval ---
            # Get the 3D state array using the method from the cube model
        state_array = self.cube_model.get_state_for_solver()

        # --- ADDED: Print initial state received by viewer ---
        if not self._initial_update_done:
            print("\n--- Initial State Received by Viewer ---")
            print(f"Shape: {state_array.shape}")
            # Use model's size to correctly determine max index for printing slices
            model_max_index = self.cube_model.size - 1
            # Print slices corresponding to faces for easier reading
            print("U (Y=n):")
            print(state_array[:, model_max_index, :])
            print("R (X=n):")
            print(state_array[model_max_index, :, :])
            print("F (Z=n):")
            print(state_array[:, :, model_max_index])
            print("D (Y=0):")
            print(state_array[:, 0, :])
            print("L (X=0):")
            print(state_array[0, :, :]) # Correct, uses 0
            print("B (Z=0):")
            print(state_array[:, :, 0])
            print("----------------------------------------\n")
            self._initial_update_done = True
        # --- END ADDED SECTION ---


            # Check the shape of the retrieved state array
            expected_shape = (self.cube_model.size, self.cube_model.size, self.cube_model.size)
            if not isinstance(state_array, np.ndarray) or state_array.shape != expected_shape:
                 print(f"Error: get_state_for_solver() returned invalid state. Expected shape {expected_shape}, got {type(state_array)} with shape {getattr(state_array, 'shape', 'N/A')}.", file=sys.stderr)
                 return

            updated_count = 0
            for key, facelet_entity in self.facelets.items():
                if facelet_entity:
                    x, y, z, axis, direction = key
                    try:
                        color_index = state_array[x, y, z]
                        facelet_entity.color = INT_COLOR_MAP.get(color_index, color.pink) # Pink for errors
                        updated_count += 1
                    except IndexError:
                        print(f"Error: Index out of bounds ({x},{y},{z}) accessing state array.", file=sys.stderr)
                        facelet_entity.color = color.magenta # Magenta for index errors
                    except KeyError:
                        # This error check should ideally happen inside get_state_for_solver or the cube itself
                        print(f"Error: Color index {color_index} not found in INT_COLOR_MAP.", file=sys.stderr)
                        facelet_entity.color = color.cyan # Cyan for map errors
                    except Exception as e:
                        print(f"Error updating color for facelet {key}: {e}", file=sys.stderr)
                        facelet_entity.color = color.black # Black for other errors

        # except Exception as e:
        #     print(f"General Error in update_colors: {e}", file=sys.stderr)
            # Potentially add more specific error handling if needed

    def animate_move(self, move: str, duration: float = 0.2):
        """
        Animates a single cube move (e.g., 'R', "U'", 'F2').

        Args:
            move: The move string in standard notation.
            duration: The time in seconds for the animation to complete.
        """
        if self.is_animating:
            print("Warning: Animation already in progress. Move ignored.", file=sys.stderr)
            return

        if not move:
            return

        size = self.cube_model.size
        n = size - 1

        # --- Parse Move ---
        face_char = move[0].upper()
        if face_char not in FACE_NAMES: # Use the imported constant
            print(f"Error: Invalid move face '{face_char}' in animate_move.", file=sys.stderr)
            return

        direction = 1 # Default CW
        turns = 1     # Default 90 degrees
        if len(move) > 1:
            if move[1] == "'":
                direction = -1 # CCW
            elif move[1] == '2':
                turns = 2 # 180 degrees
            else:
                print(f"Error: Invalid move modifier '{move[1]}' in animate_move.", file=sys.stderr)
                return
        if len(move) > 2:
             print(f"Error: Invalid move format '{move}' in animate_move.", file=sys.stderr)
             return

        angle = 90 * direction * turns

        # --- Determine Axis, Slice, and Rotation Vector ---
        axis_map = {'U': (0, 1, 0), 'D': (0, -1, 0), 'L': (-1, 0, 0),
                    'R': (1, 0, 0), 'F': (0, 0, 1), 'B': (0, 0, -1)}
        slice_info = { # Map face char to (axis_index, slice_index)
            'U': (1, n), 'D': (1, 0),
            'L': (0, 0), 'R': (0, n),
            'F': (2, n), 'B': (2, 0)
        }

        if face_char not in slice_info:
            print(f"Error: Could not determine slice for face '{face_char}'.", file=sys.stderr)
            return

        axis_index, slice_index = slice_info[face_char]
        rotation_axis = axis_map[face_char] # Use the normal vector of the face for rotation axis

        # --- Identify Pieces in the Slice ---
        pieces_to_move = []
        # Find backing pieces in the slice
        for coords, piece_entity in self.backing_pieces.items():
            if coords[axis_index] == slice_index:
                pieces_to_move.append(piece_entity)

        # Find facelets in the slice
        for key, facelet_entity in self.facelets.items():
            x, y, z, _, _ = key
            if (axis_index == 0 and x == slice_index) or \
               (axis_index == 1 and y == slice_index) or \
               (axis_index == 2 and z == slice_index):
                pieces_to_move.append(facelet_entity)

        if not pieces_to_move:
            print(f"Warning: No pieces found for move '{move}' (axis={axis_index}, slice={slice_index}).", file=sys.stderr)
            return

        # --- Perform Animation ---
        self.is_animating = True
        pivot = Entity(parent=self.parent_entity, name=f"pivot_{move}", world_rotation=(0,0,0))

        # Parent pieces to the pivot
        for p in pieces_to_move:
            p.world_parent = pivot

        # Animate the pivot: Calculate the target rotation vector
        # Target rotation is the axis scaled by the angle. Ensure axis is Vec3.
        target_rotation = pivot.rotation + Vec3(rotation_axis) * angle
        anim = pivot.animate_rotation(target_rotation, duration=duration, curve=curve.linear)
        
        # Schedule cleanup after animation
        # Pass the calculated target_rotation to the finish function
        invoke(self._finish_animation, pivot, pieces_to_move, target_rotation, delay=duration + 0.01) # Small buffer

    def _finish_animation(self, pivot: Entity, moved_pieces: list, target_rotation: Vec3):
        """Helper function called after animation completes."""
        # --- Snap to Grid ---
        # Calculate the final rotation rounded to the nearest 90 degrees
        snapped_x = round(target_rotation.x / 90) * 90
        snapped_y = round(target_rotation.y / 90) * 90
        snapped_z = round(target_rotation.z / 90) * 90
        snapped_rotation = Vec3(snapped_x, snapped_y, snapped_z)
        
        # Apply the exact snapped rotation to the pivot *before* unparenting
        pivot.rotation = snapped_rotation
        
        # Unparent pieces back to the main cube parent
        for p in moved_pieces:
            p.world_parent = self.parent_entity
            # Optional: Round individual piece rotations if needed after complex sequences,
            # but inheriting the snapped pivot rotation should be sufficient.
            # p.rotation_x = round(p.rotation_x / 90) * 90
            # p.rotation_y = round(p.rotation_y / 90) * 90
            # p.rotation_z = round(p.rotation_z / 90) * 90
            
        destroy(pivot)
        self.is_animating = False
        # print("Animation finished.") # Optional debug print

# c:\Users\Chris\Documents\GitHub\RubikSimulator\ui\viewer.py
from ursina import Entity, color, Quad, load_model, Vec3, scene, destroy, invoke, Sequence, Func, Wait, curve, mouse
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

        # --- Attributes for mouse interaction ---
        self.hovered_facelet_details = None  # Tuple: (facelet_entity, quadrant_name) for actionable hover
        self.last_hovered_facelet_entity = None # Stores the last facelet entity that was generally hovered
        self.original_facelet_colors = {}    # Stores original color of facelets for highlighting
        self.quadrant_highlight_indicator = None # Entity to show quadrant highlight
        self.highlight_intensity = 0.3       # How much to lighten/mix color for facelet highlight
        self.quadrant_dead_zone = 0.15       # Percentage of facelet half-size for dead zone (e.g., 0.1 means 10% dead zone from center)

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
                                    logic_key=facelet_key,
                                    main_face_name=info['name'], # Store 'U', 'F', etc. for interaction
                                    collider='box' # Ensure it's collidable for mouse hover
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
            # Each cubie position (x,y,z) should now hold data for its 6 potential faces.
            # The data could be color indices, with -1 for non-existent faces.
            expected_shape = (self.cube_model.size, self.cube_model.size, self.cube_model.size, 6)
            if not isinstance(state_array, np.ndarray) or state_array.shape != expected_shape:
                 print(f"Error: get_state_for_solver() returned invalid state. Expected shape {expected_shape}, got {type(state_array)} with shape {getattr(state_array, 'shape', 'N/A')}.", file=sys.stderr)
                 print("Ensure cube_model.get_state_for_solver() returns a NumPy array where each element [x,y,z] is a tuple/array of 6 color indices (for -X, +X, -Y, +Y, -Z, +Z faces of the cubie at x,y,z).", file=sys.stderr)
                 return

            updated_count = 0
            for key, facelet_entity in self.facelets.items():
                if facelet_entity:
                    x, y, z, face_axis, face_direction = key
                    try:
                        # state_array[x,y,z] is now a tuple/array of 6 color indices
                        # Order assumed: (-X, +X, -Y, +Y, -Z, +Z) or (L, R, D, U, B, F)
                        cubie_face_colors = state_array[x, y, z]
                        
                        # Map (face_axis, face_direction) to an index in cubie_face_colors
                        # (axis=0 (X), dir=-1 (L)) -> index 0
                        # (axis=0 (X), dir=1  (R)) -> index 1
                        # (axis=1 (Y), dir=-1 (D)) -> index 2
                        # (axis=1 (Y), dir=1  (U)) -> index 3
                        # (axis=2 (Z), dir=-1 (B)) -> index 4
                        # (axis=2 (Z), dir=1  (F)) -> index 5
                        if face_axis == 0: # X-axis
                            tuple_idx = 0 if face_direction == -1 else 1
                        elif face_axis == 1: # Y-axis
                            tuple_idx = 2 if face_direction == -1 else 3
                        else: # Z-axis (face_axis == 2)
                            tuple_idx = 4 if face_direction == -1 else 5
                        
                        color_index = cubie_face_colors[tuple_idx]

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

        print(f"[DEBUG] animate_move START for '{move}'. Parent entity world_rotation: {self.parent_entity.world_rotation}, world_position: {self.parent_entity.world_position}")

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

        # --- Determine Axis and Slice ---
        slice_info = { # Map face char to (axis_index, slice_index)
            'U': (1, n), 'D': (1, 0),
            'L': (0, 0), 'R': (0, n),
            'F': (2, n), 'B': (2, 0)
        }
        if face_char not in slice_info:
            print(f"Error: Could not determine slice for face '{face_char}'.", file=sys.stderr)
            return

        axis_index, slice_index = slice_info[face_char]

        # --- Identify Pieces in the Slice ---
        selected_entities = set() # Use a set to automatically handle duplicates

        # Find backing pieces in the slice
        for coords, piece_entity in self.backing_pieces.items():
            # coords is (logical_x, logical_y, logical_z)
            if coords[axis_index] == slice_index:
                selected_entities.add(piece_entity)

        # Find facelets in the slice
        for key, facelet_entity in self.facelets.items():
            # key is (logical_x, logical_y, logical_z, face_axis, face_direction)
            cubie_logical_coords = key[:3] # Extract (x,y,z)
            if cubie_logical_coords[axis_index] == slice_index:
                selected_entities.add(facelet_entity)
        
        pieces_to_move = list(selected_entities)

        if not pieces_to_move:
            print(f"Warning: No pieces found for move '{move}' (axis={axis_index}, slice={slice_index}).", file=sys.stderr)
            return

        # --- Perform Animation ---
        self.is_animating = True
        # Pivot is created at the parent's origin with no initial rotation relative to the parent.
        pivot = Entity(parent=self.parent_entity, name=f"pivot_{move}", position=(0,0,0), rotation=(0,0,0))

        # Parent pieces to the pivot
        for p in pieces_to_move:
            p.world_parent = pivot # Preserves world orientation while re-parenting

        # Ursina's positive rotation is Counter-Clockwise.
        # 'angle' is calculated such that:
        #   - CW moves (U, R, F, D, L, B) have angle = +90 or +180.
        #   - CCW moves (U', R', F', D', L', B') have angle = -90 or -180.
        # To get the desired visual rotation with Ursina, we invert 'angle'.
        ursina_animation_angle = -angle

        # Animate the pivot's local rotation on the correct axis
        if face_char in ('U', 'D'): # Y-axis
            pivot.animate_rotation_y(ursina_animation_angle, duration=duration, curve=curve.linear)
        elif face_char in ('L', 'R'): # X-axis
            pivot.animate_rotation_x(ursina_animation_angle, duration=duration, curve=curve.linear)
        elif face_char in ('F', 'B'): # Z-axis
            pivot.animate_rotation_z(ursina_animation_angle, duration=duration, curve=curve.linear)
        
        # Schedule cleanup after animation
        invoke(self._finish_animation, pivot, pieces_to_move, delay=duration + 0.01) # Small buffer

    def _finish_animation(self, pivot: Entity, moved_pieces: list):
        """Helper function called after animation completes."""
        # Re-enabled diagnostic print for parent entity's rotation
        print(f"[DEBUG] _finish_animation START. Parent entity world_rotation: {self.parent_entity.world_rotation}, world_position: {self.parent_entity.world_position}")

        # Snap pivot's local rotation to nearest 90 degrees.
        # This ensures that after animation, the pivot is perfectly aligned before re-parenting.
        pivot.rotation_x = round(pivot.rotation_x / 90) * 90
        pivot.rotation_y = round(pivot.rotation_y / 90) * 90
        pivot.rotation_z = round(pivot.rotation_z / 90) * 90
        
        # Store the final world transforms of the pieces while they are children of the snapped pivot.
        # At this point, their world_transform is what we want it to be.
        final_world_transforms = {piece: piece.world_transform for piece in moved_pieces}

        # Change parent back to the main cube parent.
        # Using world_parent should preserve their world transforms.
        for p in moved_pieces:
            p.world_parent = self.parent_entity # This attempts to keep p.world_transform constant
            
        destroy(pivot) # Destroy the pivot now that pieces are no longer its children.

        # Re-assert the world_transform for each moved piece.
        # This is a belt-and-suspenders approach: world_parent should have placed them correctly
        # in world space, but this explicitly enforces their final calculated world state.
        # final state in world space. Ursina will update their local transforms accordingly.
        for p in moved_pieces:
            p.world_transform = final_world_transforms[p]
            # Snap local rotation of the piece to the nearest 90-degree increment.
            # This helps clean up any floating-point inaccuracies after world_transform is set
            # and local transforms are derived, especially since parent_entity is axis-aligned.
            p.rotation_x = round(p.rotation_x / 90) * 90
            p.rotation_y = round(p.rotation_y / 90) * 90
            p.rotation_z = round(p.rotation_z / 90) * 90
            
        self.is_animating = False
        print(f"[DEBUG] _finish_animation END. Parent entity world_rotation: {self.parent_entity.world_rotation}, world_position: {self.parent_entity.world_position}. Move completed.")

    def update_hover_highlight(self):
        """Updates visual highlights for hovered facelets and their quadrants."""
        # 1. Restore color of the previously generally hovered facelet
        if self.last_hovered_facelet_entity:
            if self.last_hovered_facelet_entity in self.original_facelet_colors:
                self.last_hovered_facelet_entity.color = self.original_facelet_colors[self.last_hovered_facelet_entity]
            self.last_hovered_facelet_entity = None

        # Always disable quadrant indicator and clear actionable hover details initially for this frame
        if self.quadrant_highlight_indicator:
            self.quadrant_highlight_indicator.enabled = False
        self.hovered_facelet_details = None  # Clears details for a move action

        # 2. Check current hover
        current_hovered_entity = mouse.hovered_entity

        if current_hovered_entity and hasattr(current_hovered_entity, 'main_face_name') and \
           current_hovered_entity.name.startswith('facelet_'):
            facelet = current_hovered_entity
            self.last_hovered_facelet_entity = facelet  # This facelet is being hovered generally

            # Store original color if not already stored
            self.original_facelet_colors.setdefault(facelet, facelet.color)

            # Highlight the facelet itself (general hover) by interpolating its color towards white
            original_c = self.original_facelet_colors[facelet]
            white_c = color.white # This is a Vec4
            facelet.color = original_c * (1 - self.highlight_intensity) + white_c * self.highlight_intensity

            # Determine quadrant for actionable highlight (for click-to-move)
            # If 'facelet' is the 'mouse.hovered_entity', then 'mouse.point' contains
            # the intersection coordinates in the local space of 'facelet'.
            if mouse.point: # Check if mouse.point is not None (i.e., a valid intersection)
                local_point = mouse.point # Use mouse.point, which is local to mouse.hovered_entity
                lx, ly = local_point.x, local_point.y

                # Facelet Quad model is 0.9x0.9, so local coords range roughly +/- 0.45
                # Dead zone is relative to this half-size (0.45)
                abs_dead_zone = self.quadrant_dead_zone * 0.45
                quadrant_name = None

                if abs(lx) > abs(ly):  # More horizontal than vertical
                    if lx > abs_dead_zone: quadrant_name = "right"
                    elif lx < -abs_dead_zone: quadrant_name = "left"
                elif abs(ly) > abs(lx):  # More vertical than horizontal
                    if ly > abs_dead_zone: quadrant_name = "up"
                    elif ly < -abs_dead_zone: quadrant_name = "down"
                # If in dead zone or exactly on axis lines, quadrant_name remains None

                if quadrant_name:
                    self.hovered_facelet_details = (facelet, quadrant_name) # Set for action

                    # Setup and position quadrant_highlight_indicator
                    if not self.quadrant_highlight_indicator:
                        self.quadrant_highlight_indicator = Entity(
                            model=Quad(scale=(0.25, 0.25)),  # Smaller quad for indicator
                            color=color.rgba(255, 255, 0, 200),  # Semi-transparent yellow
                            parent=facelet,
                            unlit=True,
                            double_sided=True,
                            z=-0.01  # Slightly in front of the facelet surface (local Z)
                        )
                    
                    self.quadrant_highlight_indicator.parent = facelet # Ensure parented correctly
                    self.quadrant_highlight_indicator.enabled = True

                    # Position indicator towards the edge of the facelet.
                    # Facelet half-size is 0.45. Indicator half-size is 0.125.
                    # Position indicator center at ~60% towards the edge from facelet center.
                    offset_dist = 0.45 * 0.6
                    if quadrant_name == "right": self.quadrant_highlight_indicator.position = (offset_dist, 0, -0.01)
                    elif quadrant_name == "left": self.quadrant_highlight_indicator.position = (-offset_dist, 0, -0.01)
                    elif quadrant_name == "up": self.quadrant_highlight_indicator.position = (0, offset_dist, -0.01)
                    elif quadrant_name == "down": self.quadrant_highlight_indicator.position = (0, -offset_dist, -0.01)

    def get_move_from_current_hover(self) -> str | None:
        """
        Determines the cube move based on the currently hovered facelet and active quadrant.
        Returns a move string (e.g., "F", "U'") or None if no actionable hover.
        """
        if self.hovered_facelet_details:
            facelet_entity, quadrant_name = self.hovered_facelet_details

            # main_face_name was stored on the facelet entity during creation
            main_face_name = facelet_entity.main_face_name

            # Map quadrant to CW/CCW rotation of the face
            # "Right" and "Up" quadrants on the facelet surface map to a CW turn of that face.
            # "Left" and "Down" quadrants on the facelet surface map to a CCW turn of that face.
            if quadrant_name in ("right", "up"):
                return main_face_name  # Clockwise
            elif quadrant_name in ("left", "down"):
                return f"{main_face_name}'"  # Counter-clockwise
        return None

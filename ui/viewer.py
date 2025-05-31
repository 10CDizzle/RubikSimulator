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
        self.facelet_thickness = 0.05        # Thickness for cube facelets
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
                            logic_coords=(x, y, z),
                            collider=None # Explicitly disable collider for backing pieces
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
                                    model='cube', # Changed from Quad
                                    scale=(0.9, 0.9, self.facelet_thickness), # Apply thickness
                                    color=color.light_gray, # Default color
                                    position=Vec3(pos_x, pos_y, pos_z) + info['offset'],
                                    rotation=info['rotation'], # Rotation to face outwards
                                    parent=self.parent_entity, # Parent to the main cube entity
                                    double_sided=False, # Less relevant for opaque cube, but keep for consistency
                                    name=f"facelet_cube_{info['name']}_{x}_{y}_{z}",
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
        state_array = self.cube_model.get_state_for_solver()

        if not self._initial_update_done:
            print("\n--- Initial State Received by Viewer ---")
            print(f"Shape: {state_array.shape}")
            model_max_index = self.cube_model.size - 1
            print("U (Y=n):")
            print(state_array[:, model_max_index, :])
            print("R (X=n):")
            print(state_array[model_max_index, :, :])
            print("F (Z=n):")
            print(state_array[:, :, model_max_index])
            print("D (Y=0):")
            print(state_array[:, 0, :])
            print("L (X=0):")
            print(state_array[0, :, :])
            print("B (Z=0):")
            print(state_array[:, :, 0])
            print("----------------------------------------\n")
            self._initial_update_done = True

        expected_shape = (self.cube_model.size, self.cube_model.size, self.cube_model.size, 6)
        if not isinstance(state_array, np.ndarray) or state_array.shape != expected_shape:
             print(f"Error: get_state_for_solver() returned invalid state. Expected shape {expected_shape}, got {type(state_array)} with shape {getattr(state_array, 'shape', 'N/A')}.", file=sys.stderr)
             print("Ensure cube_model.get_state_for_solver() returns a NumPy array where each element [x,y,z] is a tuple/array of 6 color indices (for -X, +X, -Y, +Y, -Z, +Z faces of the cubie at x,y,z).", file=sys.stderr)
             return

        for key, facelet_entity in self.facelets.items():
            if facelet_entity:
                x, y, z, face_axis, face_direction = key
                try:
                    cubie_face_colors = state_array[x, y, z]
                    if face_axis == 0:
                        tuple_idx = 0 if face_direction == -1 else 1
                    elif face_axis == 1:
                        tuple_idx = 2 if face_direction == -1 else 3
                    else:
                        tuple_idx = 4 if face_direction == -1 else 5
                    color_index = cubie_face_colors[tuple_idx]
                    facelet_entity.color = INT_COLOR_MAP.get(color_index, color.pink)
                except IndexError:
                    print(f"Error: Index out of bounds ({x},{y},{z}) accessing state array.", file=sys.stderr)
                    facelet_entity.color = color.magenta
                except KeyError:
                    print(f"Error: Color index {color_index} not found in INT_COLOR_MAP.", file=sys.stderr)
                    facelet_entity.color = color.cyan
                except Exception as e:
                    print(f"Error updating color for facelet {key}: {e}", file=sys.stderr)
                    facelet_entity.color = color.black

    def animate_move(self, move: str, duration: float = 0.2):
        if self.is_animating:
            print("Warning: Animation already in progress. Move ignored.", file=sys.stderr)
            return
        print(f"[DEBUG] animate_move START for '{move}'. Parent entity world_rotation: {self.parent_entity.world_rotation}, world_position: {self.parent_entity.world_position}")
        if not move:
            return

        size = self.cube_model.size
        n = size - 1
        face_char = move[0].upper()
        if face_char not in FACE_NAMES:
            print(f"Error: Invalid move face '{face_char}' in animate_move.", file=sys.stderr)
            return

        direction = 1
        turns = 1
        if len(move) > 1:
            if move[1] == "'": direction = -1
            elif move[1] == '2': turns = 2
            else:
                print(f"Error: Invalid move modifier '{move[1]}' in animate_move.", file=sys.stderr)
                return
        if len(move) > 2:
             print(f"Error: Invalid move format '{move}' in animate_move.", file=sys.stderr)
             return
        angle = 90 * direction * turns

        slice_info = {'U': (1, n), 'D': (1, 0), 'L': (0, 0), 'R': (0, n), 'F': (2, n), 'B': (2, 0)}
        if face_char not in slice_info:
            print(f"Error: Could not determine slice for face '{face_char}'.", file=sys.stderr)
            return
        axis_index, slice_index_val = slice_info[face_char] # Renamed slice_index to avoid conflict

        selected_entities = set()
        for coords, piece_entity in self.backing_pieces.items():
            if coords[axis_index] == slice_index_val:
                selected_entities.add(piece_entity)
        for key, facelet_entity in self.facelets.items():
            cubie_logical_coords = key[:3]
            if cubie_logical_coords[axis_index] == slice_index_val:
                selected_entities.add(facelet_entity)
        pieces_to_move = list(selected_entities)

        if not pieces_to_move:
            print(f"Warning: No pieces found for move '{move}' (axis={axis_index}, slice={slice_index_val}).", file=sys.stderr)
            return

        self.is_animating = True
        pivot = Entity(parent=self.parent_entity, name=f"pivot_{move}", position=(0,0,0), rotation=(0,0,0))
        for p in pieces_to_move:
            p.world_parent = pivot
        ursina_animation_angle = -angle
        if face_char in ('U', 'D'): pivot.animate_rotation_y(ursina_animation_angle, duration=duration, curve=curve.linear)
        elif face_char in ('L', 'R'): pivot.animate_rotation_x(ursina_animation_angle, duration=duration, curve=curve.linear)
        elif face_char in ('F', 'B'): pivot.animate_rotation_z(ursina_animation_angle, duration=duration, curve=curve.linear)
        invoke(self._finish_animation, pivot, pieces_to_move, delay=duration + 0.01)

    def _finish_animation(self, pivot: Entity, moved_pieces: list):
        print(f"[DEBUG] _finish_animation START. Parent entity world_rotation: {self.parent_entity.world_rotation}, world_position: {self.parent_entity.world_position}")
        pivot.rotation_x = round(pivot.rotation_x / 90) * 90
        pivot.rotation_y = round(pivot.rotation_y / 90) * 90
        pivot.rotation_z = round(pivot.rotation_z / 90) * 90
        final_world_transforms = {piece: piece.world_transform for piece in moved_pieces}
        for p in moved_pieces:
            p.world_parent = self.parent_entity
        destroy(pivot)
        for p in moved_pieces:
            p.world_transform = final_world_transforms[p]
            p.rotation_x = round(p.rotation_x / 90) * 90
            p.rotation_y = round(p.rotation_y / 90) * 90
            p.rotation_z = round(p.rotation_z / 90) * 90
        self.is_animating = False
        print(f"[DEBUG] _finish_animation END. Parent entity world_rotation: {self.parent_entity.world_rotation}, world_position: {self.parent_entity.world_position}. Move completed.")

    def update_hover_highlight(self):
        if self.last_hovered_facelet_entity:
            if self.last_hovered_facelet_entity in self.original_facelet_colors:
                self.last_hovered_facelet_entity.color = self.original_facelet_colors[self.last_hovered_facelet_entity]
            self.last_hovered_facelet_entity = None
        if self.quadrant_highlight_indicator:
            self.quadrant_highlight_indicator.enabled = False
        self.hovered_facelet_details = None
        current_hovered_entity = mouse.hovered_entity

        if current_hovered_entity and hasattr(current_hovered_entity, 'main_face_name') and \
           current_hovered_entity.name.startswith('facelet_cube_'):
            facelet = current_hovered_entity
            self.last_hovered_facelet_entity = facelet
            self.original_facelet_colors.setdefault(facelet, facelet.color)
            original_c = self.original_facelet_colors[facelet]
            white_c = color.white
            facelet.color = original_c * (1 - self.highlight_intensity) + white_c * self.highlight_intensity

            if mouse.point is not None:
                try:
                    print(f"    [DEBUG] mouse.point (local to {facelet.name}): {mouse.point}")
                    local_point = mouse.point
                    lx, ly = local_point.x, local_point.y
                    abs_dead_zone = self.quadrant_dead_zone * 0.45
                    quadrant_name = None
                    
                    # THE KEY CHANGE IS HERE: Compare local_point.z against 0.5
                    expected_collider_surface_z = 0.5 
                    print(f"      [DEBUG] local_point.z: {local_point.z:.4f}, expected_collider_surface_z: {expected_collider_surface_z:.4f}")

                    if abs(local_point.z - expected_collider_surface_z) < 0.02: # Check against 0.5
                        print(f"        [DEBUG] Hit front face (assuming unit collider Z). lx: {lx:.2f}, ly: {ly:.2f}, abs_dead_zone: {abs_dead_zone:.2f}")
                        if abs(lx) > abs(ly):
                            if lx > abs_dead_zone: quadrant_name = "right"
                            elif lx < -abs_dead_zone: quadrant_name = "left"
                        elif abs(ly) > abs(lx):
                            if ly > abs_dead_zone: quadrant_name = "up"
                            elif ly < -abs_dead_zone: quadrant_name = "down"
                        print(f"        [DEBUG] Determined quadrant_name: {quadrant_name}")
                    else:
                        print(f"      [DEBUG] Hit point NOT on front face of {facelet.name}. local_point.z: {local_point.z:.4f}")

                    if quadrant_name:
                        self.hovered_facelet_details = (facelet, quadrant_name)
                        print(f"          [DEBUG] Actionable hover: {facelet.name}, Quadrant: {quadrant_name}")
                        if not self.quadrant_highlight_indicator:
                            self.quadrant_highlight_indicator = Entity(
                                model=Quad(scale=(0.25, 0.25)),
                                color=color.rgba(255, 255, 0, 200),
                                parent=facelet,
                                unlit=True,
                                double_sided=True,
                                z=0 
                            )
                        self.quadrant_highlight_indicator.parent = facelet
                        self.quadrant_highlight_indicator.enabled = True
                        indicator_z_pos_local_to_facelet = (self.facelet_thickness / 2) + 0.01
                        offset_dist = 0.45 * 0.6
                        if quadrant_name == "right": self.quadrant_highlight_indicator.position = (offset_dist, 0, indicator_z_pos_local_to_facelet)
                        elif quadrant_name == "left": self.quadrant_highlight_indicator.position = (-offset_dist, 0, indicator_z_pos_local_to_facelet)
                        elif quadrant_name == "up": self.quadrant_highlight_indicator.position = (0, offset_dist, indicator_z_pos_local_to_facelet)
                        elif quadrant_name == "down": self.quadrant_highlight_indicator.position = (0, -offset_dist, indicator_z_pos_local_to_facelet)
                except Exception as e:
                    print(f"    [DEBUG] Error during quadrant detection for {facelet.name}: {e}", file=sys.stderr)

    def get_move_from_current_hover(self) -> str | None:
        if self.hovered_facelet_details:
            facelet_entity, quadrant_name = self.hovered_facelet_details
            main_face_name = facelet_entity.main_face_name
            if quadrant_name in ("right", "up"):
                return main_face_name
            elif quadrant_name in ("left", "down"): 
                return f"{main_face_name}'"
        return None

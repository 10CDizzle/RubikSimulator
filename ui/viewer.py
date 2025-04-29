from ursina import Entity, color, Quad, load_model, Vec3, scene, destroy
import numpy as np # Need numpy if the model uses it
import sys

# Map integer color indices (expected from the model's state array) to Ursina colors
# Ensure indices 0-5 match the RubiksCube model's color assignment convention
INT_COLOR_MAP = {
    0: color.white,  # Example: U face color
    1: color.yellow, # Example: D face color
    2: color.orange, # Example: L face color
    3: color.red,    # Example: R face color
    4: color.green,  # Example: F face color
    5: color.blue,   # Example: B face color
    -1: color.black # Optional: Color for potential interior pieces if needed
}

class RubiksCubeViewer:
    def __init__(self, cube_model):
        """
        Initializes the viewer for a Rubik's Cube model.

        Args:
            cube_model: An instance of a RubiksCube class expected to have
                        `size` (int) and `state` (n x n x n numpy array) attributes.
        """
        self.cube_model = cube_model
        if not hasattr(cube_model, 'size') or not hasattr(cube_model, 'state'):
            raise AttributeError("cube_model must have 'size' and 'state' attributes.")
        if not isinstance(cube_model.state, np.ndarray) or cube_model.state.ndim != 3:
             raise TypeError("cube_model.state must be a 3D NumPy array.")
        if cube_model.state.shape != (cube_model.size, cube_model.size, cube_model.size):
             raise ValueError(f"cube_model.state shape {cube_model.state.shape} does not match cube_model.size {cube_model.size}.")

        self.parent_entity = Entity(model=None, name="CubeParent")
        # Store facelets keyed by (x, y, z, axis_index, direction)
        # axis_index: 0=X, 1=Y, 2=Z
        # direction: -1 or 1
        self.facelets = {}
        self.backing_pieces = []
        self.create_visualization()
        self.update_colors() # Initial color update

    def create_visualization(self):
        """Creates the Ursina entities representing the Rubik's Cube of size n."""

        # Clear previous visualization if any
        for piece in self.backing_pieces:
            if piece: destroy(piece)
        for facelet in self.facelets.values():
            if facelet: destroy(facelet)
        self.backing_pieces.clear()
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

        # --- Face Info (remains the same) ---
        # Defines visual offset and rotation for facelets based on normal
        face_info = {
            # Normal Vector: {Offset from piece center, Rotation to face outward}
            Vec3(0, 1, 0): {'offset': Vec3(0, 0.501, 0), 'rotation': Vec3(-90, 0, 0), 'axis': 1, 'dir': 1},  # Up (+Y)
            Vec3(0,-1, 0): {'offset': Vec3(0,-0.501, 0), 'rotation': Vec3(90, 0, 0),   'axis': 1, 'dir': -1}, # Down (-Y)
            Vec3(1, 0, 0): {'offset': Vec3(0.501, 0, 0), 'rotation': Vec3(0, 90, 0),   'axis': 0, 'dir': 1},  # Right (+X)
            Vec3(-1,0, 0): {'offset': Vec3(-0.501,0, 0), 'rotation': Vec3(0,-90, 0),  'axis': 0, 'dir': -1}, # Left (-X)
            Vec3(0, 0, 1): {'offset': Vec3(0, 0, 0.501), 'rotation': Vec3(0, 0, 0),    'axis': 2, 'dir': 1},  # Front (+Z)
            Vec3(0, 0,-1): {'offset': Vec3(0, 0,-0.501), 'rotation': Vec3(0, 180, 0), 'axis': 2, 'dir': -1}, # Back (-Z)
        }

        # Iterate through all n*n*n potential cubie positions
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    # Calculate the visual position for this cubie
                    pos_x = x - offset
                    pos_y = y - offset
                    pos_z = z - offset

                    # Determine if this piece is internal (not visible)
                    is_internal = (0 < x < n and 0 < y < n and 0 < z < n)

                    # --- Create the backing piece (optional) ---
                    if not is_internal:
                        piece = Entity(
                            model=piece_model,
                            color=color.dark_gray,
                            position=(pos_x, pos_y, pos_z),
                            scale=piece_scale,
                            parent=self.parent_entity,
                            name=f"piece_{x}_{y}_{z}"
                        )
                        self.backing_pieces.append(piece)

                    # --- Create facelets for visible faces ---
                    for normal, info in face_info.items():
                        # Check if the current (x,y,z) position has an exterior face
                        # corresponding to the current normal vector.
                        is_exterior = False
                        if info['axis'] == 1 and info['dir'] == 1 and y == n: is_exterior = True    # Top face
                        elif info['axis'] == 1 and info['dir'] == -1 and y == 0: is_exterior = True # Bottom face
                        elif info['axis'] == 0 and info['dir'] == 1 and x == n: is_exterior = True  # Right face
                        elif info['axis'] == 0 and info['dir'] == -1 and x == 0: is_exterior = True # Left face
                        elif info['axis'] == 2 and info['dir'] == 1 and z == n: is_exterior = True  # Front face
                        elif info['axis'] == 2 and info['dir'] == -1 and z == 0: is_exterior = True # Back face

                        if is_exterior:
                            try:
                                # Define the key for this facelet based on its model coords and orientation
                                facelet_key = (x, y, z, info['axis'], info['dir'])

                                facelet = Entity(
                                    model=Quad(scale=(0.9, 0.9)),
                                    color=color.light_gray, # Default color
                                    position=Vec3(pos_x, pos_y, pos_z) + info['offset'],
                                    rotation=info['rotation'],
                                    parent=scene,
                                    double_sided=False,
                                    name=f"facelet_{x}_{y}_{z}_{normal.x}_{normal.y}_{normal.z}" # More descriptive name
                                )
                                facelet.world_parent = self.parent_entity
                                self.facelets[facelet_key] = facelet

                            except Exception as e:
                                print(f"Error creating facelet for key {facelet_key}: {e}", file=sys.stderr)

        # Verify facelet count (optional) - Expected: 6 * n * n
        expected_facelets = 6 * size * size
        if len(self.facelets) != expected_facelets:
             print(f"Warning: Created {len(self.facelets)} facelet entities, expected {expected_facelets}.", file=sys.stderr)


    def update_colors(self):
        """Updates facelet colors based on the cube_model's n*n*n state array."""
        try:
            state_array = self.cube_model.state
            if state_array.shape != (self.cube_model.size, self.cube_model.size, self.cube_model.size):
                 print(f"Error: State array shape {state_array.shape} mismatch with size {self.cube_model.size}.", file=sys.stderr)
                 return

            updated_count = 0
            # Iterate through the facelets using the new key structure
            for key, facelet_entity in self.facelets.items():
                if facelet_entity:
                    x, y, z, axis, direction = key
                    try:
                        # Get the color index from the corresponding position in the state array
                        color_index = state_array[x, y, z]
                        # Map the integer index to an Ursina color
                        facelet_entity.color = INT_COLOR_MAP.get(color_index, color.pink) # Pink for errors
                        updated_count += 1
                    except IndexError:
                        print(f"Error: Index out of bounds ({x},{y},{z}) accessing state array.", file=sys.stderr)
                        facelet_entity.color = color.magenta # Magenta for index errors
                    except KeyError:
                        print(f"Error: Color index {color_index} not found in INT_COLOR_MAP.", file=sys.stderr)
                        facelet_entity.color = color.cyan # Cyan for map errors
                    except Exception as e:
                        print(f"Error updating color for facelet {key}: {e}", file=sys.stderr)
                        facelet_entity.color = color.black # Black for other errors

            # Optional: Verify update count
            # expected_facelets = 6 * self.cube_model.size * self.cube_model.size
            # if updated_count != expected_facelets:
            #     print(f"Warning: Updated colors for {updated_count} facelets, expected {expected_facelets}.", file=sys.stderr)

        except Exception as e:
            print(f"General Error in update_colors: {e}", file=sys.stderr)


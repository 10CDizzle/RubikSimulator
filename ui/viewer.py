from ursina import Entity, color

COLOR_MAP = [
    color.red,
    color.green,
    color.blue,
    color.orange,
    color.yellow,
    color.white
]

class RubiksCubeViewer:
    def __init__(self, cube_model):
        self.cube_model = cube_model
        self.parent_entity = Entity()  # <-- Add this
        self.cubes = []
        self.create_visualization()
    
    def create_visualization(self):
        x_offset = (self.cube_model.x - 1) / 2
        y_offset = (self.cube_model.y - 1) / 2
        z_offset = (self.cube_model.z - 1) / 2

        for x in range(self.cube_model.x):
            for y in range(self.cube_model.y):
                for z in range(self.cube_model.z):
                    mini_cube = Entity(
                        model='cube',
                        color=COLOR_MAP[self.cube_model.state[x][y][z]],
                        position=(x - x_offset, y - y_offset, z - z_offset),  # <-- Center it!
                        scale=0.9,
                        parent=self.parent_entity
                    )
                    self.cubes.append(mini_cube)

    
    def update_colors(self):
        for idx, cube in enumerate(self.cubes):
            x = idx // (self.cube_model.y * self.cube_model.z)
            yz = idx % (self.cube_model.y * self.cube_model.z)
            y = yz // self.cube_model.z
            z = yz % self.cube_model.z
            cube.color = COLOR_MAP[self.cube_model.state[x][y][z]]

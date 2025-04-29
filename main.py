from ursina import Ursina, Button, color, mouse, held_keys, time
from cube.cube import RubiksCube
from ui.viewer import RubiksCubeViewer
import time

solve_steps = []
current_step_index = 0
step_timer = 0
step_duration = 0.5  # <-- n seconds per move (you can adjust)
is_solving = False

app = Ursina()

cube_model = RubiksCube(3, 3, 3)
viewer = RubiksCubeViewer(cube_model)

solve_button = Button(text='Solve', color=color.azure, position=(0.7, 0.45), scale=(0.2, 0.1))

def update():
    global is_solving, solve_steps, current_step_index, step_timer

    if solve_button.hovered and mouse.left and not is_solving:
        solve_steps = cube_model.get_solve_steps()
        current_step_index = 0
        step_timer = 0
        is_solving = True

    # --- Animate solving ---
    if is_solving:
        step_timer += time.dt
        if step_timer >= step_duration:
            if current_step_index < len(solve_steps):
                step = solve_steps[current_step_index]
                cube_model.apply_move(step)
                viewer.update_colors()
                current_step_index += 1
                step_timer = 0
            else:
                is_solving = False

    # --- Rotate viewer with WASD ---
    rotation_speed = 40
    dt = time.dt
    if held_keys['a']:
        viewer.parent_entity.rotation_y += rotation_speed * dt
    if held_keys['d']:
        viewer.parent_entity.rotation_y -= rotation_speed * dt
    if held_keys['w']:
        viewer.parent_entity.rotation_x += rotation_speed * dt
    if held_keys['s']:
        viewer.parent_entity.rotation_x -= rotation_speed * dt



app.run()

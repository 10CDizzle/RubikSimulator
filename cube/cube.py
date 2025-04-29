import numpy as np
from cube.solver import simple_solver

class RubiksCube:
    def __init__(self, x, y, z):
        
        self.x, self.y, self.z = x, y, z
        # Randomly initialize the cube: each face gets a color id (0 to 5)
        self.state = np.random.randint(0, 6, size=(x, y, z))
        self.solution_moves = []
    
    def solve(self):
        # Simply call the solver for now
        self.state = simple_solver(self.state)

    def get_solve_steps(self):
    # Just return a copy of the moves
        return self.solution_moves.copy()

    def apply_move(self, move):
        # Apply a single move
        if move in self.solution_moves:
            self.solution_moves.remove(move)
        # You would also update the cube's internal state here if needed
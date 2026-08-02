"""
Generate a valid scrambled cube state by applying random moves to a solved cube.
"""
import random

def apply_move(state, move):
    """Apply a single move to the cube state (URFDLB order, 54 chars)."""
    state = list(state)
    # Move definitions: which stickers cycle
    # Each move is a list of cycles (a, b, c, d) meaning a->b->c->d->a
    moves = {
        'U':  [[0,2,8,6], [1,5,7,3], [9,45,35,27], [10,46,34,28], [11,47,33,29]],
        'D':  [[18,20,26,24], [19,23,25,21], [15,53,39,36], [16,50,38,37], [17,51,44,43]],
        'R':  [[9,11,17,15], [10,14,16,12], [2,53,29,20], [5,52,26,23], [8,51,35,24]],
        'L':  [[36,38,44,42], [37,41,43,39], [0,18,45,27], [3,21,48,30], [6,24,51,33]],
        'F':  [[18,20,26,24], [19,23,25,21], [6,42,35,11], [7,39,32,14], [8,36,29,17]],
        'B':  [[45,47,53,51], [46,50,52,48], [0,27,53,20], [1,30,52,17], [2,33,51,14]],
    }
    
    # Reverse mapping for prime moves
    reverse_moves = {}
    for name, cycles in moves.items():
        reverse_moves[name + "'"] = [[d, c, b, a] for a, b, c, d in cycles]
    
    if move in moves:
        cycles = moves[move]
    elif move in reverse_moves:
        cycles = reverse_moves[move]
    elif move.endswith('2'):
        base = move[0]
        if base in moves:
            # Apply twice
            s = apply_move(''.join(state), base)
            s = apply_move(s, base)
            return s
        return ''.join(state)
    else:
        return ''.join(state)
    
    for cycle in cycles:
        a, b, c, d = cycle
        temp = state[d]
        state[d] = state[c]
        state[c] = state[b]
        state[b] = state[a]
        state[a] = temp
    
    return ''.join(state)

# Start from solved cube
solved = 'U' * 9 + 'R' * 9 + 'F' * 9 + 'D' * 9 + 'L' * 9 + 'B' * 9

# Apply random scramble
random.seed(42)
move_list = ['U', "U'", 'D', "D'", 'R', "R'", 'L', "L'", 'F', "F'", 'B', "B'",
             'U2', 'D2', 'R2', 'L2', 'F2', 'B2']

state = solved
for _ in range(20):
    move = random.choice(move_list)
    state = apply_move(state, move)

print(f"Scrambled state: {state}")
print(f"Length: {len(state)}")

from collections import Counter
counts = Counter(state)
print(f"Color counts: {dict(counts)}")

# Verify with kociemba
try:
    import kociemba
    solution = kociemba.solve(state)
    print(f"Kociemba solution: {solution}")
    print(f"Solution moves: {len(solution.split())}")
except Exception as e:
    print(f"Kociemba error: {e}")

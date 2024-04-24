import json

with open('matrix.json') as f:
    matrix = json.load(f)

with open('passives.json') as f:
    passives = json.load(f)["passives"]

pal_to_int = {pal: i for i, pal in enumerate(matrix.keys())}
int_to_pal = {i: pal for i, pal in enumerate(matrix.keys())}

passives_to_int = {skill: i for i, skill in enumerate(passives)}
int_to_passives = {i: skill for i, skill in enumerate(passives)}

matrix_encoded = {pal_to_int[pal1]: {pal_to_int[pal2]: pal_to_int[child] for pal2, child in row.items()} for pal1, row in matrix.items()}

from __future__ import annotations
from data import pal_to_int, int_to_pal, passives_to_int, int_to_passives

class Pal:
    def __init__(self, 
                 name: str,
                 sex: int,
                 passives=set(),
                 player: str="",
                 parent1: Pal=None,
                 parent2: Pal=None,
                 generation=0
                 ):
        self.name = name
        self.sex = sex
        self.passives = passives
        self.player = player

        self.parent1 = parent1
        self.parent2 = parent2
        self.generation = generation

    def is_done(self):
        return set(self.passives) == set(list(range(4)))

    def get_children(self, other: Pal, matrix) -> Pal:
        if self.sex == other.sex:
            return None
        name = matrix[self.name][other.name]
        passives = self.passives | other.passives
        return [Pal(name, 0, passives, parent1=self, parent2=other, generation=max(self.generation, other.generation) + 1),
                Pal(name, 1, passives, parent1=self, parent2=other, generation=max(self.generation, other.generation) + 1)]

    def get_ancestors(self):
        if self.parent1 is None:
            return {repr(self)}
        return {repr(self): [self.parent1.get_ancestors(), self.parent2.get_ancestors()]}

    def __repr__(self) -> str:
        sex = '♂' if self.sex == 0 else '♀'
        return f'{int_to_pal[self.name]} ({sex}, {", ".join([int_to_passives[skill] for skill in self.passives])}, {self.generation}, {self.player})'

    def __hash__(self) -> int:
        return hash(self.name) ^ hash(self.sex) ^ hash(self.passives)
    
    def __eq__(self, other: Pal) -> bool:
        return isinstance(other, Pal) \
                and self.name == other.name \
                and self.sex == other.sex \
                and self.passives == other.passives
    
    def is_equivalent(self, other: Pal) -> bool:
        return isinstance(other, Pal) \
                and self.name == other.name \
                and self.passives == other.passives

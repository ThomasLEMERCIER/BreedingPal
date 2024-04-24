from tqdm import tqdm

from utils import Pal

from data import int_to_passives


def search(target: str, sources: list[Pal], matrix: dict[str, dict[str, str]]):
    pool = sources.copy()
    seen = set([p for p in sources])
    while True:
        new_pool = []
        for i, p1 in tqdm(enumerate(pool)):
            for p2 in pool[i + 1:]:
                children = p1.get_children(p2, matrix)
                if children is not None:
                    for child in children:
                        if child in seen:
                            continue
                        seen.add(child)
                        if child.name == target and child.is_done():
                            return child
                        new_pool.append(child)
        pool = new_pool + pool
        if len(new_pool) == 0:
            print(f'No solution found for {target} with {sources} as sources')
            return None

def filter_sources(target: Pal, sources: list[Pal]):
    return list(filter(lambda p: p.passives.issubset(target.passives), sources))

def check_possibility(target: Pal, sources: list[Pal]):
    skill_found = [False for _ in range(len(target.passives))]
    for source in sources:
        for i, skill in enumerate(target.passives):
            if skill in source.passives:
                skill_found[i] = True
        if all(skill_found):
            return True, skill_found
    return False, skill_found

def search_depth(target: Pal, sources: list[Pal], matrix: dict[str, dict[str, str]], max_depth: int):
    pool = sources.copy()
    seen = set([p for p in sources])
    for depth in range(max_depth):
        pool = filter_sources(target, pool)
        if len(pool) == 0:
            print(f'No solution found for {target}')
            return None
        possible, skill_found = check_possibility(target, pool)
        if not possible:
            print(f'No solution can be found for {target} without the following skills: {[int_to_passives[skill] for i, skill in enumerate(target.passives) if not skill_found[i]]}')
            return None
        print(f'Searching depth {depth+1}: {len(pool)} pals in pool')
        next_pool = []
        for i, p1 in enumerate(pool):
            for j, p2 in enumerate(pool[i + 1:]):
                print(f"Checking {i * len(pool) + j} / {len(pool) * (len(pool) - 1) / 2}", end='\r')
                children = p1.get_children(p2, matrix)
                if children is not None:
                    for child in children:
                        if child.is_equivalent(target):
                            return child
                        if child not in seen:
                            next_pool.append(child)
                            seen.add(child)
        pool = pool + next_pool

    print(f'No solution found for {target}')
    return None

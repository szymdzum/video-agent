"""Shot-rating calibration (idea from ride-recap's label/compare loop, MIT (c) 2026 Ian Macomber).
Ratings live in <project>/edit/ratings.json:
  [{"src": "za_lodka.MP4", "from": 10, "to": 35, "model": {"light":6,"composition":7,"motion":5,"scenery":8,"subject":8,
    "stars":4, "note":"..."}, "user": {"stars": 3, "note": "trzęsie na początku"}}]

Usage:
  ratings.py ask ratings.json [N]   -> prints N unrated-by-user stretches (spread across model stars) for him to rate
  ratings.py compare ratings.json   -> agreement stats + every disagreement of >= 2 stars (turn each into a rule)
"""
import json, sys

AXES = ('light', 'composition', 'motion', 'scenery', 'subject')


def load(p): return json.load(open(p))


def ask(items, n):
    todo = [i for i in items if not (i.get('user') or {}).get('stars')]
    todo.sort(key=lambda i: (i.get('model') or {}).get('stars', 0))
    step = max(1, len(todo) // max(1, n))  # spread across the model's star range, low to high
    for i in todo[::step][:n]:
        m = i.get('model') or {}
        print(f"  {i['src']} {i['from']}-{i['to']} s   (model ★{m.get('stars','?')}: {m.get('note','')})")


def compare(items):
    both = [i for i in items if (i.get('user') or {}).get('stars') and (i.get('model') or {}).get('stars')]
    if not both: print('no stretches rated by both yet'); return
    d = [i['model']['stars'] - i['user']['stars'] for i in both]
    exact = sum(x == 0 for x in d); near = sum(abs(x) <= 1 for x in d)
    print(f"{len(both)} rated by both: exact {exact}, within 1★ {near}, mean model-user {sum(d)/len(d):+.2f}★")
    for i, x in sorted(zip(both, d), key=lambda t: -abs(t[1])):
        if abs(x) >= 2:
            m = i['model']
            print(f"  {x:+d}★  {i['src']} {i['from']}-{i['to']}: model ★{m['stars']} "
                  f"({', '.join(f'{a[:4]} {m.get(a)}' for a in AXES if a in m)}) vs his ★{i['user']['stars']}"
                  f" \"{i['user'].get('note','')}\"  -> write a rule")


if __name__ == '__main__':
    cmd, path = sys.argv[1], sys.argv[2]
    items = load(path)
    ask(items, int(sys.argv[3]) if len(sys.argv) > 3 else 8) if cmd == 'ask' else compare(items)

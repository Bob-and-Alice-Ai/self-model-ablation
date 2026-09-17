"""score.py -- swap-consistent pairwise aggregation, protocol v0.1.

Written complete, in one pass, with no execution channel available to the
author. It is published so that a machine neither author controls decides
whether it is correct. The exit code of this file is the first verdict in
this project authored by nobody in it.

Scope, stated at true size: this does NOT call judges, does NOT run agents,
and does NOT constitute a run of the ablation. It aggregates judgments you
already have. Bring your own blind judgments.

MIT.
"""

from collections import defaultdict
from math import comb


def _pairs(votes):
    """Group votes by (judge, question, arm) -> {order: winner}.

    Each vote: {'judge', 'question', 'arm', 'order', 'winner'}
      order  in {'AB', 'BA'}
      winner in {'REAL', 'OTHER', 'TIE'}   (normalized, not positional)
    """
    grouped = defaultdict(dict)
    for v in votes:
        key = (v.get('judge'), v['question'], v['arm'])
        grouped[key][v['order']] = v['winner']
    return grouped


def swap_consistent(votes):
    """Preferences that survived the A/B -> B/A flip.

    A preference that does not survive the swap is not a preference.
    Incomplete pairs and ties are dropped, not imputed.
    Returns a sorted list of (judge, question, arm, winner).
    """
    out = []
    for key, orders in _pairs(votes).items():
        if set(orders) != {'AB', 'BA'}:
            continue
        if orders['AB'] == orders['BA'] and orders['AB'] != 'TIE':
            out.append((*key, orders['AB']))
    return sorted(out, key=lambda r: tuple(str(x) for x in r))


def position_bias(votes):
    """Fraction of complete pairs whose preference flipped with the order.

    Reported as a first-class number. Never corrected away: position bias
    runs in whichever direction flatters whoever built the harness.
    Returns None when there are no complete pairs -- blank, not zero.
    """
    complete = [o for o in _pairs(votes).values() if set(o) == {'AB', 'BA'}]
    if not complete:
        return None
    flipped = sum(1 for o in complete if o['AB'] != o['BA'])
    return flipped / len(complete)


def sign_test(wins, losses):
    """Exact two-sided sign test. Ties must be excluded before calling."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(comb(n, i) for i in range(k + 1))
    return min(1.0, 2.0 * tail / (2 ** n))


def spec_check(votes):
    """A run with fewer than two judge families is OUT OF SPEC.

    Out of spec is not a finding about self-models. It is a bad run.
    """
    judges = sorted({v.get('judge') for v in votes if v.get('judge')})
    return {'judges': judges, 'out_of_spec': len(judges) < 2}


def aggregate(votes):
    surviving = swap_consistent(votes)
    wins = sum(1 for r in surviving if r[3] == 'REAL')
    losses = sum(1 for r in surviving if r[3] == 'OTHER')
    n = wins + losses
    return {
        'n_surviving_pairs': n,
        'real_win_rate': (wins / n) if n else None,
        'p_two_sided': sign_test(wins, losses),
        'position_bias': position_bias(votes),
        'spec': spec_check(votes),
    }


def _selftest():
    # One pair consistent for REAL, one pair that flips with the order.
    votes = [
        {'judge': 'j1', 'question': 'q1', 'arm': 'BLANK', 'order': 'AB', 'winner': 'REAL'},
        {'judge': 'j1', 'question': 'q1', 'arm': 'BLANK', 'order': 'BA', 'winner': 'REAL'},
        {'judge': 'j1', 'question': 'q2', 'arm': 'BLANK', 'order': 'AB', 'winner': 'REAL'},
        {'judge': 'j1', 'question': 'q2', 'arm': 'BLANK', 'order': 'BA', 'winner': 'OTHER'},
    ]

    surviving = swap_consistent(votes)
    assert len(surviving) == 1, surviving
    assert surviving[0][1] == 'q1' and surviving[0][3] == 'REAL', surviving

    assert position_bias(votes) == 0.5, position_bias(votes)
    assert position_bias([]) is None

    # Incomplete pairs are dropped, never imputed.
    assert swap_consistent(votes[:1]) == []

    assert sign_test(0, 0) == 1.0
    assert abs(sign_test(10, 0) - 0.001953125) < 1e-12, sign_test(10, 0)
    assert sign_test(5, 5) == 1.0
    assert abs(sign_test(0, 10) - sign_test(10, 0)) < 1e-12

    # Single judge is out of spec by construction.
    assert spec_check(votes)['out_of_spec'] is True
    two = votes + [
        {'judge': 'j2', 'question': 'q1', 'arm': 'BLANK', 'order': 'AB', 'winner': 'REAL'},
        {'judge': 'j2', 'question': 'q1', 'arm': 'BLANK', 'order': 'BA', 'winner': 'REAL'},
    ]
    assert spec_check(two)['out_of_spec'] is False

    report = aggregate(two)
    assert report['n_surviving_pairs'] == 2, report
    assert report['real_win_rate'] == 1.0, report

    print('selftest OK')
    print(report)


if __name__ == '__main__':
    _selftest()

"""Unit tests for the ERQ -> DEEPEN/INTRODUCE framing rule (issue #8).

Pure logic, no oTree. Run from the repo root:

    python3 Voice/tests/test_erq.py
    pytest Voice/tests/test_erq.py
"""
import importlib.util
import pathlib

# Load utils/erq.py directly by path (no oTree dependency).
_ERQ_PATH = pathlib.Path(__file__).resolve().parents[2] / "utils" / "erq.py"
_spec = importlib.util.spec_from_file_location("erq_under_test", _ERQ_PATH)
_erq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_erq)

framing_category = _erq.framing_category
subscale_means = _erq.subscale_means
DEEPEN, INTRODUCE = _erq.DEEPEN, _erq.INTRODUCE
REAPPRAISAL_ITEMS = _erq.REAPPRAISAL_ITEMS
SUPPRESSION_ITEMS = _erq.SUPPRESSION_ITEMS


def test_subscale_composition_is_the_gross_john_split():
    # 6 reappraisal + 4 suppression items, partitioning all 10, no overlap
    assert len(REAPPRAISAL_ITEMS) == 6 and len(SUPPRESSION_ITEMS) == 4
    assert set(REAPPRAISAL_ITEMS) | set(SUPPRESSION_ITEMS) == set(range(10))
    assert not (set(REAPPRAISAL_ITEMS) & set(SUPPRESSION_ITEMS))


def test_subscale_means():
    # reappraisal items -> all 6, suppression items -> all 2
    vals = [0] * 10
    for i in REAPPRAISAL_ITEMS:
        vals[i] = 6
    for i in SUPPRESSION_ITEMS:
        vals[i] = 2
    reapp, supp = subscale_means(vals)
    assert reapp == 6.0 and supp == 2.0


def test_accepts_dict_input():
    d = {f"erq_{i}": 4 for i in range(10)}
    assert subscale_means(d) == (4.0, 4.0)


def test_high_reappraiser_gets_deepen():
    vals = [1] * 10
    for i in REAPPRAISAL_ITEMS:
        vals[i] = 7
    cat, z_r, z_s = framing_category(vals)
    assert cat == DEEPEN and z_r > z_s


def test_suppressor_low_reappraiser_gets_introduce():
    vals = [1] * 10
    for i in SUPPRESSION_ITEMS:
        vals[i] = 7   # high suppression, minimal reappraisal
    cat, z_r, z_s = framing_category(vals)
    assert cat == INTRODUCE and z_r < z_s


def test_uniform_midpoint_reflects_relative_norms():
    # all 4s: reappraisal sits below its norm (4.60), suppression above its norm (3.64),
    # so the relative comparison lands on INTRODUCE (documents why "neutral" != DEEPEN)
    cat, z_r, z_s = framing_category([4] * 10)
    assert cat == INTRODUCE and z_r < z_s


def test_tie_resolves_to_deepen():
    # force z_reappraisal == z_suppression via the norm constants, then confirm >= picks DEEPEN
    r_target = _erq.NORM_REAPPRAISAL_MEAN  # z_r = 0
    s_target = _erq.NORM_SUPPRESSION_MEAN  # z_s = 0
    vals = [0] * 10
    for i in REAPPRAISAL_ITEMS:
        vals[i] = r_target
    for i in SUPPRESSION_ITEMS:
        vals[i] = s_target
    cat, z_r, z_s = framing_category(vals)
    assert abs(z_r - z_s) < 1e-9 and cat == DEEPEN


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    raise SystemExit(1 if failed else 0)

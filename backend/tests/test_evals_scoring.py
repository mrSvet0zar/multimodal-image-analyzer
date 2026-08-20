"""Unit tests for eval scoring logic (no API calls)."""

from evals.cases import CASES, EvalCase
from evals.run_evals import score_case


def _draw(_):
    pass


def test_perfect_score():
    case = EvalCase("t", _draw, expected_text="hello", expected_keywords=["red", "circle"])
    analysis = {
        "description": "A red circle",
        "tags": ["circle", "geometry"],
        "objects": [{"name": "red shape"}],
        "extracted_text": "HELLO there",
    }
    score, failures = score_case(case, analysis)
    assert score == 1.0
    assert failures == []


def test_partial_score_and_failures():
    case = EvalCase("t", _draw, expected_text="stop", expected_keywords=["blue", "square"])
    analysis = {
        "description": "A blue shape",
        "tags": [],
        "objects": [],
        "extracted_text": "",
    }
    score, failures = score_case(case, analysis)
    # blue matches; text 'stop' and 'square' fail -> 1/3
    assert round(score, 3) == round(1 / 3, 3)
    assert "text~'stop'" in failures
    assert "kw:square" in failures


def test_keywords_only_case():
    case = EvalCase("t", _draw, expected_text=None, expected_keywords=["green"])
    assert score_case(case, {"description": "green triangle"})[0] == 1.0
    assert score_case(case, {"description": "blue"})[0] == 0.0


def test_dataset_is_well_formed():
    assert len(CASES) >= 5
    for case in CASES:
        assert case.id
        assert case.image_bytes()[:2] == b"\xff\xd8"  # valid JPEG magic

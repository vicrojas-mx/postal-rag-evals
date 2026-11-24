import pytest
from tests.evals.retrieval_eval import matches

@pytest.mark.parametrize("expected, retrieved, expected_metrics", [
    pytest.param(["7-1.2", "7-14.2"],  ["a", "7-14.2", "b", "7-1.2"], (1, 1.0, 2), id="All expected found"),
    pytest.param(["7-14.2", "7-1.2"],  ["a", "7-14.2", "b", "7-1.2"], (1, 1.0, 2), id="All expected found swapped"),
    pytest.param(["14-6"],  ["14-6.1"], (1, 1.0, 1), id="Family Rule"),
    pytest.param(["14-6.1"],  ["14-6"], (0, 0.0, None), id="Family Rule Swap"),
    pytest.param(["1-40"],  ["1-4"], (0, 0.0, None), id="Not found"),
    pytest.param(["7-1.2", "7-14.2"],  ["a", "7-14.2", "b", "7-6.2"], (1, 0.5   , 2), id="One found"),
])
def test_matches_retrieved_vs_expected(expected, retrieved, expected_metrics):
    assert matches(retrieved, expected) == expected_metrics

import pytest

from each.prediction import predict_timing


@pytest.mark.parametrize("parallelism", [1, 4, 10])
@pytest.mark.parametrize("remaining", [1, 10, 100, 1000])
@pytest.mark.parametrize("seed", [0, 384139841])
def test_predictions_based_on_constant_data_are_fairly_consistent(parallelism, remaining, seed):
    prediction = predict_timing([1], parallelism, remaining, seed=seed)
    actual = remaining / parallelism

    assert prediction.mean != actual
    assert prediction.percentile(1) * 0.1 <= actual <= prediction.percentile(99) * 10
    assert prediction.percentile(1) * 0.1 <= prediction.mean <= prediction.percentile(99) * 10

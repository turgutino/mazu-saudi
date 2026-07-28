import numpy as np
import torch

from mazu_saudi.mcr_precip.real_data import (
    ChannelStats,
    PreparedProxyData,
    SplitIndices,
)
from mazu_saudi.mcr_precip.real_experiment import (
    NeuralExperimentConfig,
    apply_platt_calibrator,
    evaluate_neural_variant,
    fit_platt_calibrator,
    train_neural_variant,
)


def _tiny_data():
    generator = torch.Generator().manual_seed(4)
    n, height, width = 9, 5, 6
    dynamic = torch.randn(n, 1, 4, height, width, generator=generator)
    occurrence = (dynamic[:, :, :1].squeeze(2) > 0.8).float()
    return PreparedProxyData(
        dynamic=dynamic,
        static=torch.zeros(1, 1, height, width),
        mechanism=torch.rand(n, 8, generator=generator),
        availability=torch.ones(n, 3),
        occurrence=occurrence,
        rainfall=torch.zeros(n, 1, height, width),
        lead_hours=torch.full((n,), 24, dtype=torch.long),
        valid_dates=np.array([f"2025-01-{day:02d}" for day in range(2, 11)]),
        input_dates=np.array([f"2025-01-{day:02d}" for day in range(1, 10)]),
        split=SplitIndices(np.array([0, 1, 2, 3, 4]), np.array([5, 6]), np.array([7, 8])),
        feature_names=("a", "b", "c", "d"),
        channel_stats=ChannelStats(np.zeros(2), np.zeros(2), np.ones(2)),
        terrain_available=False,
    )


def test_real_neural_experiment_smoke_uses_validation_threshold():
    data = _tiny_data()
    model, training = train_neural_variant(
        data,
        constrained=True,
        seed=3,
        config=NeuralExperimentConfig(
            hidden_channels=4,
            epochs=1,
            patience=1,
            batch_days=2,
        ),
    )
    result = evaluate_neural_variant(model, data, batch_days=2)
    assert training["epochs_ran"] == 1
    assert result["threshold_source"] == "validation"
    assert result["calibration"]["method"] == "platt-validation"
    assert 0 < result["threshold"] < 1
    assert result["parameters"] > 0


def test_platt_calibration_is_fit_only_from_explicit_arrays():
    y = np.array([0, 0, 0, 1, 1, 1])
    raw = np.array([0.4, 0.6, 0.7, 0.75, 0.85, 0.95])
    parameters = fit_platt_calibrator(y, raw)
    calibrated = apply_platt_calibrator(raw, parameters)
    assert parameters["input_scale"] > 0
    assert np.isfinite(calibrated).all()
    assert ((calibrated > 0) & (calibrated < 1)).all()
    assert np.all(np.diff(calibrated) >= 0)

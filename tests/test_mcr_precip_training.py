from datetime import datetime, timezone

import torch

from mazu_saudi.mcr_precip.model import MCRPrecip, MCRPrecipConfig
from mazu_saudi.mcr_precip.synthetic import make_synthetic_batch
from mazu_saudi.mcr_precip.training import load_bundle, predict, save_bundle, train_step


def test_train_step_updates_model_and_is_finite():
    torch.manual_seed(5)
    batch, prior = make_synthetic_batch(batch_size=3, height=8, width=8)
    model = MCRPrecip(MCRPrecipConfig(5, 2, hidden_channels=8))
    before = model.occurrence_head.weight.detach().clone()
    metrics = train_step(model, batch, torch.optim.Adam(model.parameters(), lr=1e-3), routing_prior=prior)
    assert all(torch.isfinite(torch.tensor(value)) for value in metrics.values())
    assert not torch.equal(before, model.occurrence_head.weight)


def test_model_bundle_round_trip_preserves_predictions(tmp_path):
    batch, _ = make_synthetic_batch(batch_size=2, height=8, width=8)
    model = MCRPrecip(MCRPrecipConfig(5, 2, hidden_channels=8))
    before = predict(model, batch)
    path = tmp_path / "model.pt"
    metadata = {"source_version": "test-v1", "feature_contract": "mcr-precip-v1", "created_at": datetime.now(timezone.utc).isoformat()}
    save_bundle(path, model, metadata)
    restored, restored_metadata = load_bundle(path)
    after = predict(restored, batch)
    assert restored_metadata == metadata
    for key in before:
        assert torch.allclose(before[key], after[key])

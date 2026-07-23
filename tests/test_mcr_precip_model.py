import inspect

import torch

from mazu_saudi.mcr_precip.model import MCRPrecip, MCRPrecipConfig
from mazu_saudi.mcr_precip.synthetic import make_synthetic_batch


def _model_and_batch(batch_size=4):
    batch, _ = make_synthetic_batch(batch_size=batch_size, height=8, width=9)
    model = MCRPrecip(MCRPrecipConfig(5, 2, hidden_channels=8))
    return model, batch


def test_forward_outputs_probabilistic_contract_and_monotone_quantiles():
    model, batch = _model_and_batch()
    output = model(batch)
    assert output.occurrence_logits.shape == (4, 1, 8, 9)
    assert output.quantiles.shape == (4, 3, 8, 9)
    assert output.expert_features.shape == (4, 4, 8, 8, 9)
    assert torch.allclose(output.router_weights.sum(1), torch.ones(4), atol=1e-6)
    assert (output.quantiles[:, 1:] >= output.quantiles[:, :-1]).all()
    assert (output.uncertainty > 0).all()


def test_missing_terrain_suppresses_orographic_expert():
    model, batch = _model_and_batch()
    batch.availability[:, 2] = 0
    weights = model(batch).router_weights
    assert (weights[:, 2] < 1e-4).all()
    assert torch.allclose(weights.sum(1), torch.ones(4), atol=1e-6)


def test_all_experts_receive_gradient_and_region_id_is_not_an_input():
    model, batch = _model_and_batch()
    model(batch).occurrence_logits.mean().backward()
    for expert in model.experts:
        assert any(parameter.grad is not None for parameter in expert.parameters())
    assert "region" not in inspect.signature(model.forward).parameters


def test_wind_rotation_changes_advection_feature():
    model, batch = _model_and_batch(batch_size=2)
    base = model(batch).expert_features[:, 0]
    batch.mechanism[:, :2] = batch.mechanism[:, [1, 0]]
    rotated = model(batch).expert_features[:, 0]
    assert not torch.allclose(base, rotated)

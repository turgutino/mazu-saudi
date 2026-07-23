import torch

from mazu_saudi.mcr_precip.losses import directional_counterfactual_loss, pinball_loss, routing_kl


def test_pinball_loss_is_zero_at_target():
    target = torch.ones(2, 1, 3, 3)
    prediction = target.expand(2, 3, 3, 3).clone()
    assert pinball_loss(prediction, target, (0.1, 0.5, 0.9)).item() == 0


def test_routing_kl_is_zero_for_matching_distributions():
    weights = torch.tensor([[0.1, 0.2, 0.3, 0.4]])
    assert abs(routing_kl(weights, weights).item()) < 1e-7


def test_counterfactual_directional_constraint():
    base = torch.tensor([[0.5, 0.2, 0.2, 0.1]])
    valid = torch.tensor([[0.3, 0.3, 0.3, 0.1]])
    invalid = torch.tensor([[0.7, 0.1, 0.1, 0.1]])
    assert directional_counterfactual_loss(base, valid, 0).item() == 0
    assert directional_counterfactual_loss(base, invalid, 0).item() > 0

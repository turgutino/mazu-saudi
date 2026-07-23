import pytest
import torch

from mazu_saudi.mcr_precip.synthetic import make_synthetic_batch


def test_synthetic_batch_satisfies_contract():
    batch, _ = make_synthetic_batch(batch_size=3)
    batch.validate(mechanism_dim=8, availability_dim=3)
    assert tuple(batch.lead_hours.tolist()) == (1, 3, 6)


def test_contract_rejects_noncausal_lead_and_nan_inputs():
    batch, _ = make_synthetic_batch(batch_size=2)
    batch.lead_hours[0] = 24
    with pytest.raises(ValueError, match="1, 3, or 6"):
        batch.validate(8, 3)
    batch.lead_hours[0] = 1
    batch.dynamic[0, 0, 0, 0, 0] = torch.nan
    with pytest.raises(ValueError, match="finite"):
        batch.validate(8, 3)

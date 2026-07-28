"""Training and evaluation for the bounded 2025 Saudi proxy comparison."""

from copy import deepcopy
from dataclasses import dataclass
import time

import numpy as np
import torch

from .evaluation import binary_metrics, select_csi_threshold
from .losses import LossConfig, total_loss
from .model import MCRPrecip, MCRPrecipConfig
from .real_data import PreparedProxyData, routing_priors


@dataclass(frozen=True)
class NeuralExperimentConfig:
    hidden_channels: int = 8
    epochs: int = 20
    patience: int = 4
    batch_days: int = 4
    learning_rate: float = 2e-3
    prior_weight: float = 0.1


def _observable_flat(target: torch.Tensor, probability: np.ndarray):
    y = target.detach().cpu().numpy().reshape(-1)
    p = np.asarray(probability).reshape(-1)
    valid = np.isfinite(y) & np.isfinite(p)
    return y[valid], p[valid]


@torch.no_grad()
def predict_indices(
    model: MCRPrecip,
    data: PreparedProxyData,
    indices: np.ndarray,
    batch_days: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    probabilities = []
    targets = []
    for start in range(0, len(indices), batch_days):
        selected = indices[start : start + batch_days]
        batch = data.batch(selected).to(device)
        probabilities.append(model(batch).occurrence_probability.cpu().numpy())
        targets.append(batch.occurrence.cpu().numpy())
    return np.concatenate(targets), np.concatenate(probabilities)


def train_neural_variant(
    data: PreparedProxyData,
    constrained: bool,
    seed: int,
    config: NeuralExperimentConfig = NeuralExperimentConfig(),
    device: str | torch.device = "cpu",
) -> tuple[MCRPrecip, dict]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    target_device = torch.device(device)
    model = MCRPrecip(
        MCRPrecipConfig(
            dynamic_channels=data.dynamic.shape[2],
            static_channels=data.static.shape[1],
            hidden_channels=config.hidden_channels,
        )
    ).to(target_device)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.learning_rate, weight_decay=1e-5
    )
    train_target = data.occurrence[data.split.train]
    positives = torch.nansum(train_target).item()
    observed = torch.isfinite(train_target).sum().item()
    negatives = observed - positives
    pos_weight = negatives / max(positives, 1.0)
    loss_config = LossConfig(
        quantile_weight=0.0,
        prior_weight=config.prior_weight if constrained else 0.0,
        counterfactual_weight=0.0,
        pos_weight=pos_weight,
    )

    best_score = -np.inf
    best_state = None
    bad_epochs = 0
    train_indices = data.split.train.copy()
    history = []
    for epoch in range(1, config.epochs + 1):
        np.random.shuffle(train_indices)
        model.train()
        epoch_loss = 0.0
        seen = 0
        for start in range(0, len(train_indices), config.batch_days):
            selected = train_indices[start : start + config.batch_days]
            batch = data.batch(selected).to(target_device)
            optimizer.zero_grad(set_to_none=True)
            output = model(batch)
            prior = routing_priors(data, selected).to(target_device) if constrained else None
            loss, _ = total_loss(
                output,
                batch,
                model.config.quantile_levels,
                config=loss_config,
                routing_prior=prior,
            )
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite real-data training loss")
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach()) * len(selected)
            seen += len(selected)

        val_y_tensor, val_probability = predict_indices(
            model, data, data.split.validation, config.batch_days, target_device
        )
        val_y, val_p = _observable_flat(torch.from_numpy(val_y_tensor), val_probability)
        val_metrics = binary_metrics(val_y, val_p)
        score = val_metrics["pr_auc"]
        history.append(
            {"epoch": epoch, "loss": epoch_loss / max(seen, 1), "validation_pr_auc": score}
        )
        if score > best_score:
            best_score = score
            best_state = deepcopy(model.state_dict())
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= config.patience:
                break
    if best_state is None:
        raise RuntimeError("training produced no valid validation checkpoint")
    model.load_state_dict(best_state)
    return model, {
        "seed": seed,
        "constrained": constrained,
        "best_validation_pr_auc": float(best_score),
        "epochs_ran": len(history),
        "history": history,
        "pos_weight": float(pos_weight),
    }


def evaluate_neural_variant(
    model: MCRPrecip,
    data: PreparedProxyData,
    batch_days: int = 4,
    device: str | torch.device = "cpu",
) -> dict:
    target_device = torch.device(device)
    val_target, val_probability = predict_indices(
        model, data, data.split.validation, batch_days, target_device
    )
    val_y, val_p = _observable_flat(torch.from_numpy(val_target), val_probability)
    threshold, validation_metrics = select_csi_threshold(val_y, val_p)

    start = time.perf_counter()
    test_target, test_probability = predict_indices(
        model, data, data.split.test, batch_days, target_device
    )
    elapsed = time.perf_counter() - start
    test_y, test_p = _observable_flat(torch.from_numpy(test_target), test_probability)
    return {
        "threshold_source": "validation",
        "threshold": float(threshold),
        "validation": validation_metrics,
        "test": binary_metrics(test_y, test_p, threshold=threshold),
        "test_observations": int(test_y.size),
        "test_positive_rate": float(test_y.mean()),
        "parameters": int(sum(parameter.numel() for parameter in model.parameters())),
        "cpu_inference_seconds": float(elapsed),
        "cpu_microseconds_per_grid_cell": float(elapsed * 1e6 / max(test_y.size, 1)),
    }

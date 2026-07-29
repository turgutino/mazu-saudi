import numpy as np

from mazu_saudi.indicator_definitions import (
    DEFAULT_IVT_LEVELS_HPA,
    INDICATOR_FORMULA_VERSION,
    integrate_ivt,
    precipitation_rate_to_amount,
    rolling_precipitation_amount_max,
    vapor_pressure_deficit_kpa,
    wind_speed,
)


def test_canonical_formula_contract_is_versioned_and_uses_six_ivt_levels():
    assert INDICATOR_FORMULA_VERSION == "1.0.0"
    assert DEFAULT_IVT_LEVELS_HPA == (1000, 925, 850, 700, 500, 300)


def test_shared_vector_and_vpd_formulas_accept_numpy_arrays():
    assert wind_speed(np.array([3.0]), np.array([4.0]))[0] == 5.0
    vpd = vapor_pressure_deficit_kpa(np.array([30.0]), np.array([50.0]))
    assert 2.0 < vpd[0] < 2.2


def test_shared_ivt_returns_components_and_magnitude():
    levels = (1000, 850, 700)
    humidity = {level: np.array([0.01]) for level in levels}
    zonal = {level: np.array([10.0]) for level in levels}
    meridional = {level: np.array([0.0]) for level in levels}

    ivt_u, ivt_v, magnitude = integrate_ivt(
        humidity,
        zonal,
        meridional,
        levels,
    )

    np.testing.assert_allclose(ivt_u, magnitude)
    np.testing.assert_array_equal(ivt_v, np.array([0.0]))


def test_shared_fymerg_formula_integrates_half_hour_rates_as_amounts():
    rates = np.array([[[1.0]], [[3.0]]])

    np.testing.assert_array_equal(
        precipitation_rate_to_amount(rates),
        np.array([[[0.5]], [[1.5]]]),
    )
    np.testing.assert_array_equal(
        rolling_precipitation_amount_max(rates, 2),
        np.array([[2.0]]),
    )

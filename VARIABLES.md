# DS1 Variable Guide — Saudi Arabia Extreme Weather

CMA DS1 dataset contains 35 surface variables for June 2025.
Region: 16-32°N, 34-56°E | Resolution: 0.1° (~10 km)

---

## Flash Flood Variables (Priority: HIGH)

| Variable | Full Name | Unit | Relevance |
|----------|-----------|------|-----------|
| `prate` | Precipitation rate | kg/m²/s | **Core flash flood indicator** — total precipitation intensity |
| `cpr` | Convective precipitation rate | kg/m²/s | **ARST mechanism** — convective rain from Red Sea Trough |
| `crain` | Categorical rain | code | Rain yes/no classification |
| `cfrzr` | Categorical freezing rain | code | Freezing rain indicator |

**For Jeddah flash flood prediction:**
- `prate` > 0.01 kg/m²/s = significant rainfall event
- `cpr` / `prate` ratio > 0.7 = convective (flash flood risk)

---

## Extreme Heat Variables (Priority: HIGH)

| Variable | Full Name | Unit | Relevance |
|----------|-----------|------|-----------|
| `avg_slhtf` | Surface latent heat flux | W/m² | Evaporation cooling — lower = hotter, drier conditions |
| `avg_ishf` | Surface sensible heat flux | W/m² | **Direct heat stress indicator** — heat transferred to air |
| `gflux` | Ground heat flux | W/m² | Soil heat storage — drives nocturnal heat retention |
| `sdswrf` | Surface downward shortwave radiation | W/m² | **Solar heating** — main driver of extreme heat |
| `sulwrf` | Surface upward longwave radiation | W/m² | Surface thermal emission — relates to land surface temperature |
| `sdlwrf` | Surface downward longwave radiation | W/m² | Greenhouse trapping — higher = stronger heat retention |
| `avg_al` | Forecast albedo | % | Surface reflectivity — desert sand has high albedo |

**Extreme heat index:**
- High `sdswrf` + low `avg_slhtf` + high `avg_ishf` = extreme heat day

---

## Wind Variables (Priority: MEDIUM)

| Variable | Full Name | Unit | Relevance |
|----------|-----------|------|-----------|
| `avg_utaua` | U-component surface momentum flux | N/m² | East-west wind stress — Red Sea wind patterns |
| `avg_vtaua` | V-component surface momentum flux | N/m² | North-south wind stress — monsoon circulation |
| `iegwss` | Eastward gravity wave surface stress | N/m² | Mountain wave effects (Hejaz mountains) |
| `ingwss` | Northward gravity wave surface stress | N/m² | Orographic effects on precipitation |

---

## Radiation Budget Variables (Priority: MEDIUM)

| Variable | Full Name | Unit | Relevance |
|----------|-----------|------|-----------|
| `suswrf` | Surface upward shortwave radiation | W/m² | Reflected solar radiation |
| `csdsf` | Clear sky downward solar flux | W/m² | Solar input without clouds |
| `csusf` | Clear sky upward solar flux | W/m² | Reflected solar (clear sky) |
| `csdlf` | Clear sky downward longwave flux | W/m² | Greenhouse under clear sky |
| `csulf` | Clear sky upward longwave flux | W/m² | Surface emission (clear sky) |
| `vbdsf` | Visible beam downward solar flux | W/m² | Direct sunlight component |
| `vddsf` | Visible diffuse downward solar flux | W/m² | Scattered sunlight |
| `nbdsf` | Near IR beam downward solar flux | W/m² | Near-infrared direct |
| `nddsf` | Near IR diffuse downward solar flux | W/m² | Near-infrared scattered |
| `duvb` | UV-B downward solar flux | W/m² | UV radiation — health impact |
| `cduvb` | Clear sky UV-B downward solar flux | W/m² | UV under clear sky |

---

## Low Priority for Saudi Arabia

| Variable | Full Name | Unit | Why Low Priority |
|----------|-----------|------|-----------------|
| `snowc` | Snow cover | % | No snow in Saudi Arabia |
| `evcw` | Canopy water evaporation | W/m² | Minimal vegetation |
| `evbs` | Direct evaporation from bare soil | W/m² | Useful for drought monitoring |
| `trans` | Transpiration | W/m² | Minimal vegetation |
| `sbsno` | Sublimation from snow | W/m² | No snow |
| `csnow` | Categorical snow | code | No snow |
| `cicep` | Categorical ice pellets | code | Not applicable |
| `snohf` | Snow phase change heat flux | W/m² | No snow |
| `unknown` | Unknown | unknown | Unidentified variable |

---

## Recommended Variable Set for Analysis

### Flash Flood Model (Xu Xiaoke):
```
prate, cpr, crain, avg_utaua, avg_vtaua
```

### Extreme Heat Model (Xu Xiaoke):
```
sdswrf, avg_ishf, avg_slhtf, gflux, sdlwrf, sulwrf, avg_al
```

### Knowledge Graph Operators:
```
cpr/prate ratio  → ARST (Active Red Sea Trough) activation
avg_ishf         → ADHSI (Asymmetric Diurnal Heat Stress Index)
sdswrf + avg_al  → Surface energy balance
```

---

## How to Load These Variables

```python
import xarray as xr

ds = xr.open_dataset("output_saudi/saudi_ds1_surface_avg_202506.nc")

# Flash flood variables
precip_rate = ds["prate"]        # kg/m²/s
convective  = ds["cpr"]          # kg/m²/s

# Heat variables
sensible_heat = ds["avg_ishf"]   # W/m²
solar_in      = ds["sdswrf"]     # W/m²

# Convert precipitation to mm/day
precip_mm_day = precip_rate * 86400  # 1 kg/m²/s = 86400 mm/day

print(f"Max daily precipitation: {float(precip_mm_day.max()):.2f} mm/day")
print(f"Max sensible heat flux:  {float(sensible_heat.max()):.2f} W/m²")
```

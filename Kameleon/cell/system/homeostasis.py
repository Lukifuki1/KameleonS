#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# homeostasis.py
# Dinamična regulacija parametrov evolucije (mutacije, selekcija, decay, SIS toleranca)

from statistics import mean, pstdev

from loguru import logger

# Privzete mejne vrednosti parametrov
PARAMS = {
    "mutation_rate": 0.15,  # verjetnost spremembe strategije
    "selection_pressure": 0.65,  # agresivnost izločanja slabih entitet
    "decay_rate": 0.10,  # hitrost staranja nepodprtih strategij
    "sis_tolerance": 0.05,  # prag dovoljenih semantičnih odstopanj
}

# Dovoljeni varni razponi
BOUNDS = {
    "mutation_rate": (0.01, 0.60),
    "selection_pressure": (0.10, 0.95),
    "decay_rate": (0.01, 0.40),
    "sis_tolerance": (0.01, 0.25),
}

# Ciljne stabilnostne vrednosti
TARGET_VARIANCE = 0.12
TARGET_DRIFT = 0.0

# PID koeficienti
KP_VAR = 0.35
KI_VAR = 0.10
KD_VAR = 0.25

KP_D = 0.20

# Notranji PID akumulatorji
integral_var = 0.0
last_variance = None


def clamp(value, min_v, max_v):
    return max(min_v, min(value, max_v))


def adjust_parameters(score_history):
    """Samouravnavanje parametrov evolucijskega cikla."""
    global integral_var, last_variance

    if len(score_history) < 6:
        return PARAMS

    # Varianca robustnosti
    variance = pstdev(score_history)

    # Drift med zadnjimi in prvimi vrednostmi
    drift = mean(score_history[-3:]) - mean(score_history[:3])

    # PID – varianca
    error_var = TARGET_VARIANCE - variance
    integral_var += error_var
    derivative_var = 0 if last_variance is None else (variance - last_variance)
    last_variance = variance

    adj = (KP_VAR * error_var) + (KI_VAR * integral_var) - (KD_VAR * derivative_var)

    # PID – drift korekcija
    drift_adj = KP_D * (TARGET_DRIFT - drift)

    # Posodobitev parametrov
    PARAMS["mutation_rate"] = clamp(
        PARAMS["mutation_rate"] + adj, *BOUNDS["mutation_rate"]
    )
    PARAMS["selection_pressure"] = clamp(
        PARAMS["selection_pressure"] - adj, *BOUNDS["selection_pressure"]
    )
    PARAMS["decay_rate"] = clamp(
        PARAMS["decay_rate"] + drift_adj, *BOUNDS["decay_rate"]
    )
    PARAMS["sis_tolerance"] = clamp(
        PARAMS["sis_tolerance"] + (adj * 0.5), *BOUNDS["sis_tolerance"]
    )

    logger.debug(
        f"HOMEOSTAZA: var={variance:.4f}, drift={drift:.4f} → "
        f"mut={PARAMS['mutation_rate']:.3f}, "
        f"sel={PARAMS['selection_pressure']:.3f}, "
        f"dec={PARAMS['decay_rate']:.3f}, "
        f"sis={PARAMS['sis_tolerance']:.3f}"
    )

    return PARAMS


def get():
    """Vrne trenutne homeostatske parametre."""
    return PARAMS.copy()

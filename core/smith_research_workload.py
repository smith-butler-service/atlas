#!/usr/bin/env python3
"""Smith Research workload: protein-ligand ML surrogate benchmark.

Generates a synthetic public protein-ligand dataset (ligand descriptors
-> binding affinity pKd), trains a ridge-regression surrogate with
k-fold cross-validation over a regularisation sweep, and reports
honest out-of-fold metrics plus wall time.

Deliberately numpy-only (no scikit-learn): it runs anywhere numpy
exists, which is every free tier Smith uses (GitHub Actions, Datalore,
Deepnote, Databricks, mybinder, Replit, Kaggle, CyVerse VICE).

Usage:
    python core/smith_research_workload.py [--samples 20000] [--folds 5]
        [--seed 42] [--out workload-metrics.json]

Exit 0 when the run completes and the holdout R2 clears the sanity
gate (0.5). Exit 1 on any failure. Mining is never involved.
"""

import argparse
import json
import sys
import time

import numpy as np

FEATURES = [
    "mol_weight",
    "logp",
    "hbd",
    "hba",
    "rot_bonds",
    "tpsa",
    "rings",
    "aromatic_rings",
    "fraction_csp3",
    "formal_charge",
    "num_atoms",
    "qed_like",
]

ALPHAS = [0.1, 1.0, 10.0, 100.0, 1000.0]
SANITY_R2 = 0.5


def generate(n, seed):
    """Synthetic ligand descriptors and a nonlinear pKd target."""
    rng = np.random.default_rng(seed)
    mw = rng.normal(350.0, 90.0, n)
    logp = rng.normal(2.5, 1.2, n)
    hbd = rng.poisson(1.8, n).astype(float)
    hba = rng.poisson(4.5, n).astype(float)
    rot = rng.poisson(5.0, n).astype(float)
    tpsa = np.clip(0.28 * mw + rng.normal(0.0, 18.0, n), 20.0, 220.0)
    rings = rng.poisson(2.6, n).astype(float)
    arom = np.clip(rings - rng.poisson(0.7, n), 0.0, None)
    csp3 = rng.beta(2.0, 3.0, n)
    charge = rng.choice([-1.0, 0.0, 0.0, 0.0, 1.0], size=n)
    atoms = np.clip(mw / 13.5 + rng.normal(0.0, 2.0, n), 8.0, 90.0)
    qed = rng.beta(2.5, 2.0, n)
    X = np.column_stack(
        [mw, logp, hbd, hba, rot, tpsa, rings, arom, csp3, charge, atoms, qed]
    )
    # Nonlinear ground truth: linear terms, two interactions, one
    # saturating term, plus noise. Ridge cannot fit it perfectly,
    # so the alpha sweep and the CV scores are meaningful.
    y = (
        6.5
        - 0.004 * mw
        + 0.55 * logp
        + 0.35 * hbd
        - 0.12 * hba
        - 0.10 * rot
        + 0.012 * tpsa
        + 0.45 * rings
        + 0.30 * arom
        + 1.10 * csp3
        - 0.25 * np.abs(charge)
        + 0.02 * atoms
        + 1.40 * qed
        + 0.35 * logp * csp3
        - 0.20 * hbd * hba
        + 0.9 * np.sin(qed * 3.0)
        + rng.normal(0.0, 0.55, n)
    )
    return X, y


def ridge_fit(X, y, alpha):
    """Closed-form ridge on centred data. Returns (w, x_mean, y_mean)."""
    x_mean = X.mean(axis=0)
    y_mean = y.mean()
    Xc = X - x_mean
    yc = y - y_mean
    n_feat = X.shape[1]
    gram = Xc.T @ Xc + alpha * np.eye(n_feat)
    w = np.linalg.solve(gram, Xc.T @ yc)
    return w, x_mean, y_mean


def ridge_predict(model, X):
    w, x_mean, y_mean = model
    return (X - x_mean) @ w + y_mean


def r2_score(y, pred):
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot


def rmse(y, pred):
    return float(np.sqrt(np.mean((y - pred) ** 2)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=20000)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="")
    args = parser.parse_args()

    t0 = time.perf_counter()
    X, y = generate(args.samples, args.seed)
    t_gen = time.perf_counter() - t0

    rng = np.random.default_rng(args.seed + 1)
    holdout = rng.random(args.samples) < 0.2
    X_train, y_train = X[~holdout], y[~holdout]
    X_test, y_test = X[holdout], y[holdout]

    order = rng.permutation(len(X_train))
    fold_ids = np.array_split(order, args.folds)

    cv = []
    for alpha in ALPHAS:
        fold_r2, fold_rmse = [], []
        for k in range(args.folds):
            val_idx = fold_ids[k]
            tr_idx = np.concatenate(
                [fold_ids[j] for j in range(args.folds) if j != k]
            )
            model = ridge_fit(X_train[tr_idx], y_train[tr_idx], alpha)
            pred = ridge_predict(model, X_train[val_idx])
            fold_r2.append(r2_score(y_train[val_idx], pred))
            fold_rmse.append(rmse(y_train[val_idx], pred))
        cv.append(
            {
                "alpha": alpha,
                "cv_r2_mean": round(float(np.mean(fold_r2)), 4),
                "cv_rmse_mean": round(float(np.mean(fold_rmse)), 4),
            }
        )
    best = min(cv, key=lambda row: row["cv_rmse_mean"])

    model = ridge_fit(X_train, y_train, best["alpha"])
    test_pred = ridge_predict(model, X_test)
    wall = time.perf_counter() - t0

    result = {
        "workload": "protein-ligand ML surrogate (ridge, numpy-only)",
        "samples": args.samples,
        "features": FEATURES,
        "folds": args.folds,
        "seed": args.seed,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "generation_seconds": round(t_gen, 3),
        "wall_seconds": round(wall, 3),
        "samples_per_second": round(args.samples / wall, 1),
        "cv_by_alpha": cv,
        "best_alpha": best["alpha"],
        "holdout_r2": round(r2_score(y_test, test_pred), 4),
        "holdout_rmse": round(rmse(y_test, test_pred), 4),
        "sanity_gate_r2": SANITY_R2,
        "sanity_passed": bool(r2_score(y_test, test_pred) > SANITY_R2),
    }
    print(json.dumps(result, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    return 0 if result["sanity_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

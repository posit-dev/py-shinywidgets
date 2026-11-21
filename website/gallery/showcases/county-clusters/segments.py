from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

FEATURES: dict[str, str] = {
    "median_income": "Median household income",
    "pct_rural": "% rural",
    "pct_65_older": "% 65 and older",
    "some_college": "% some college",
    "broadband": "% broadband access",
    "uninsured": "% uninsured",
    "life_expectancy": "Life expectancy (years)",
    "adult_obesity": "% adult obesity",
}

# (trait when a cluster's z-score is high, trait when it's low)
FEATURE_TRAITS: dict[str, tuple[str, str]] = {
    "median_income": ("affluent", "lower-income"),
    "pct_rural": ("rural", "urban"),
    "pct_65_older": ("older", "younger"),
    "some_college": ("college-educated", "less educated"),
    "broadband": ("well-connected", "low-broadband"),
    "uninsured": ("high uninsured", "well-insured"),
    "life_expectancy": ("long life expectancy", "short life expectancy"),
    "adult_obesity": ("high obesity", "low obesity"),
}

RANDOM_STATE = 0
NAME_TOP_N = 2
NAME_THRESHOLD = 0.2


@dataclass
class Clustering:
    k: int
    labels: npt.NDArray[np.intp]
    profile: pd.DataFrame
    names: list[str]
    silhouette: float


def fit(df: pd.DataFrame, k: int) -> Clustering:
    z = standardize(df)
    # sklearn's stubs type n_init as str only, though an int (explicit restart count) is valid at runtime.
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE)  # type: ignore[arg-type]
    raw_labels = kmeans.fit_predict(z)
    order = stable_order(df, raw_labels, k)
    labels = order[raw_labels]
    profile = cluster_profile(z, labels, k)
    names = [segment_name(profile.loc[i]) for i in range(k)]
    silhouette = float(silhouette_score(z, labels)) if k > 1 else float("nan")
    return Clustering(
        k=k, labels=labels, profile=profile, names=names, silhouette=silhouette
    )


def twins(df: pd.DataFrame, fips: str, n: int = 5) -> pd.DataFrame:
    z = standardize(df)
    matches = np.flatnonzero(df["fips"].to_numpy() == fips)
    if not len(matches):
        empty = pd.Series(dtype=float)
        return df.iloc[0:0].assign(distance=empty)
    pos = int(matches[0])
    distances = np.linalg.norm(z - z[pos], axis=1)
    order = np.argsort(distances)
    order = order[order != pos]
    top = order[:n]
    return df.iloc[top].assign(distance=distances[top])


def standardize(df: pd.DataFrame) -> npt.NDArray[np.float64]:
    x = df[list(FEATURES)].to_numpy(dtype=np.float64)
    return StandardScaler().fit_transform(x)


def stable_order(
    df: pd.DataFrame, raw_labels: npt.NDArray[np.intp], k: int
) -> npt.NDArray[np.intp]:
    income = df["median_income"].to_numpy(dtype=np.float64)
    population = df["population"].to_numpy(dtype=np.float64)
    weighted_income = np.zeros(k)
    for cluster in range(k):
        mask = raw_labels == cluster
        weighted_income[cluster] = np.average(income[mask], weights=population[mask])
    rank_order = np.argsort(weighted_income)
    mapping = np.empty(k, dtype=np.intp)
    mapping[rank_order] = np.arange(k)
    return mapping


def cluster_profile(
    z: npt.NDArray[np.float64], labels: npt.NDArray[np.intp], k: int
) -> pd.DataFrame:
    rows = [z[labels == cluster].mean(axis=0) for cluster in range(k)]
    return pd.DataFrame(rows, columns=list(FEATURES), index=range(k))


def segment_name(z_row: pd.Series) -> str:
    ranked = sorted(FEATURES, key=lambda f: -abs(float(z_row.loc[f])))
    traits = [
        FEATURE_TRAITS[f][0 if float(z_row.loc[f]) >= 0 else 1]
        for f in ranked
        if abs(float(z_row.loc[f])) > NAME_THRESHOLD
    ]
    if not traits:
        return "Average mix"
    name = " · ".join(traits[:NAME_TOP_N])
    return name[0].upper() + name[1:]

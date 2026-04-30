"""Customer Segmentation.

K-Means clustering on RFM features, plus a heuristic next-best-offer (NBO)
recommender. Produces actionable, named segments suitable for marketing,
relationship management, and product strategy.
"""

from __future__ import annotations

import pandas as pd

from ..logger import get_logger
from ._io import load_core_frames

_log = get_logger("ml.segmentation")


SEGMENT_NAMES = {
    0: "Champions",
    1: "Loyal",
    2: "Potential",
    3: "At Risk",
    4: "Hibernating",
}


class CustomerSegmentation:
    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.model = None
        self.feature_columns = ["Recency", "Frequency", "Monetary"]

    def build_rfm(self) -> pd.DataFrame:
        frames = load_core_frames()
        tx = frames["transactions"].copy()
        acc = frames["accounts"].copy()
        tx["TransactionDate"] = pd.to_datetime(tx["TransactionDate"], errors="coerce")
        tx = tx.merge(acc[["AccountID", "CustomerID"]], on="AccountID", how="left")
        as_of = tx["TransactionDate"].max()
        rfm = (
            tx.groupby("CustomerID")
              .agg(
                  Recency=("TransactionDate", lambda s: (as_of - s.max()).days),
                  Frequency=("TransactionID", "count"),
                  Monetary=("Amount", "sum"),
              )
              .reset_index()
        )
        return rfm

    def fit(self) -> pd.DataFrame:
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler
        except ImportError as exc:
            raise RuntimeError("scikit-learn is required for CustomerSegmentation") from exc

        rfm = self.build_rfm()
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(rfm[self.feature_columns])
        self.model = KMeans(n_clusters=self.n_clusters, n_init=10, random_state=self.random_state)
        rfm["Cluster"] = self.model.fit_predict(x_scaled)

        # Order clusters by Monetary descending and rename
        order = (
            rfm.groupby("Cluster")["Monetary"].mean().sort_values(ascending=False).index.tolist()
        )
        cluster_to_segment = {c: SEGMENT_NAMES.get(i, f"Segment_{i}") for i, c in enumerate(order)}
        rfm["Segment"] = rfm["Cluster"].map(cluster_to_segment)

        _log.info("segmentation_done segments=%d customers=%d", self.n_clusters, len(rfm))
        return rfm

    @staticmethod
    def next_best_offer(rfm: pd.DataFrame) -> pd.DataFrame:
        offers = {
            "Champions":   "Premium wealth advisory + co-branded credit card",
            "Loyal":       "Loyalty rewards uplift + savings rate boost",
            "Potential":   "Cross-sell savings + personal loan pre-approval",
            "At Risk":     "Win-back campaign with fee waivers",
            "Hibernating": "Reactivation incentive (cashback on next 3 txns)",
        }
        rfm = rfm.copy()
        rfm["NextBestOffer"] = rfm["Segment"].map(offers).fillna("Standard relationship review")
        return rfm


def main() -> None:
    seg = CustomerSegmentation()
    rfm = seg.fit()
    rfm = seg.next_best_offer(rfm)
    print(rfm.head(15).to_string(index=False))


if __name__ == "__main__":
    main()

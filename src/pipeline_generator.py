"""Generate the data-pipeline architecture diagram (PNG).

Run as a script when the optional ``diagrams`` package is installed:

    pip install diagrams
    python -m src.pipeline_generator

The Mermaid diagrams under ``diagrams/*.md`` are the primary documentation
artifacts; this script regenerates the legacy raster ``data_pipeline.png``.
"""

from __future__ import annotations

import os
import urllib.request


def render() -> None:
    try:
        from diagrams import Cluster, Diagram, Edge
        from diagrams.aws.general import Users
        from diagrams.custom import Custom
        from diagrams.onprem.database import MSSQL
        from diagrams.programming.language import Python
    except ImportError:
        print("The 'diagrams' package is not installed. Skipping rendering.")
        print("Install with: pip install diagrams (also requires Graphviz on PATH)")
        return

    streamlit_url = (
        "https://raw.githubusercontent.com/streamlit/streamlit/develop/docs/images/"
        "streamlit-mark-color.png"
    )
    streamlit_icon = "streamlit.png"
    if not os.path.exists(streamlit_icon):
        try:
            urllib.request.urlretrieve(streamlit_url, streamlit_icon)
        except Exception:  # noqa: BLE001
            pass

    graph_attr = {
        "fontsize": "20", "fontname": "Helvetica-bold", "bgcolor": "#F4F7F6",
        "pad": "1.0", "splines": "spline", "nodesep": "1.0", "ranksep": "1.5",
    }
    node_attr = {"fontname": "Helvetica", "fontsize": "12", "fontcolor": "#2C3E50"}
    edge_attr = {"color": "#34495E", "fontname": "Helvetica", "fontsize": "10",
                 "fontcolor": "#7F8C8D", "penwidth": "2.0"}
    cluster_attr = {"bgcolor": "#FFFFFF", "pencolor": "#BDC3C7", "penwidth": "2.0",
                    "fontname": "Helvetica-bold", "fontsize": "14", "fontcolor": "#2980B9"}

    with Diagram(
        "Global Horizon Bank Data Architecture",
        show=False,
        filename="diagrams/data_pipeline",
        direction="LR",
        graph_attr=graph_attr, node_attr=node_attr, edge_attr=edge_attr,
    ):
        users = Users("Bank Customers\n& Operations")

        with Cluster("OLTP System", graph_attr=cluster_attr):
            python_gen = Python("Faker & Pandas\nData Generator")
            oltp_db = MSSQL("SQL Server\nTransactional DB")
            users >> Edge(label="Daily Transactions") >> oltp_db
            python_gen >> Edge(label="Bulk Insert") >> oltp_db

        with Cluster("ETL Process", graph_attr=cluster_attr):
            etl_procs = MSSQL("Stored Procedures\n(T-SQL)")

        with Cluster("Data Warehouse", graph_attr=cluster_attr):
            dwh_db = MSSQL("SQL Server\nStar Schema OLAP")

        with Cluster("Analytics & Reporting", graph_attr=cluster_attr):
            if os.path.exists(streamlit_icon):
                dashboard = Custom("Streamlit App", streamlit_icon)
            else:
                dashboard = Python("Streamlit App")
            analysts = Users("Executive & Analysts")

        oltp_db >> Edge(label="Extract (Daily Batch)") >> etl_procs
        etl_procs >> Edge(label="Transform & Load\n(SCD Type 2)") >> dwh_db
        dwh_db >> Edge(label="Aggregate Queries\n(Window Functions)") >> dashboard
        dashboard >> Edge(label="Business Insights") >> analysts


if __name__ == "__main__":
    render()

# =============================================================================
# Global Horizon Bank — Executive Dashboard (Production Image)
# =============================================================================
FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="Global Horizon Bank Dashboard" \
      org.opencontainers.image.description="Enterprise Data Warehouse Platform — Executive Dashboard" \
      org.opencontainers.image.source="https://github.com/<org>/global-horizon-bank-dwh-project"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# System dependencies — freetds for pymssql, build tools for pyarrow / scikit-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        freetds-dev \
        freetds-bin \
        ca-certificates \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project files
COPY . .

# Streamlit port
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://localhost:8501/_stcore/health || exit 1

# Start the executive dashboard
ENTRYPOINT ["streamlit", "run", "dashboard/app_executive.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--browser.gatherUsageStats=false"]

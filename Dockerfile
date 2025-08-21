FROM python:3.11-slim-bookworm AS builder

# System deps for building Python wheels on both amd64 + arm64
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc build-essential python3-dev \
        ffmpeg git libegl1 libssl-dev libffi-dev zlib1g-dev libjpeg-dev \
        qt6-base-dev qt6-tools-dev-tools build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app/

# Force pip to use wheels when available
ENV PIP_ONLY_BINARY=:all:
# Upgrade pip & build tools
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install in a venv to isolate dependencies
RUN python3 -m venv /venv && /venv/bin/pip install .

# ---------------------------------------------------------------------

FROM python:3.11-slim-bookworm AS prod

# Runtime deps only (no compilers, git, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg libegl1 libgl1-mesa-dev libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed venv + app
COPY --from=builder /venv /venv
COPY --from=builder /app /app

# Use venv in PATH
ENV PATH="/venv/bin:$PATH"
WORKDIR /app

EXPOSE 5000
CMD ["onthespot-web", "--host", "0.0.0.0", "--port", "5000"]

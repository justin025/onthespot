# Builder uses the full Debian base
FROM python:3.11-bookworm AS builder

WORKDIR /app
COPY . /app/

# Upgrade pip & build tools
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install in a venv (keeps things isolated + easy copy later)
RUN python3 -m venv /venv && /venv/bin/pip install .

# ---------------------------------------------------------------------

# Runtime stays slim
FROM python:3.11-slim-bookworm AS prod

# Install only minimal runtime deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg libegl1 libgl1-mesa-dev libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv and app from builder
COPY --from=builder /venv /venv
COPY --from=builder /app /app

ENV PATH="/venv/bin:$PATH"
WORKDIR /app

EXPOSE 5000
CMD ["onthespot-web", "--host", "0.0.0.0", "--port", "5000"]

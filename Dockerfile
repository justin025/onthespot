FROM python:3.11-slim-bookworm AS base

FROM base AS updated-system

RUN apt-get update && \
    apt-get install -y ffmpeg git libegl1

RUN pip install git+https://github.com/justin025/onthespot

FROM updated-system AS cleaned-system

RUN apt-get purge -y git && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /root/.cache

FROM cleaned-system AS prod
EXPOSE 5000
CMD ["onthespot-web", "--host", "0.0.0.0", "--port", "5000"]

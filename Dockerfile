FROM debian:latest
ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

RUN apt update -y
RUN apt upgrade -y
RUN apt install -y python3 python3-pip python3.11-venv ffmpeg git libegl1
RUN apt install -y python3-pyqt6

WORKDIR /app
RUN python3 -m venv venv
RUN source /app/venv/bin/activate

# copy PyQt6 files to the virtual environment, as it is not installable directly via pip
RUN cp -r /usr/lib/python3/dist-packages/PyQt6* /app/venv/lib/python3.11/site-packages/

COPY requirements.txt /app/requirements.txt
RUN /app/venv/bin/python3 -m pip install --upgrade pip
RUN /app/venv/bin/python3 -m pip install -r /app/requirements.txt

COPY setup.cfg pyproject.toml /app/
COPY src /app/src
RUN /app/venv/bin/python3 -m pip install /app

EXPOSE 5000
CMD ["/app/venv/bin/onthespot-web", "--host", "0.0.0.0", "--port", "5000"]

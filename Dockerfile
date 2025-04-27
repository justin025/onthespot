FROM debian:latest
ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]
RUN apt update -y
RUN apt upgrade -y
RUN apt install -y python3 python3-pip python3.11-venv ffmpeg git libegl1 -y
WORKDIR /app
RUN python3 -m venv venv
RUN source /app/venv/bin/activate
RUN /app/venv/bin/python3 -m pip install git+https://github.com/justin025/onthespot
EXPOSE 5000
CMD ["/app/venv/bin/onthespot-web", "--host", "0.0.0.0", "--port", "5000"]

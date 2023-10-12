FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-c"]

# Install system dependencies

# Python 3.11 latest supported by this OS
RUN apt -y update && apt -y upgrade
RUN apt -y install software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa 
RUN apt -y update
RUN apt -y install python3.11
RUN apt -y install python3.11-venv
RUN python3.11 -m ensurepip
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 

# Install project dependencies
ADD requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

WORKDIR /app

# This config for dev server only
ENTRYPOINT python manage.py runserver --insecure 0.0.0.0:80
# DeepView.Profile API

![DeepView](https://raw.githubusercontent.com/CentML/DeepView.Profile/main/assets/deepview.png)

DeepView.Profile API is a RESTful service wrapper around [DeepView.Profile](https://github.com/CentML/DeepView.Profile) which is profiling tool of [PyTorch](https://pytorch.org) neural networks.

- [Installation](#installation)
- [Running Service](#running-service)
- [Service usage](#service-usage)
- [Dev tooling](#dev-tooling)

## Installation

DeepView.Profile API has same requirements as [DeepView.Profile](https://github.com/CentML/DeepView.Profile).

It works NVIDIA GPU environments with CUDA. CUDA support by PyTorch and drivers must start fom 11.7+ version.

if you have installed NVIDIA drivers you may check CUDA version using following command:

```bash
nvidia-smi
```

### Installation from source

```bash
git clone https://github.com/cpavel/DeepView.Profile-API.git
cd deepview_profile_api
pip install -r requirements.txt
```

### Install project into Docker Container

You may create docker image to run project in container.
First clone project from repo, then run following command from the **root** folder of the repo

```bash
docker build --pull --rm . -f "docker/Dockerfile" -t deepview/service:latest
```

## Running Service

### Set up env variables

Set DEBUG to True if necessary, either in .env file or in system environment variable

```bash
export DEBUG=True
```

### Run development server

Run Django development server from repo root:

```bash
python manage.py runserver 0.0.0.0:80
```

You may change port if necessary.

If Debug=False, you may need to add runserver --insecure param to see Swagger UI

### Running service in container

Make sure have installed [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) first.
If you have troubles with setting up your host machine, you may read [How to Install PyTorch on the GPU with Docker](https://saturncloud.io/blog/how-to-install-pytorch-on-the-gpu-with-docker/).

Run container

```bash
docker run -it --rm --gpus all -v $(pwd):/app/ -p 80:80 deepview/service
```

### Production server consideration

- Production server must not use Django development web server
- You will need to route Django static files to be able see Swagger UI
- Don't forget to check final settings by 

```bash
python manage.py check --deploy
```

## Service usage

- Check if swagger page is working (<http://127.0.0.1:80/swagger> if running locally)
- Try "status" endpoint to see if everything is ok
- Try "profile" endpoint with one of the [DeepView.Profile/examples](https://github.com/CentML/DeepView.Profile/tree/main/examples)

## Dev tooling

Black v2023+ is used for code formatting
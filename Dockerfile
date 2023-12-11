# Use Ubuntu 16.04 as the base image
FROM ubuntu:16.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    gcc \
    libnuma-dev \
    make \
    numactl \
    zlib1g-dev

# Install Miniconda for Python 3.8
ENV MINICONDA_VERSION Miniconda3-py38_4.10.3-Linux-x86_64.sh
RUN apt-get install -y wget && \
    wget https://repo.anaconda.com/miniconda/${MINICONDA_VERSION} && \
    bash ${MINICONDA_VERSION} -b -p /miniconda && \
    rm ${MINICONDA_VERSION}
ENV PATH="/miniconda/bin:${PATH}"

# Set up the Python environment
RUN conda create -n gavel-env python=3.8
ENV PATH /miniconda/envs/gavel-env/bin:$PATH
RUN /bin/bash -c "source activate gavel-env"

# Copy your project files into the Docker image
COPY . /gavel

# Install Python dependencies
RUN pip install -r /gavel/scheduler/requirements.txt

# Set the working directory
WORKDIR /gavel/scheduler

# Compile the project
RUN make

# Command to run when starting the container
CMD ["bash"]

# Use an ARM64 compatible base image
FROM ubuntu:20.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    gcc \
    libnuma-dev \
    make \
    numactl \
    zlib1g-dev

# Install OpenBLAS and other dependencies
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    pkg-config

# Install Miniconda for ARM64
ENV MINICONDA_VERSION Miniconda3-latest-Linux-aarch64.sh
RUN apt-get install -y wget && \
    wget https://repo.anaconda.com/miniconda/${MINICONDA_VERSION} && \
    bash ${MINICONDA_VERSION} -b -p /miniconda && \
    rm ${MINICONDA_VERSION}
ENV PATH="/miniconda/bin:${PATH}"

# Create the Python environment
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

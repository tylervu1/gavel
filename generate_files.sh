#!/bin/bash

# Detect the operating system
OS=$(uname -s)

# Define file paths
DOCKERFILE_MAC="Dockerfile.mac"
DOCKERFILE_OTHER="Dockerfile.other"
REQUIREMENTS_MAC="requirements.mac.txt"
REQUIREMENTS_OTHER="requirements.other.txt"

# Copy the appropriate Dockerfile and requirements.txt based on the OS
if [[ "$OS" == "Darwin" ]]; then
    cp $DOCKERFILE_MAC Dockerfile
    cp $REQUIREMENTS_MAC scheduler/requirements.txt
else
    cp $DOCKERFILE_OTHER Dockerfile
    cp $REQUIREMENTS_OTHER scheduler/requirements.txt
fi

# Confirmation messages
echo "Dockerfile and requirements.txt have been set up for your system."

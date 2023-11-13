#!/bin/bash

# Check if the backend.env file path is provided as an argument
if [ -z "$1" ]; then
    echo "Error: backend.env file path not provided"
    exit 1
fi

# Read the backend.env file and export each variable
while IFS='=' read -r key value; do
    # Skip lines that start with # (comments) or are empty
    [[ $key =~ ^[[:space:]]*#|^$ ]] && continue
    # Trim leading and trailing whitespace from key and value
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    # Export the variable
    export "$key=$value"
done < "$1"
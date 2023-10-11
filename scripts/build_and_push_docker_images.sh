#!/bin/bash

# Build Docker images
docker build -t ontology-matching-services-backend-app:latest -f Dockerfile.backend .
docker build -t ontology-matching-services-frontend-app:latest -f Dockerfile.frontend .

# Tag and push Backend image to GitHub Packages
docker tag ontology-matching-services-backend-app:latest ghcr.io/catalystneuro/ontology-matching-services-backend-app:latest
docker push ghcr.io/catalystneuro/ontology-matching-services-backend-app:latest

# Tag and push Frontend image to GitHub Packages
docker tag ontology-matching-services-frontend-app:latest ghcr.io/catalystneuro/ontology-matching-services-frontend-app:latest
docker push ghcr.io/catalystneuro/ontology-matching-services-frontend-app:latest

echo "All operations completed successfully!"
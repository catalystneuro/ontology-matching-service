# Ontology Matching Service

Private repo to play with metadata extraction

How to test locally without docker

First export local variables for the database

```
export OPENAI_API_KEY="your_key_here"
export QDRANT_API_KEY="your_key_here"
```

Then run the following command to start the server of the backend:
```
uvicorn app.main:app --reload
```



And then test the service by running this:

```
curl http://localhost:8000/get_ontology_matches/?text=This%20describes%20a%20behavior%20of%20hunting%20in%20a%20caged%20environment
curl https://ontology-matching.delightfulsand-a1030a48.centralus.azurecontainerapps.io/get_ontology_matches/?text=This%20describes%20a%20behavior%20of%20hunting%20in%20a%20caged%20environment
```

This queries the behavior for `This describes a behavior of hunting in a caged environment`


You can see the schema:
```
http://localhost:8000/docs

```

Build with docker

```
docker build -t ontology-matching-services-backend-app:latest -f Dockerfile.backend .
docker build -t ontology-matching-services-frontend-app:latest -f Dockerfile.frontend .
```

How to upload to github packages:

Backend:
 
```
docker tag ontology-matching-services-backend-app ghcr.io/catalystneuro/ontology-matching-services-backend-app:latest
docker push ghcr.io/catalystneuro/ontology-matching-services-backend-app:latest

```

Frontend:
```
docker tag ontology-matching-services-frontend-app:latest ghcr.io/catalystneuro/ontology-matching-services-frontend-app:latest
docker push ghcr.io/catalystneuro/ontology-matching-services-frontend-app:latest
```

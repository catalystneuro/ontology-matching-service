from typing import List, Dict, Literal, Optional
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai.error import InvalidRequestError

from ontology_matching_service.ontology_grounding import semantic_match, rerank


class ParentStructure(BaseModel):
    definition: Optional[str] = None
    id: str
    name: Optional[str] = None
    parent_structure: Optional[List["ParentStructure"]] = None
    synonyms: Optional[str] = None
    text_to_embed: Optional[str] = None


ParentStructure.update_forward_refs()  # This is needed because of the recursive definition


class Payload(BaseModel):
    definition: Optional[str] = None
    direct_parents: List[str]
    id: str
    name: Optional[str] = None
    parent_structure: Optional[List[ParentStructure]] = None
    synonyms: Optional[str] = None
    text_to_embed: Optional[str] = None


origins = [
    "http://localhost:3000",  # Allow local frontend origin
    "http://frontend:3000",  # Allow Docker-internal frontend service address using docker-compose
    "https://ontology-matching-frontend.delightfulsand-a1030a48.centralus.azurecontainerapps.io",  # Allow your frontend in Azure Container Apps
]

if os.environ.get("EXTERNAL_SERVER_ADDRESS", None):
    external_server_address = os.environ.get("EXTERNAL_SERVER_ADDRESS")
    origins.append(external_server_address)  # Adds an origin to allow external server access


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/get_ontology_matches/", response_model=List[Payload])
async def get_ontology_matches(
    text: str = Query(..., description="Text excerpt to match against"),
    ontology: Optional[Literal["neuro_behavior_ontology", "cognitiveatlas"]] = Query("neuro_behavior_ontology", description="Ontology type to use"),
):

    api_key = os.environ.get("QDRANT_API_KEY")
    if not api_key:
        raise ValueError("QDRANT_API_KEY environment variable not set")

    open_ai_api_key = os.environ.get("OPENAI_API_KEY")
    if not open_ai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    top = 30
    score_threshold = 0.50

    try:
        results_list = semantic_match(text=text, top=top, score_threshold=score_threshold, ontology=ontology)
        if ontology in ["neuro_behavior_ontology"]:
            results_list = rerank(results_list, text, ontology=ontology)
        
    except InvalidRequestError as e:
        # Handle the specific InvalidRequestError
        detail = "Text too large. Try using a shorter description or use smaller pieces of your text as input."
        raise HTTPException(status_code=400, detail=detail)

    except Exception as e:
        # Handle general errors and raise a 500 Internal Server Error
        raise HTTPException(status_code=500, detail=str(e))
    
    if results_list:
        payload_list = [result.payload for result in results_list][:5]
        
    else:
        payload_list = []

    return payload_list

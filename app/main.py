from typing import List, Dict, Literal, Optional
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ontology_matching_service.ontology_grounding import semantic_match, rerank

class ParentStructure(BaseModel):
    definition: Optional[str] = None
    id: str
    name: Optional[str] = None
    parent_structure: Optional[List['ParentStructure']] = None
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
    "http://16.171.225.165:3000",  # Allow aws frontend origin

]

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
        ontology: Optional[Literal["behavior"]] = Query("behavior", description="Ontology type to use")):
    

    api_key = os.environ.get("QDRANT_API_KEY")
    if not api_key:
        raise ValueError("QDRANT_API_KEY environment variable not set")

    open_ai_api_key = os.environ.get("OPENAI_API_KEY")
    if not open_ai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
        
    # Your pre-defined values
    top = 30
    score_threshold = 0.50
        
    results_list = semantic_match(text=text, top=top, score_threshold=score_threshold)
    if not results_list:
        raise HTTPException(status_code=404, detail="Matches not found")
    
    results_list = rerank(results_list, text)
    if results_list:
        payload_list = [result.payload for result in results_list]
    else:
        results_list = [{}]
    
    return payload_list[:5]
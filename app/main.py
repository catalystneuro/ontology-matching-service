from typing import List, Literal, Optional
import os
import pyodbc


from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
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
data_base_logging = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize the database connection at startup
@app.on_event("startup")
async def startup():
    global data_base_logging
    server = os.environ["LOG_DATA_BASE_SERVER"]
    database = os.environ["LOG_DATA_BASE_NAME"]
    username = os.environ["LOG_DATA_BASE_USER_NAME"]
    password = os.environ["LOG_DATA_BASE_USER_PASSWORD"]
    database_url = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
    )
    data_base_logging = pyodbc.connect(database_url, autocommit=True)


# Close the database connection on shutdown
@app.on_event("shutdown")
async def shutdown():
    global data_base_logging
    data_base_logging.close()


# Dependency to get the DB connection
def get_data_base_logging():
    return data_base_logging


def log_query(data_base_logging: pyodbc.Connection, text: str, payload_list: List[Payload], ontology: str):
    
    # Remove some redundant information from the payload for logging
    modified_payload_list = [
        {
            "name": payload["name"],
            "id": payload["id"],
            "definition": payload["definition"],
            "synonyms": payload["synonyms"],
        }
        for payload in payload_list
    ]

    payload_to_log = str(modified_payload_list)

    try:
        cursor = data_base_logging.cursor()
        query_text = text
        insert_query = """
            INSERT INTO QueryLogs (QueryText, Timestamp, Endpoint, ResponsePayload, AdditionalInfo , BackEndLog , OntologyQueried)
            VALUES (?, GETDATE(), '/get_ontology_matches/', ?, NULL, NULL, ?)
        """
        cursor.execute(insert_query, query_text, payload_to_log, ontology)
        print("Query logged successfully")
    except Exception as e:
        print(f"An error occurred while logging: {e}")


@app.get("/get_ontology_matches/", response_model=List[Payload])
async def get_ontology_matches(
    background_tasks: BackgroundTasks,
    data_base_logging=Depends(get_data_base_logging),
    text: str = Query(..., description="Text excerpt to match against"),
    ontology: Optional[Literal["neuro_behavior_ontology", "cognitiveatlas"]] = Query(
        "neuro_behavior_ontology", description="Ontology type to use"
    ),
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

    # loging
    background_tasks.add_task(log_query, data_base_logging, text, payload_list, ontology)

    return payload_list


def process_response(payload_list):
    
    # Remove some redundant information from the payload for logging
    
    output = {response.id: dict(name=response.payload["name"], definition=response.payload["definition"]) for response in payload_list}
    
    return output
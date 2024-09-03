import warnings
import json
import os

import openai
from qdrant_client import QdrantClient

from functools import lru_cache


@lru_cache(maxsize=None)
def get_qdrant_client():
    qdrant_url = "ea062dec-cb5b-4320-82a7-3c99a9110bf9.europe-west3-0.gcp.cloud.qdrant.io:6333"
    api_key = os.getenv("QDRANT_API_KEY", "")
    return QdrantClient(url=qdrant_url, api_key=api_key)


def embed_text(text: str) -> list:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )
    embedding = response['data'][0]['embedding']
    return embedding


def semantic_match(text, top=30, score_threshold=0.5, ontology="neuro_behavior_ontology"):
    qdrant_client = get_qdrant_client()

    query_vector = embed_text(text)

    results = qdrant_client.search(
        collection_name=ontology,
        query_vector=query_vector,
        limit=top,
        with_payload=True,
        score_threshold=score_threshold,
        with_vectors=False,
    )

    return results


def rerank_with_openai_from_ontologies_and_text(text, descriptions, ontology):
    ontology_properly_fromatted = ontology.replace("_", " ").title()
    if "ontology" not in ontology_properly_fromatted:
        ontology_properly_fromatted += " Ontology"
    prompt = f""" 
    Here is a text description of a behavior:
    {text}
    And here is the description of some entities from the {ontology_properly_fromatted}:
    {descriptions}

    From those entities, return a reranked list with the 10 most relevant entities to the text description ordered from most relevant to least relevant.
    If an element does not seem related enough, do not include it in the list.
    Format the response as a JSON object with the following structure:
    {{
        "relevant_entities": ["entity_id_1", "entity_id_2", "entity_id_3", "entity_id_4", "entity_id_5", "entity_id_6", "entity_id_7", "entity_id_8", "entity_id_9", "entity_id_10"]
    }}
    
    """

    model = "gpt-3.5-turbo"
    openai.api_key = os.getenv("OPENAI_API_KEY")

    system_content = "You are a neuroscience researcher and you are interested in figuring out specific behaviors from a text description"
    completion = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )

    response = completion.choices[0].message.content
    try:
        
        # Remove markdown formatting if it exists
        if response.startswith('```json'):
            response = response.strip('```').strip()
            response = response.replace("json", "")
        json_dict = json.loads(response)
        key = list(json_dict.keys())[0]
        entities_found = json_dict[key]
    except:
        warnings.warn(
            f"The response from OpenAI was not in the expected format. Here is the response:"
            f"\n {response} \n Returning an empty list."
        )
        entities_found = []
    return entities_found


def build_description_sentence(result: dict):
    payload = result.payload
    name = payload["name"]
    definition = payload.get("definition", "")
    synonym = payload.get("synonym", "")
    id = payload["id"]

    description = f"id: {id}, name: {name}, definition: {definition}, synonyms: {synonym}"

    return description


def naive_rerank_with_bm25(example_to_test, results):
    from rank_bm25 import BM25Okapi
    import nltk

    nltk.download("punkt")
    from nltk.tokenize import word_tokenize

    terms_info = [(result.payload["id"], result.payload["name"]) for result in results]
    terms = [result.payload["text_to_embed"] for result in results]

    text = example_to_test["text_excerpt"]

    # Tokenizing
    tokenize = True
    if tokenize:
        tokenized_corpus = [word_tokenize(term) for term in terms]
        tokenized_query = word_tokenize(text)
    else:
        tokenized_corpus = [term for term in terms]
        tokenized_query = text

    # BM25 model
    bm25 = BM25Okapi(tokenized_corpus)

    # Get scores for the query against each term in the corpus
    scores = bm25.get_scores(tokenized_query)

    # Zip together terms' information and scores, and sort
    sorted_terms = sorted(zip(terms_info, scores), key=lambda x: x[1], reverse=True)

    return sorted_terms


def rerank(results_list, text: str, ontology: str):
    # Build descriptions of the behavior for prompts and call LLM to rerank
    description_list = [build_description_sentence(result=result) for result in results_list]
    entities_found = rerank_with_openai_from_ontologies_and_text(
        text=text,
        descriptions=description_list,
        ontology=ontology,
    )

    results_dict = {result.payload["id"]: result for result in results_list}
    seen_ids = set()
    matching_result_list = []

    # Remove duplicates
    for id in entities_found:
        if id not in seen_ids and id in results_dict:
            matching_result_list.append(results_dict[id])
            seen_ids.add(id)

    return matching_result_list


def rerank_bm25(results_list, text: str):
    # Build descriptions of the behavior for prompts and call LLM to rerank
    sorted_terms = naive_rerank_with_bm25(example_to_test={"text_excerpt": text}, results=results_list)

    # LLM returns strings with the IDs. Match them back to the original results to get the full payloads
    matching_result_list = []
    for term in sorted_terms:
        id = term[0][0]
        matching_result = next((result for result in results_list if result.payload["id"] == id))
        matching_result_list.append(matching_result)

    return matching_result_list


def process_response(payload_list):
    
    # Remove some redundant information from the payload for logging
    
    output = {response.payload["id"]: dict(name=response.payload["name"], definition=response.payload["definition"]) for response in payload_list}
    
    return output
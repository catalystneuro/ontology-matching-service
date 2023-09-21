import requests
import warnings
import json
from pathlib import Path
import os

import openai
from langchain.embeddings.openai import OpenAIEmbeddings
from qdrant_client import QdrantClient


def semantic_match(text, top=30, score_threshold=0.5):
    qdrant_url = "https://18ef891e-d231-4fdd-8f6d-8e2d91337c24.us-east4-0.gcp.cloud.qdrant.io"
    api_key = os.environ["QDRANT_API_KEY"]
    qdrant_client = QdrantClient(
        url=qdrant_url,
        api_key=api_key,
    )

    results = query_qdrant_vector_database(
        text=text, qdrant_client=qdrant_client, top=top, score_threshold=score_threshold
    )

    return results


def embed_text(text: str) -> list:
    embedding_model = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
    embedding = embedding_model.embed_documents([text])[0]

    return embedding


def query_qdrant_vector_database(text: str, qdrant_client, top=5, score_threshold=0.5):
    collection_name = "neuro_behavior_ontology"

    query_vector = embed_text(text)
    search_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=top,
        with_payload=True,
        score_threshold=score_threshold,
        with_vectors=False,
    )

    return search_results


def rerank_with_openai_from_ontologies_and_text(text, descriptions):
    prompt = f""" 
    Here is a text description of a behavior:
    {text}
    And here is the description of some entities from the Neuro Behavioral Ontology:
    {descriptions}

    From those entities, return a reranked list with the 10 most relevant entities to the text description ordered from most relevant to least relevant.
    If an element does not seem related enough, do not include it in the list.
    The format of the output list should be in json style and include only the ids of the entities in the list, not the names or definitions.
    """

    model = "gpt-3.5-turbo"
    openai.api_key = os.getenv("OPENAI_API_KEY")

    system_content = "You are a neuroscience researcher and you are interested in figuring out specific behaviors from a text description"
    try:
        completion = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
    except:
        raise (f"OpenAI API call failed with promprt {prompt}")

    response = completion.choices[0].message.content
    response

    try:
        json_dict = json.loads(response)
        key = list(json_dict.keys())[0]
        entities_found = json_dict[key]
    except:
        warnings.warn(
            f"The response from OpenAI was not in the expected format. Here is the response:" 
            "\n {response} \n Returning an empty list."
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


def rerank(results_list, text: str):
    # Build descriptions of the behavior for prompts and call LLM to rerank
    description_list = [build_description_sentence(result=result) for result in results_list]
    entities_found = rerank_with_openai_from_ontologies_and_text(text=text, descriptions=description_list)

    # LLM returns strings with the IDs. Match them back to the original results to get the full payloads
    matching_result_list = []
    for id in entities_found:
        matching_result = next((result for result in results_list if result.payload["id"] == id))
        matching_result_list.append(matching_result)

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

##############################
# Old LLM as an entity reranker
##############################

def extract_behavior_descriptions_from_prompt(prompt):
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

    return response


def extract_behavior_metadata_from(section):
    instructions_prompt = "You are a neuroscience researcher and you are interested in figuring out behavior from the methods section of scientific papers."

    prompt = (
        f"{instructions_prompt} \n"
        f"Here is the section method of a paper {section} \n"
        "Return a list with behaviors described  using complete sentences. If possible, usedefinitions from the neurobehavior ontology (OBO). "
        "Return the list in the following format: \n"
        "First behavior: description of first behavior, second behavior : description of second behavior, ... \n"
        "Do not add any introductory sentences before the list. "
        "Do not add any notes after the list. "
        "Report only the different types of tracked behaviors. Omit any other details about the experiment. "
        "Do not add line jumps \n between the items in the list."
        "If only one behavior is described, return a list with one item."
        "If no behaviors are described, return an empty list []."
    )

    response = extract_behavior_descriptions_from_prompt(prompt)

    if response != "[]":
        behaviors = response.split("\n")
        behaviors = [b for b in behaviors if b]
    else:
        behaviors = []

    return behaviors


def ground_terms_in_ontology(text_list: list[str], top=5, score_threshold=0.5) -> list:
    qdrant_url = "https://18ef891e-d231-4fdd-8f6d-8e2d91337c24.us-east4-0.gcp.cloud.qdrant.io"
    api_key = os.environ["QDRANT_API_KEY"]
    qdrant_client = QdrantClient(
        url=qdrant_url,
        api_key=api_key,
    )

    all_results_concatenated = []
    for text in text_list:
        results = query_qdrant_vector_database(
            text=text, qdrant_client=qdrant_client, top=top, score_threshold=score_threshold
        )
        all_results_concatenated += results

    # Order by result.score
    all_results_concatenated = sorted(all_results_concatenated, key=lambda x: x.score, reverse=True)

    return all_results_concatenated

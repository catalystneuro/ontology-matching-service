import os 
import pickle
from pathlib import Path

import numpy as np 
import tiktoken
from langchain.embeddings.openai import OpenAIEmbeddings
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http import models



# Concatenate all the dataframes
import pandas as pd 

from cognitiveatlas.api import get_disorder
from cognitiveatlas.api import get_concept
from cognitiveatlas.api import get_task


all_tasks = get_task(silent=True)

all_tasks_df = all_tasks.pandas 

all_tasks_df["type"] = "task"
columns = ["id", "name", "definition_text", "alias", "type"]
all_tasks_df = all_tasks_df[columns]
all_tasks_df.head()
all_concepts = get_concept(silent=True)
all_concepts_df = all_concepts.pandas
all_concepts_df["type"] = "concept"

columns = ["id", "name", "definition_text", "alias", "type"]
all_concepts_df = all_concepts_df[columns]
all_concepts_df.head()
all_disorders = get_disorder(silent=True)

all_disorders_df = all_disorders.pandas
all_disorders_df["type"] = "disorder"
all_disorders_df["alias"] = ""
all_disorders_df["definition_text"] = all_disorders_df["definition"]
columns = ["id", "name", "definition_text", "alias", "type"]
all_disorders_df = all_disorders_df[columns]
all_disorders_df.head()

# There are 204 terms in disorders, so we have som extra ones here.
print(f"{all_tasks_df.shape=}, {all_concepts_df.shape=}, {all_disorders_df.shape=}")
all_data_df = pd.concat([all_tasks_df, all_concepts_df, all_disorders_df])
print(all_data_df.shape)
all_data_df.sample(n=5, random_state=42)


# Change the id to node_id, alias to synonyms, and definition_text to definition_text to definition in the columns of all_data_df
all_data_df.columns = ["node_id", "name", "definition", "synonyms", "type"]
all_data_df.head()
all_data_df["node_id"] = all_data_df["type"] + ":" + all_data_df["node_id"]
all_data_df["name"] = all_data_df["name"].str.strip()
all_data_df["definition"][all_data_df["definition"].isnull()] = ""
all_data_df["definition"] = all_data_df["definition"].str.strip()
all_data_df["synonyms"] = all_data_df["synonyms"].str.strip() 
all_data_df["synonyms"][all_data_df["synonyms"].isnull()] = ""
all_data_df["text_to_embed"] = all_data_df["name"] + " " + all_data_df["definition"] + " " + all_data_df["synonyms"]
assert all_data_df["text_to_embed"].isnull().sum() == 0

id_to_info = {}
for row in all_data_df.to_dict(orient="records"):
    node_info = {}
    node_info["id"] = row["node_id"]
    node_info["synonyms"] = row["synonyms"]
    node_info["definition"] = row["definition"]
    node_info["name"] = row["name"]
    node_info["parent_structure"] = []
    node_info["direct_parents"] = []  # Is_a relationship still not implemented
    node_info["text_to_embed"] = row["text_to_embed"]
    id_to_info[row["node_id"]] = node_info


# embedding model parameters
embedding_model = "text-embedding-ada-002"
embedding_encoding = "cl100k_base"  # this the encoding for text-embedding-ada-002
encoding = tiktoken.get_encoding(embedding_encoding)

text_to_embed = [node_info["text_to_embed"] for node_info in id_to_info.values()]
length_of_encoding_per_node = [len(encoding.encode(text)) for text in text_to_embed]
total_tokens = sum(length_of_encoding_per_node)
dollars_per_token = 0.0001 / 1000  #  Check the latest pricing to re-estimate this.
print(f"Total prize to embed {total_tokens * dollars_per_token: 2.4f} USD ")


ontology_name = "cognitiveatlas"
this_code_file_path = Path(__file__)
package_folder = this_code_file_path.parent.parent
pickle_file_path = package_folder / f"data/{ontology_name}_embeddings.pickle"

overwrite = True

if overwrite:
    # Remove file if it exists
    if pickle_file_path.is_file():
        os.remove(pickle_file_path)
        
if not pickle_file_path.is_file(): 
    print(f'creating ebmedings in {pickle_file_path.stem}')
    embedding_model = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
    documents = text_to_embed
    embeddings = embedding_model.embed_documents(documents)
    with open(pickle_file_path, 'wb') as f:
        pickle.dump(embeddings, f)
else:
    with open(pickle_file_path, 'rb') as f:
        embeddings = pickle.load(f)

embeddings = np.array(embeddings)
num_vectors, vector_size = embeddings.shape
print(f"{embeddings.shape=}")

qdrant_url = "ea062dec-cb5b-4320-82a7-3c99a9110bf9.europe-west3-0.gcp.cloud.qdrant.io:6333"
api_key = os.environ["QDRANT_API_KEY"]
client = QdrantClient(
    url=qdrant_url,
    api_key=api_key,
)

collection_name = ontology_name
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE, on_disk=True),
)   


batch_size = 100
points = []
for index, node_info in enumerate(tqdm(id_to_info.values())):

    # Create a point
    node_id = node_info["id"]
    id = index
    vector = embeddings[index]
    payload = node_info

    point = models.PointStruct(
        id=id,
        vector=vector.tolist(),
        payload=payload,
    )
    points.append(point)

    # If we have reached the batch size, upload the points
    if len(points) == batch_size:
        operation_info = client.upsert(
            collection_name=collection_name,
            wait=True,
            points=points
        )
        # Clear points list after upload
        points = []

# After all points are created, there might be some points that have not been uploaded yet
if points:
    operation_info = client.upsert(
        collection_name=collection_name,
        wait=True,
        points=points
    )
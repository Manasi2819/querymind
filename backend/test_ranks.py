import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path='C:/app/chroma_db')
collection = client.get_collection(name='user_1_sql_metadata')

query = "Give me records of hardware assigned to each of them"
query_embedding = model.encode(query).tolist()

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=30,
    include=['metadatas', 'distances']
)

print(f"Query: {query}\n")
for i in range(len(results['ids'][0])):
    table = results['metadatas'][0][i]['table_name']
    dist = results['distances'][0][i]
    print(f"{i+1}. {table} (Dist: {dist:.4f})")

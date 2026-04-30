import chromadb
client = chromadb.PersistentClient(path='C:/app/chroma_db')
collection = client.get_collection(name='user_1_sql_metadata')
res = collection.get(where={"table_name": "employee"})
if res["documents"]:
    for line in res["documents"][0].split("\n"):
        print(line)
else:
    print("Not found")

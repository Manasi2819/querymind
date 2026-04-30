import chromadb
client = chromadb.PersistentClient(path='../chroma_db')
for coll in client.list_collections():
    try:
        res = coll.get(where={"table_name": "employee"})
        if res["documents"]:
            print(f"Collection: {coll.name} - Found employee!")
            print(res["documents"][0])
    except:
        pass

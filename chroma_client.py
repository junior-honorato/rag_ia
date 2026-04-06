import os
import chromadb

class ChromaManager:
    def __init__(self):
        # Conecta a um banco local persistente na pasta 'chroma_db'
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection_name = "multimodal-rag-index"
        self.collection = None

    def ensure_index_exists(self, dimension=768):
        """Verifica ou Cria a coleção no ChromaDB."""
        print(f"Inicializando Banco Vetorial Local ChromaDB ('{self.collection_name}')...")
        # Configura espaço com distância Cosseno equivalente ao Pinecone
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_vector(self, vector_id, vector_values, metadata=None):
        """Realiza o upsert de um vetor no banco local."""
        if not self.collection:
            self.ensure_index_exists()
            
        meta = metadata if metadata else {}
        
        self.collection.upsert(
            ids=[vector_id],
            embeddings=[vector_values],
            metadatas=[meta]
        )
        print(f"[Upsert] Vetor ID '{vector_id}' armazenado localmente no ChromaDB!")

    def search_similar(self, query_vector, top_k=3):
        """Pesquisa vetores adjacentes e devolve formato de RAG."""
        if not self.collection:
            self.ensure_index_exists()
            
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["metadatas", "distances"]
        )
        
        reformatted_matches = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                # O Chroma (quando hnsw=cosine) devolve a distância de cosseno.
                # A similaridade pura (score de 0 a 1) é dada por 1 - distância.
                dist = results["distances"][0][i]
                sim_score = 1.0 - dist
                
                reformatted_matches.append({
                    "id": results["ids"][0][i],
                    "score": sim_score,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                })
                
        return {"matches": reformatted_matches}

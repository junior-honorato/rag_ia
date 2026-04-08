import os
import uuid
import chromadb

class ChromaManager:
    def __init__(self):
        # Conecta a um banco local persistente na pasta 'chroma_db'
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection_name = "multimodal-rag-index"
        self.collection = None
        self.cache_name = "semantic-cache"
        self.cache_collection = None

    def ensure_index_exists(self, dimension=768):
        """Verifica ou Cria a coleção no ChromaDB."""
        print(f"Inicializando Banco Vetorial Local ChromaDB ('{self.collection_name}')...")
        # Configura espaço com distância Cosseno equivalente ao Pinecone
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def ensure_cache_exists(self):
        """Prepara Coleção do Semantic Cache"""
        if not self.cache_collection:
            self.cache_collection = self.client.get_or_create_collection(
                name=self.cache_name,
                metadata={"hnsw:space": "cosine"}
            )

    def check_cache(self, query_vector, threshold=0.04):
        """Verifica se há pergunta parecida (distância < 0.04 = >96% similaridade)"""
        self.ensure_cache_exists()
        try:
            results = self.cache_collection.query(
                query_embeddings=[query_vector],
                n_results=1,
                include=["metadatas", "distances"]
            )
            if results and results.get("ids") and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
                dist = results["distances"][0][0]
                if dist <= threshold:
                    return results["metadatas"][0][0].get("answer_text")
        except:
            pass
        return None

    def save_to_cache(self, query_vector, answer_text, query_text):
        """Salva a resposta para uso futuro"""
        self.ensure_cache_exists()
        vid = f"c_{uuid.uuid4().hex[:12]}"
        self.cache_collection.upsert(
            ids=[vid],
            embeddings=[query_vector],
            metadatas=[{"answer_text": answer_text, "query": query_text}]
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

    def delete_by_file(self, filename):
        """Deleta fisicamente no banco ChromaDB todos os chunks que tenham essa origem."""
        if not self.collection:
            self.ensure_index_exists()
            
        try:    
            self.collection.delete(where={"original_file": filename})
            print(f"[🗑️  Delete] Vetores antigos de '{filename}' apagados DB.")
        except Exception as e:
            print(f"[Delete] Erro ao deletar '{filename}': {e}")

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

    def get_parent_content_by_file(self, filename, max_chars=5000):
        """Busca conteúdos Pais para gerar resumos retroativos sem PyPDFLoader"""
        if not self.collection:
            self.ensure_index_exists()
            
        try:
            results = self.collection.get(
                where={"original_file": filename},
                limit=30
            )
            
            texto_montado = ""
            unique_parents = set()
            
            if results and results.get("metadatas"):
                for meta in results["metadatas"]:
                    pid = meta.get("parent_id")
                    if pid and pid not in unique_parents:
                        unique_parents.add(pid)
                        texto_montado += meta.get("parent_content", "") + " "
                        if len(texto_montado) > max_chars:
                            break
                            
            return texto_montado[:max_chars]
        except Exception as e:
            print(f"Erro ao obter parent_content: {e}")
            return ""

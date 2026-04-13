import os
import mimetypes
from google import genai
from google.genai import types

def get_embedding(client, text=None, file_path=None):
    """
    Função utilitária para extrair embeddings usando o modelo gemini-embedding-2-preview.
    Pode aceitar texto ou caminhos de arquivos (imagens, áudio, vídeos, PDFs).
    Retorna o vetor (lista de floats) de tamanho especificado (768).
    """
    contents = []
    
    if text:
        contents.append(text)
        
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
            
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream' # Fallback
            
        part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        contents.append(part)
        
    if not contents:
        raise ValueError("Forneça um texto ou o caminho de um arquivo multimodal.")

    # A chamada de embedding:
    result = client.models.embed_content(
        model=os.environ.get("GEMINI_EMBEDDING_MODEL_NAME"),
        contents=contents,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    
    # Retorna o vetor gerado
    if result.embeddings:
        return result.embeddings[0].values
    else:
        raise Exception("Nenhum embedding retornado.")

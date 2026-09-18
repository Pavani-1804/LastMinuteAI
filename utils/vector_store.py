from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def create_vector_store(text):
    try:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=250)
        chunks = splitter.split_text(text)
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        batch_size = 150
        db = FAISS.from_texts(chunks[:batch_size], embeddings)
        for i in range(batch_size, len(chunks), batch_size):
            db.add_texts(chunks[i:i + batch_size])
            
        db.save_local("faiss_index")
        return len(chunks)
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return 0

import os
import re
import glob
import json
import hashlib
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import CSVLoader, PyPDFLoader
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_chroma import Chroma
from ai.constant import *

def load_registry(registry_path: str = None) -> Dict[str, Any]:
    path = registry_path or REGISTRY_PATH
    if not os.path.exists(path):
        return {"docs": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def save_registry(reg: Dict[str, Any], registry_path: str = None) -> None:
    path = registry_path or REGISTRY_PATH
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)

def normalize(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def infer_category(filename: str) -> str:
    name = filename.lower()
    if "camera" in name:
        return "camera"
    if "network" in name or "ethernet" in name:
        return "network"
    if "policy" in name:
        return "policy"
    if "anime" in name:
        return "anime"
    return "general"

def make_doc_id(filename: str, content_hash: str) -> str:
    return f"{normalize(filename)}__{content_hash[:12]}"

class CustomSemanticChunker:
    def __init__(self, embeddings, similarity_threshold=0.75, min_chunk_size=100, max_chunk_size=1500):
        self.embeddings = embeddings
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def split_into_sentences(self, text):
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def compute_similarity(self, text1, text2):
        if not text1.strip() or not text2.strip():
            return 0.0
        try:
            embeddings1 = self.embeddings.embed_query(text1)
            embeddings2 = self.embeddings.embed_query(text2)
            emb1 = np.array(embeddings1).reshape(1, -1)
            emb2 = np.array(embeddings2).reshape(1, -1)
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0
    
    def create_semantic_chunks_from_text(self, text):
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []
        
        chunks = []
        current_chunk = [sentences[0]]
        print(f"Processing {len(sentences)} sentences for semantic chunking...")
        
        for i in range(1, len(sentences)):
            current_chunk_text = " ".join(current_chunk)
            next_sentence = sentences[i]
            similarity = self.compute_similarity(current_chunk_text, next_sentence)
            potential_chunk = current_chunk + [next_sentence]
            potential_chunk_text = " ".join(potential_chunk)
            
            should_break = (
                similarity < self.similarity_threshold or 
                len(potential_chunk_text) > self.max_chunk_size
            )
            
            if should_break and len(current_chunk_text) >= self.min_chunk_size:
                chunks.append(current_chunk_text)
                current_chunk = [next_sentence]
            else:
                current_chunk.append(next_sentence)
            
            if i % 100 == 0:
                print(f"Processed {i}/{len(sentences)} sentences...")
        
        if current_chunk:
            final_chunk_text = " ".join(current_chunk)
            if len(final_chunk_text) >= self.min_chunk_size:
                chunks.append(final_chunk_text)
            elif chunks:
                chunks[-1] += " " + final_chunk_text
        
        return chunks
    
    def split(self, documents: List[Document]) -> List[Document]:
        all_chunks = []
        per_doc_counter: Dict[str, int] = {}
        
        for doc in documents:
            doc_id = doc.metadata.get("doc_id", "unknown_doc")
            per_doc_counter.setdefault(doc_id, 0)
            
            semantic_chunks = self.create_semantic_chunks_from_text(doc.page_content)
            
            for chunk_text in semantic_chunks:
                chunk_idx = per_doc_counter[doc_id]
                per_doc_counter[doc_id] += 1
                
                chunk_doc = Document(
                    page_content=chunk_text,
                    metadata={
                        **doc.metadata.copy(),
                        "chunk_id": f"{doc_id}::semantic_chunk{chunk_idx}",
                        "chunk_index": chunk_idx,
                        "chunking_method": "semantic"
                    }
                )
                all_chunks.append(chunk_doc)
        
        print(f"Created {len(all_chunks)} semantic chunks from {len(documents)} documents")
        return all_chunks

class FolderLoader:
    def __init__(self, file_types: Tuple[str, ...] = ("csv", "pdf")):
        self.file_types = file_types

    def list_paths(self, folder_path: str) -> List[str]:
        paths: List[str] = []
        for ext in self.file_types:
            paths.extend(glob.glob(os.path.join(folder_path, f"*.{ext}")))
        return sorted(paths)

    def load_file(self, path: str, base_meta: Dict[str, Any]) -> List[Document]:
        filename = os.path.basename(path)
        print(f"Loading file: {filename}")
        
        if filename.lower().endswith(".pdf"):
            pages = PyPDFLoader(path).load()
            for p in pages:
                p.metadata.update(base_meta)
            print(f"Loaded {len(pages)} pages from PDF")
            return pages

        if filename.lower().endswith(".csv"):
            csv_docs = CSVLoader(path).load()
            for d in csv_docs:
                d.metadata.update(base_meta)
            print(f"Loaded {len(csv_docs)} rows from CSV")
            return csv_docs
        
        return []
    
class Splitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def split(self, documents: List[Document]) -> List[Document]:
        chunks = self.splitter.split_documents(documents)
        per_doc_counter: Dict[str, int] = {}
        
        for ch in chunks:
            doc_id = ch.metadata.get("doc_id", "unknown_doc")
            per_doc_counter.setdefault(doc_id, 0)
            idx = per_doc_counter[doc_id]
            per_doc_counter[doc_id] += 1
            ch.metadata["chunk_id"] = f"{doc_id}::chunk{idx}"
            ch.metadata["chunk_index"] = idx
            ch.metadata["chunking_method"] = "standard"
        
        print(f"Created {len(chunks)} standard chunks from {len(documents)} documents")
        return chunks

class VectorDB:
    def __init__(self, embedding, persist_directory: str = DB_DIR, batch_size: int = 1000, semantic: bool = False, registry_path: str = None):
        self.semantic = semantic
        self.registry_path = registry_path or REGISTRY_PATH
        self.db = Chroma(
            persist_directory=persist_directory,
            collection_name=COLLECTION,
            embedding_function=embedding
        )
        self.reg = load_registry(self.registry_path)
        
        if self.semantic:
            self.splitter = CustomSemanticChunker(
                embeddings=embedding,
                similarity_threshold=0.75,
                min_chunk_size=100,
                max_chunk_size=1500
            )
        else:
            self.splitter = Splitter(chunk_size=500, chunk_overlap=50)
            
        self.loader = FolderLoader(file_types=("csv", "pdf"))
        self.batch_size = max(1, min(batch_size, 5000))

    def _safe_persist(self):
        """Safely persist the database, handling both old and new Chroma versions."""
        try:
            if hasattr(self.db, 'persist'):
                self.db.persist()
                print("Database persisted using persist() method")
            else:
                print("Database persistence is automatic in this Chroma version")
        except Exception as e:
            print(f"Warning: Could not persist database: {e}")

    def close(self):
        """Properly close the database connection"""
        try:
            # For newer ChromaDB versions, just clear references
            if hasattr(self.db, '_client') and self.db._client:
                try:
                    if hasattr(self.db._client, 'reset'):
                        self.db._client.reset()
                except:
                    pass
            # Clear main reference
            self.db = None
            print("Database connection closed")
        except Exception as e:
            print(f"Error closing database: {e}")

    def persist(self):
        self._safe_persist()
        save_registry(self.reg, self.registry_path)

    def _register(self, abs_path: str, filename: str, category: str, content_hash: str, doc_id: str, chunk_count: int, added_at: str):
        self.reg["docs"][abs_path] = {
            "doc_id": doc_id,
            "filename": filename,
            "abs_path": abs_path,
            "category": category,
            "content_hash": content_hash,
            "added_at": added_at,
            "chunk_count": chunk_count,
            "chunking_method": "semantic" if self.semantic else "standard"
        }

    def _add_documents_batched(self, docs: List[Document]):
        if not docs:
            print("No documents to add")
            return
            
        print(f"Adding {len(docs)} documents to vector store in batches of {self.batch_size}")
        
        max_retries = 3
        for i in range(0, len(docs), self.batch_size):
            batch = docs[i:i + self.batch_size]
            batch_num = i//self.batch_size + 1
            total_batches = (len(docs)-1)//self.batch_size + 1
            
            # Retry mechanism for each batch
            for retry in range(max_retries):
                try:
                    self.db.add_documents(batch)
                    print(f"✓ Added batch {batch_num}/{total_batches} ({len(batch)} docs)")
                    break  # Success, move to next batch
                    
                except Exception as e:
                    error_msg = str(e)
                    if retry < max_retries - 1:
                        wait_time = 2 * (retry + 1)  # 2, 4 seconds
                        print(f"✗ Batch {batch_num} failed (attempt {retry+1}/{max_retries}): {error_msg}")
                        print(f"  Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"✗ Batch {batch_num} failed after {max_retries} attempts")
                        raise Exception(f"Failed to add batch {batch_num} after {max_retries} retries: {error_msg}")
        
        print("All batches added successfully, persisting...")
        self._safe_persist()
        print("✓ Vector store persisted successfully")

    def ingest_file_incremental(self, path: str):
        abs_path = os.path.abspath(path)
        filename = os.path.basename(path)
        content_hash = sha256_file(path)
        existing = self.reg["docs"].get(abs_path)

        if existing and existing.get("content_hash") == content_hash:
            print(f"File {filename} unchanged, skipping...")
            return

        if existing and existing.get("doc_id") and existing.get("content_hash") != content_hash:
            print(f"Removing old version of {filename}")
            self.db.delete(where={"doc_id": existing["doc_id"]})
            self._safe_persist()

        doc_id = make_doc_id(filename, content_hash)
        category = infer_category(filename)
        added_at = utc_now_iso()

        base_meta = {
            "doc_id": doc_id,
            "filename": filename,
            "abs_path": abs_path,
            "category": category,
            "added_at": added_at,
            "content_hash": content_hash,
            "file_type": os.path.splitext(filename)[1].lstrip("."),
        }

        print(f"Processing {filename} with {'semantic' if self.semantic else 'standard'} chunking...")
        
        docs = self.loader.load_file(path, base_meta)
        
        if not docs:
            print(f"No content loaded from {filename}")
            return
            
        chunks = self.splitter.split(docs)
        
        if not chunks:
            print(f"No chunks created from {filename}")
            return
            
        self._add_documents_batched(chunks)
        self._register(abs_path, filename, category, content_hash, doc_id, len(chunks), added_at)
        self.persist()
        
        print(f"Successfully processed {filename}: {len(chunks)} chunks created")

    def ingest_folder_incremental(self, folder_path: str):
        print(f"Looking for files in: {folder_path}")
        
        if not os.path.exists(folder_path):
            print(f"ERROR: Folder does not exist: {folder_path}")
            return
            
        paths = self.loader.list_paths(folder_path)
        print(f"Found {len(paths)} files: {[os.path.basename(p) for p in paths]}")
        
        if not paths:
            print(f"No PDF/CSV files found in {folder_path}")
            return
            
        for i, p in enumerate(paths, 1):
            print(f"\n{'='*60}")
            print(f"Processing file {i}/{len(paths)}: {os.path.basename(p)}")
            print(f"{'='*60}")
            self.ingest_file_incremental(p)

    def add_document(self, path: str):
        self.ingest_file_incremental(path)

    def remove_by_doc_id(self, doc_id: str):
        self.db.delete(where={"doc_id": doc_id})
        self._safe_persist()
        to_del = [k for k, v in self.reg["docs"].items() if v.get("doc_id") == doc_id]
        for k in to_del:
            del self.reg["docs"][k]
        self.persist()

    def remove_by_filename(self, filename: str):
        matches = [v["doc_id"] for v in self.reg["docs"].values() if v.get("filename") == filename]
        for doc_id in matches:
            self.remove_by_doc_id(doc_id)

    def list_docs(self) -> List[Dict[str, Any]]:
        return sorted(self.reg["docs"].values(), key=lambda x: x.get("added_at", ""))

    def as_retriever(self, k: int = 4, meta_filter: Optional[Dict[str, Any]] = None):
        return self.db.as_retriever(search_type="mmr",search_kwargs={"k": k, "filter": meta_filter} if meta_filter else {"k": k})

    def as_hybrid_retriever(self, k: int = 4, sparse_k: int = 3, dense_weight: float = 0.7, sparse_weight: float = 0.3, meta_filter: Optional[Dict[str, Any]] = None):
        """
        Create a hybrid retriever that combines dense (semantic) and sparse (BM25) retrieval.
        
        Args:
            k: Number of documents to retrieve for dense retrieval
            sparse_k: Number of documents to retrieve for sparse retrieval  
            dense_weight: Weight for dense retriever (default 0.7)
            sparse_weight: Weight for sparse retriever (default 0.3)
            meta_filter: Optional metadata filter
            
        Returns:
            EnsembleRetriever combining dense and BM25 retrievers, or dense retriever if EnsembleRetriever unavailable
        """
        try:
            # Check if EnsembleRetriever is available
            if EnsembleRetriever is None:
                print("Warning: EnsembleRetriever not available, falling back to dense retriever")
                return self.db.as_retriever(search_kwargs={"k": k, "filter": meta_filter} if meta_filter else {"k": k})

            # Get dense retriever
            dense_retriever = self.db.as_retriever(search_kwargs={"k": k, "filter": meta_filter} if meta_filter else {"k": k})
            
            # Get documents from the vector database for BM25
            docs_data = self.db.get()
            if not docs_data or not docs_data['documents']:
                print("Warning: No documents found for BM25 retriever, falling back to dense only")
                return dense_retriever
            
            # Create Document objects for BM25
            documents = []
            for i, (doc_content, metadata) in enumerate(zip(docs_data['documents'], docs_data['metadatas'])):
                # Apply filter if provided
                if meta_filter:
                    match = True
                    for key, value in meta_filter.items():
                        if metadata.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                
                documents.append(Document(
                    page_content=doc_content,
                    metadata=metadata
                ))
            
            if not documents:
                print("Warning: No documents match the filter criteria, falling back to dense only")
                return dense_retriever
            
            # Create BM25 retriever
            sparse_retriever = BM25Retriever.from_documents(documents)
            sparse_retriever.k = sparse_k
            
            # Create ensemble retriever
            hybrid_retriever = EnsembleRetriever(
                retrievers=[dense_retriever, sparse_retriever],
                weights=[dense_weight, sparse_weight]
            )
            
            print(f"Created hybrid retriever with {len(documents)} documents (Dense: {dense_weight}, BM25: {sparse_weight})")
            return hybrid_retriever
            
        except Exception as e:
            print(f"Error creating hybrid retriever: {e}")
            print("Falling back to dense retriever only")
            return self.db.as_retriever(search_kwargs={"k": k, "filter": meta_filter} if meta_filter else {"k": k})

    def get_retriever(self, use_hybrid: bool = False, k: int = 4, **kwargs):
        """
        Get a retriever based on the specified type.
        
        Args:
            use_hybrid: If True, returns hybrid retriever, otherwise dense retriever
            k: Number of documents to retrieve
            **kwargs: Additional arguments for hybrid retriever (sparse_k, dense_weight, sparse_weight, meta_filter)
            
        Returns:
            Retriever instance (either dense or hybrid)
        """
        if use_hybrid:
            return self.as_hybrid_retriever(k=k, **kwargs)
        else:
            meta_filter = kwargs.get('meta_filter')
            return self.as_retriever(k=k, meta_filter=meta_filter)

    def view_chunks(self, limit=10):
        try:
            docs = self.db.get()
            
            print(f"\nTotal chunks in vector store: {len(docs['documents'])}")
            print("="*80)
            
            if len(docs['documents']) == 0:
                print("No chunks found in vector store!")
                return
            
            for i in range(min(limit, len(docs['documents']))):
                content = docs['documents'][i]
                metadata = docs['metadatas'][i]
                
                print(f"\nChunk {i+1}:")
                print(f"  Chunk ID: {metadata.get('chunk_id', 'N/A')}")
                print(f"  File: {metadata.get('filename', 'N/A')}")
                print(f"  Category: {metadata.get('category', 'N/A')}")
                print(f"  Method: {metadata.get('chunking_method', 'N/A')}")
                print(f"  Content preview:")
                print("-" * 40)
                print(content[:200] + "..." if len(content) > 200 else content)
                print("="*80)
                
        except Exception as e:
            print(f"Error viewing chunks: {e}")
            import traceback
            traceback.print_exc()

    def get_stats(self):
        try:
            docs = self.db.get()
            total_chunks = len(docs['documents'])
            
            print(f"\n=== Vector Store Statistics ===")
            print(f"Total chunks: {total_chunks}")
            
            if total_chunks > 0:
                # Count by chunking method
                chunking_methods = {}
                categories = {}
                files = {}
                
                for metadata in docs['metadatas']:
                    method = metadata.get('chunking_method', 'unknown')
                    chunking_methods[method] = chunking_methods.get(method, 0) + 1
                    
                    category = metadata.get('category', 'unknown')
                    categories[category] = categories.get(category, 0) + 1
                    
                    filename = metadata.get('filename', 'unknown')
                    files[filename] = files.get(filename, 0) + 1
                
                print(f"Files: {len(files)}")
                print(f"Chunking methods: {dict(chunking_methods)}")
                print(f"Categories: {dict(categories)}")
                print(f"Files processed: {list(files.keys())}")
            
        except Exception as e:
            print(f"Error getting stats: {e}")
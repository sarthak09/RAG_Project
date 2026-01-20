from typing import List
from flashrank import Ranker, RerankRequest
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document

class Reranker:
    def __init__(self, reranker_type: str = "flashrank"):
        self.reranker_type = reranker_type
        if reranker_type == "cross_encoder":
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        elif reranker_type == "bge":
            self.reranker = CrossEncoder('BAAI/bge-reranker-base')
        elif reranker_type == "flashrank":
            self.reranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")
        else:
            self.reranker = None

    def rerank_docs(self, question: str, docs: List[Document], top_k: int = 5):
        if not docs or self.reranker is None:
            return docs[:top_k]
        if self.reranker_type in ["cross_encoder", "bge"]:
            pairs = [(question, doc.page_content) for doc in docs]
            scores = self.reranker.predict(pairs)
            scored_docs = list(zip(docs, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, score in scored_docs[:top_k]]
        elif self.reranker_type == "flashrank":
            passages = [{"id": i, "text": doc.page_content} for i, doc in enumerate(docs)]
            request = RerankRequest(query=question, passages=passages)
            results = self.reranker.rerank(request)
            return [docs[r['id']] for r in results[:top_k]]
        return docs[:top_k]
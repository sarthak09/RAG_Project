from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class queryDecompose:
    def __init__(self):
        self.pquery_expansion_prompt = PromptTemplate.from_template("""
        You are an AI assistant. Decompose the following complex question into 2 to 4 smaller sub-questions for better document retrieval.

        Question: "{question}"

        Sub-questions:
        """)

    def expand_query(self, query, llm ):
        query_expansion_chain=self.pquery_expansion_prompt| llm | StrOutputParser()
        return query_expansion_chain.invoke({"question": query})
    
class queryExpansion:
    def __init__(self):
        self.pquery_expansion_prompt = PromptTemplate.from_template("""
        You are a helpful assistant. Expand the following query to improve document retrieval by adding relevant synonyms, technical terms, and useful context.

        Original query: "{query}"

        Expanded query:
        """)

    def expand_query(self, query, llm ):
        query_expansion_chain=self.pquery_expansion_prompt| llm | StrOutputParser()
        return query_expansion_chain.invoke({"query": query})
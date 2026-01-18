from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.prompts import ChatPromptTemplate

custom_prompt = ChatPromptTemplate.from_template("""Use the following context to answer the question. 
If you don't know the answer based on the context, say you don't know.
Provide specific details from the context to support your answer.

Context:
{context}

Question: {question}

Answer:""")


def format_docs(docs):
    return "\n\n".join(
        f"[file={d.metadata.get('filename')} page={d.metadata.get('page')} doc_id={d.metadata.get('doc_id')} chunk_id={d.metadata.get('chunk_id')}]\n{d.page_content}"
        for d in docs
    )

def build_rag_chain(llm_obj, retriever):
    def get_docs(q: str):
        return retriever.invoke(q)

    def get_context(q: str):
        docs = get_docs(q)
        return {"docs": docs, "context": format_docs(docs), "question": q}

    chain = RunnableParallel(
        answer=(
            RunnablePassthrough()
            | get_context
            | (lambda x: {"context": x["context"], "question": x["question"]})
            | custom_prompt
            | llm_obj.llm
            | StrOutputParser()
        ),
        context_docs=RunnablePassthrough() | get_context | (lambda x: x["docs"]),
        context_text=RunnablePassthrough() | get_context | (lambda x: x["context"]),
    )
    return chain
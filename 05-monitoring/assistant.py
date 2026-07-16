'''
PENDING MODULE FOR MODULE 5 [use the next url to check trace and monitoring] : 
[video] : https://www.youtube.com/watch?v=ImY5-Q97sRw&list=PL3MmuxUbc_hJAmLLf2x1LSKRKbZwKXoHd
[repo] : https://github.com/DataTalksClub/llm-zoomcamp/blob/main/05-monitoring/code/assistant.py
'''

import sys

from dotenv import load_dotenv
from openai import OpenAI

from ingest import load_faq_data, build_index
from metrics import RAGWithMetrics
from db_save import save_conversation

def create_assistant():
    load_dotenv()

    documents = load_faq_data()
    index = build_index(documents)

    return RAGWithMetrics(
        index=index,
        llm_client=OpenAI()
    )

if __name__ == "__main__":

    assistant = create_assistant()

    query = "How do I join the course?"
    if len(sys.argv) > 1:
        query = sys.argv[1]

    answer = assistant.rag(query)
    print(answer)

    save_conversation(assistant.last_call, query, "llm-zoomcamp")
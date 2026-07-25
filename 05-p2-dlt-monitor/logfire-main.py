# import logfire


# def main():
#     logfire.configure()
#     logfire.info('Hello, {place}!, this is a test', place='World')

# if __name__ == '__main__':
#     main()

from dotenv import load_dotenv
load_dotenv()
import os
print('has key:', 'OPENAI_API_KEY' in os.environ, len(os.environ.get('OPENAI_API_KEY','')))
from pydantic_ai.providers import infer_provider
p = infer_provider('openai-chat')
print("> e: ",os.environ.get('OPENAI_API_KEY',''))
print(p)
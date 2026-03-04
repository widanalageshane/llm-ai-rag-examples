from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI 

messages = [
    AIMessage(content="Hello, how can I assist you today?"),
    HumanMessage(content="Can you tell me a joke?"),
    AIMessage(content="Sure! Why don't scientists trust atoms? Because they make up everything!"),
    HumanMessage(content="That's funny! Can you tell me another one?")
]

for message in messages:
    print(message)


## Chat models interact via messages
## Lets use Gemini free tier as our chat model, this required ENV variable GOOGLE_API_KEY 
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
result = llm.invoke(messages)
print(result)
print("\n\n\nModel response content: ", result.content)







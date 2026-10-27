# scratch.py, in the same folder as chatbot.py
from chatbot import agent

print(agent.run_sync("hello").output)                                   # does the model alone work?
print(agent.run_sync("How do I get the Fisherman achievement?").output)  # does the tool call work?
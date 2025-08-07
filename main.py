from langgraph.graph import START, END, StateGraph, add_messages
from typing_extensions import TypedDict
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt, Command
from typing import Annotated
from prompt import linkedin_post_prompt
from langgraph.checkpoint.memory import MemorySaver
import uuid
from dotenv import load_dotenv
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()



class State(TypedDict):
    linkdln_post: str
    generated_post: Annotated[list[str], add_messages]
    human_feedback: Annotated[list[str], add_messages]

@tool
def web_search(topic: str):
    """Takes topic as the input and does websearch and returns the relevant information """

    print(f"Performing web search on {topic}")
    search = DuckDuckGoSearchRun()
    output = search.invoke(topic)

    return output

def human_feedback_method(state: State):
    "This takes state as input and takes human feedback for post"

    generated_post = state["generated_post"]
    user_feedback = interrupt(generated_post)
    if user_feedback.lower() == "done":
        return Command(update={"human_feedback": state["human_feedback"]+ ['finalised']},
                       goto=END)
    else:
         return Command(update={"human_feedback": [user_feedback]},
                                goto="chatbot")

tools=[web_search]
llm = init_chat_model(model_provider="OpenAI", model="gpt-4.1")
llm_with_tools = llm.bind_tools(tools=tools)

def chatbot(state: State)-> State:
    
    linkdln_post = state["linkdln_post"]
    human_feedback = state["human_feedback"][-1] if state["human_feedback"] else "No feedback yet"

    prompt = linkedin_post_prompt.format(linkdln_post=linkdln_post, human_feedback=human_feedback)
    response = llm_with_tools.invoke(prompt)
    generate_linkdln_post = response.content if response.content else "No content"

    return {
        "messages":[response],
        "linkdln_post": state["linkdln_post"],
        "generated_post": [generate_linkdln_post],
        "human_feedback": [human_feedback]

    }

tool_node = ToolNode(
    tools=[web_search]
)
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("human", human_feedback_method)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot",tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("chatbot","human")

def main():
    graph = graph_builder.compile()

# Print ASCII representation to console
    print(graph.get_graph().draw_ascii())
    checkpointer = MemorySaver()
    graph = graph_builder.compile(checkpointer)
    thread_config = {"configurable": {
        "thread_id": uuid.uuid4()
    }}
    user_input = input("> ")
    state = {
        "linkdln_post": user_input,
        "generated_post": [],
        "human_feedback": []
    }

    for chunk in graph.stream(state, config=thread_config):
        for node_id, value in chunk.items():

            if (node_id == "__interrupt__"):
                while True:
                    user_feedback = input(f"{chunk['__interrupt__'][0].value[0].content} \n\nPlease provide your feedback> ")
                    graph.invoke(Command(resume=user_feedback), config=thread_config)

                    if user_feedback.lower() == "done":
                        break


main()
                    






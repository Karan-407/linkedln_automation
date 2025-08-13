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
from ddgs import DDGS
from langchain_core.messages import ToolMessage
from linkedln_script import create_linkedin_post
import json

load_dotenv()


class State(TypedDict):
    messages: Annotated[list, add_messages]
    linkdln_post: str
    generated_post: Annotated[list[str], add_messages]
    human_feedback: Annotated[list[str], add_messages]
    ready_to_post: bool

@tool
def web_search(topic: str):
    """Takes topic as the input and does websearch and returns the relevant information """

    print(f"Performing web search on {topic}")
    with DDGS() as ddgs:
        output = ddgs.text(topic, max_results=5)

    return {"messages":[output]}

def human_feedback_method(state: State):
    "This takes state as input and takes human feedback for post"

    generated_post = state["generated_post"][-1].content
    user_feedback = interrupt(generated_post)
    if user_feedback.lower() == "approve":
        return Command(
            update={
                "human_feedback": state["human_feedback"] + ['approved'],
                "ready_to_post": True
            },
            goto="linkedln"
        )
    elif user_feedback.lower() == "done":
        return Command(
            update={"human_feedback": state["human_feedback"] + ['finished']},
            goto=END
        )
    else:
        return Command(
            update={
                "human_feedback": state["human_feedback"] + [user_feedback],
                "ready_to_post": False
            },
            goto="chatbot"
        )

tools=[web_search]
llm = init_chat_model(model_provider="OpenAI", model="gpt-4o")
llm_with_tools = llm.bind_tools(tools=tools)


def linkedln_post(state: State):
    try:
        if state["ready_to_post"] == True:
            content = state["generated_post"][-1].content
            create_linkedin_post(content=content)
    except Exception as er:
        return {
            "message": [f"Got unexpected error {er}"],
            "linkdln_post": state["linkdln_post"], 
            "generated_post": state["generated_post"],
            "human_feedback": state["human_feedback"] + [f"Error: {er}"]
        }
    finally:
        return Command(goto=END)

def chatbot_router(state: State):
    """Router function to handle both use cases dynamically"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    # Check if LLM wants to use tools (web search)
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"  # Use Case 1: Go to tools first
    else:
        return "human"  # Use Case 2: Go directly to human feedback

def human_router(state: State):
    """Router function to handle human feedback decisions"""
    last_feedback = state["human_feedback"][-1].content if state["human_feedback"] else ""
    
    if last_feedback == "approved":
        return "linkedln"  # Post to LinkedIn
    elif last_feedback == "finished":
        return "__end__"   # End the workflow
    else:
        return "chatbot"   # Go back for revision
 

def chatbot(state: State)-> State:
    
    tool_msgs = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
    if tool_msgs:
        tool_response_str = tool_msgs[0].content
    else:
        tool_response_str = "No data from tool"
    linkdln_post = state["linkdln_post"]
    human_feedback = state["human_feedback"][-1].content if state["human_feedback"] else "No feedback yet"

    prompt = linkedin_post_prompt.format(linkdln_post=linkdln_post, web_search_results=tool_response_str, human_feedback=human_feedback)
    response = llm_with_tools.invoke(prompt)
    generate_linkdln_post = response if response.content else "No content"

    return {
        "messages":[response],
        "linkdln_post": state["linkdln_post"],
        "generated_post": [generate_linkdln_post],
        "human_feedback": [human_feedback]

    }

tool_node = ToolNode(
    tools=tools
)
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("human", human_feedback_method)
graph_builder.add_node("linkedln", linkedln_post)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot",chatbot_router)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_conditional_edges("human", human_router)
graph_builder.add_edge("linkedln", END)

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
        "messages":[],
        "linkdln_post": user_input,
        "generated_post": [],
        "human_feedback": [],
        "ready_to_post": False
    }

    for chunk in graph.stream(state, config=thread_config):
        for node_id, value in chunk.items():

            if node_id == "__interrupt__":
                while True:
                    user_feedback = input(f"{chunk['__interrupt__'][0].value} \n\nPlease provide your feedback> ")
                    graph.invoke(Command(resume=user_feedback), config=thread_config)

                    if user_feedback.lower() == "done" or "approve":
                        break


main()
                    






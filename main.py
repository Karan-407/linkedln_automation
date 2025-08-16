import uuid
from typing import Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
import requests

# Note: The 'duckduckgo-search' library has been renamed to 'ddgs'.
# It's recommended to 'pip install -U ddgs' and use the new library.
from ddgs import DDGS

# Local imports from your other files
from prompt import linkedin_post_prompt, improve_user_query, summarize_text_query
from linkedin_script import create_linkedin_post


# Load environment variables from .env file
load_dotenv()


# --- State Definition ---
class State(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        messages: The list of messages that form the conversation history.
        topic: The initial user-provided topic for the LinkedIn post.
        generated_post: The latest version of the generated post content.
        feedback: The latest human feedback provided for revision.
        ready_to_post: A boolean flag to indicate if the post is approved.
    """

    messages: Annotated[list[BaseMessage], lambda x, y: x + y]
    topic: str
    generated_post: str
    feedback: str
    ready_to_post: bool
    tool_results: str


# --- Tools ---
@tool
def web_search(topic: str) -> str:
    """
    Takes a topic as input, performs a web search, and returns the top 5 results as a formatted string.
    This tool is used to gather current information or data for the LinkedIn post.
    """
    print(f"---TOOL: Performing web search for topic: '{topic}'---")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(topic, max_results=5)
            if not results:
                return "No results found."
            # Format results into a single, clean string for the LLM
            formatted_results = "\n\n".join(
                [f"Title: {r['title']}\nSnippet: {r['body']}" for r in results]
            )
            return formatted_results
    except Exception as e:
        print(f"Error during web search: {e}")
        return f"An error occurred during web search: {e}"

@tool
def fetch_url_data(url: str):
    """ This methods takes url as the input and returns the content
    """
    print(f"---TOOL: Performing get call for url: '{url}'---")
    output = requests.get(url=url)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(output.text, "html.parser")

    # Remove unwanted tags (scripts, styles, nav, etc.)
    for tag in soup(["script", "style", "header", "footer", "nav"]):
        tag.extract()

    page_text = soup.get_text(separator=" ", strip=True)
    return page_text


# --- Model and Tools Initialization ---
main_llm = ChatOpenAI(model="gpt-4o")
small_llm = ChatOpenAI(model="gpt-4o-mini")
tools = [web_search, fetch_url_data]
llm_with_tools = main_llm.bind_tools(tools)
tool_node = ToolNode(tools)

def improve_input(state: State) -> dict:
    """
    This method improves the input provide by the user
    """
    print("---AGENT: Improving the User Input---")
    topic = state["topic"]
    prompt = improve_user_query.format(topic=topic)
    response = small_llm.invoke(prompt)
    print(response.content)

    return {
        "messages": [HumanMessage(content=response.content)],
        "topic":response.content
    }

def summaries_text(text: str) -> str:
    """
    Takes text as an input summaries it and retuns the summary in less than 200 worda
    """
    prompt = summarize_text_query.format(text=text)
    summary = small_llm.invoke(prompt)
    return summary.content

# --- Graph Nodes ---
def agent(state: State) -> dict:
    """
    The main agent node. It invokes the LLM to either generate a post or decide to use a tool.
    """
    print("---AGENT: Generating post or deciding on tool use---")
    messages = state["messages"]
    topic = state["topic"]
    feedback = state["feedback"]
    tool_results = state["tool_results"]

    # Check for tool results in the message history

    if messages:
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg,"name", "")
                content = summaries_text(msg.content)
                if "fetch_url_data" in tool_name:
                    tool_results = f"Primary URL content:\n{content}"
                    search_snippets = [summaries_text(m.content) for m in messages 
                                       if isinstance(m, ToolMessage) and "web_search" in getattr(m, "name", "") ]
                    if search_snippets:
                        tool_results += "\n\nOptional enrichment:\n" + "\n".join(search_snippets)
                    break
                elif "web_search" in tool_name and "Primary URL content" not in tool_results:
                  tool_results = content

    # Format the prompt for the LLM
    prompt = linkedin_post_prompt.format(
        topic=topic, web_search_results=tool_results, feedback=feedback
    )

    # Create a new HumanMessage for this turn to not pollute the history
    invocation_messages = messages + [HumanMessage(content=prompt)]

    response = llm_with_tools.invoke(invocation_messages)

    # The agent returns new messages and the generated post content
    return {
        "messages": [response],
        "generated_post": response.content if response.content else "",
        "tool_results": tool_results
    }


def human_review(state: State) -> dict:
    """
    This node is a placeholder that signals the graph to wait for human input.
    The graph will be interrupted after this node runs.
    """
    print("---HUMAN REVIEW: Awaiting feedback---")
    # No state change needed here, just a point to pause.
    return {}


def post_to_linkedin(state: State) -> dict:
    """
    Posts the final, approved content to LinkedIn.
    """
    print("---ACTION: Posting to LinkedIn---")
    if state.get("ready_to_post"):
        post_content = state.get("generated_post")
        if not post_content:
            print("---ACTION: Failed. No post content found in the state.")
            return {}

        result = create_linkedin_post(content=post_content)
        if result.get("success"):
            print(f"Post successfully published! Post ID: {result.get('post_id')}")
        else:
            print(f"Failed to post. Error: {result.get('error')}")
            print(f"Details: {result.get('details')}")
    else:
        print("---ACTION: Skipped posting as post was not approved.---")
    return {}

def tools_condition_router(state: State):
    if isinstance(state, list):
        ai_message = state[-1]
    elif isinstance(state, dict) and (messages := state.get("messages", [])):
        ai_message = messages[-1]
    elif messages := getattr(state, messages, []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return ai_message.additional_kwargs["tool_calls"][0]['function']['name']
    return "__end__"

# --- Conditional Edges (Routers) ---
def after_human_review(state: State) -> str:
    """
    Router that directs the flow after human feedback is received.
    This runs when the graph is resumed after the interruption.
    """
    print("---ROUTER: Processing human feedback---")
    last_feedback = state.get("feedback", "").lower()

    if "approve" in last_feedback:
        print("---ROUTER: Feedback is 'approve'. Moving to post.---")
        return "post"
    elif "exit" in last_feedback:
        print("---ROUTER: Feedback is 'exit'. Ending workflow.---")
        return "end"
    else:
        print("---ROUTER: Revision feedback received. Returning to agent.---")
        return "revise"


# --- Graph Definition ---
graph_builder = StateGraph(State)

graph_builder.add_node("agent", agent)
graph_builder.add_node("tools", tool_node)
graph_builder.add_node("human_review", human_review)
graph_builder.add_node("post_to_linkedin", post_to_linkedin)
graph_builder.add_node("improve_input",improve_input)

graph_builder.set_entry_point("improve_input")
graph_builder.add_edge("improve_input","agent")

# This conditional edge checks if the LLM's last response was a tool call.
# The key "__end__" signifies the default path when no tools are called.
graph_builder.add_conditional_edges(
    "agent",
    tools_condition,
    {"tools": "tools", "__end__": "human_review"},
)
graph_builder.add_edge("tools", "agent")

# This conditional edge routes based on human feedback after the graph resumes.
graph_builder.add_conditional_edges(
    "human_review",
    after_human_review,
    {"post": "post_to_linkedin", "revise": "agent", "end": END},
)
graph_builder.add_edge("post_to_linkedin", END)

# --- Compile and Run ---
memory = MemorySaver()
# We interrupt the graph after the 'human_review' node to wait for input.
graph = graph_builder.compile(checkpointer=memory, interrupt_after=["human_review"])

print("\n--- LinkedIn Post Agent Graph ---")
print(graph.get_graph().draw_ascii())
print("---------------------------------\n")


def main():
    """
    Main function to run the interactive LinkedIn post generation agent.
    """
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    print("Welcome to the LinkedIn Post Generation Agent!")
    topic = input("What topic would you like to create a post about?\n> ")

    # Initial input to start the graph.
    initial_input = {
        "messages": [HumanMessage(content=f"Initial topic: {topic}")],
        "topic": topic,
        "feedback": "No feedback yet.",
        "tool_results": "No tools result"
    }

    while True:
        # Run the graph. It will execute until it hits the interrupt
        # or a terminal state (END).
        result = graph.invoke(initial_input, config=config)

        # The graph is now paused at the 'human_review' node.
        # The `result` dictionary holds the state at that point.
        generated_post = result.get("generated_post")
        if not generated_post:
            print(
                "\nAn unexpected error occurred, or the workflow finished prematurely."
            )
            break

        print(f"\n>>>>>> Generated Post <<<<<<\n\n{generated_post}")
        print("\n---------------------------------")
        print("Please provide your feedback.")
        user_feedback = input(
            "Type 'approve' to post, 'exit' to quit, or provide revision instructions.\n> "
        )


        if user_feedback.lower() == "exit":
            print("Exiting workflow.")
            break

        # **KEY FIX**: To resume correctly, we first update the state of the
        # paused graph with the new feedback, then we invoke it with `None`
        # to tell it to continue from where it left off.

        is_approved = "approve" in user_feedback.lower()

        # Update the state of the graph in the checkpointer
        graph.update_state(
            config,
            {"feedback": user_feedback, "ready_to_post": is_approved},
        )

        # Resume the graph from the interruption point.
        # We pass `None` as the input because the checkpointer already has the state.
        initial_input = None

        if is_approved:
            print("\nPost approved. Resuming to post to LinkedIn...")
            # This final invoke will resume from the interruption and run to the end.
            graph.invoke(None, config=config)
            print("\nWorkflow finished.")
            break

        # If not approved, the loop continues. The next `graph.invoke` will use
        # the updated state from the checkpointer to revise the post.


if __name__ == "__main__":
    main()
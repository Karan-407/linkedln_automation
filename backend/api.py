from fastapi import FastAPI
from pydantic import BaseModel
import uuid
from main import graph
from langchain_core.messages import HumanMessage
import uvicorn

sessions = {}

class GenerateRequest(BaseModel):
    query: str
    url: str
    temperature: float = 0.7

class EditRequest(BaseModel):
    user_feedback: str
    session_id: str

class PostRequest(BaseModel):
    session_id: str
    user_feedback: str

app = FastAPI()

@app.post("/generate")
async def generate_post(req: GenerateRequest):
    print(req)
    req = req.dict()
    session_id = str(uuid.uuid4())
    config = {"configurable":{"thread_id": session_id}}

    initial_input = {
        "messages": [HumanMessage(content=f"Initial topic: {req['query']}")],
        "topic": req["query"],
        "feedback": "No feedback yet.",
        "tool_results": "No tools result"
    }

    result = graph.invoke(initial_input, config=config)
    generated_post = result.get("generated_post", "")
    logs = ["Post generated successfully"]

    sessions[session_id] = {"config": config, "state": result}

    return {
        "session_id": session_id,
        "logs": logs,
        "generated_post": generated_post
    }

@app.post("/edit")
async def edit_state(req: EditRequest):
    req = req.dict()
    print(req)
    user_feedback = req["user_feedback"]
    is_approved = "approve" in user_feedback.lower()
    session_id = req["session_id"]
    config = {"configurable":{"thread_id": session_id}}

    # Update the state of the graph in the checkpointer
    graph.update_state(
            config,
            {"feedback": user_feedback, "ready_to_post": is_approved},
        )

    # Resume the graph from the interruption point.
    # We pass `None` as the input because the checkpointer already has the state.
    # is_approved = "approve" in user_feedback.lower()
    initial_input = None
    result = graph.invoke(initial_input, config=config)
    return { "state" : "result",
                 "generated_post": result["generated_post"]}

@app.post("/post")
async def post_to_linkedin(req: PostRequest):
    print("\nPost approved. Resuming to post to LinkedIn...")
    # This final invoke will resume from the interruption and run to the end.
    req = req.dict()
    session_id = req["session_id"]
    user_feedback = req["user_feedback"]
    is_approved = True
    config = {"configurable":{"thread_id": session_id}}
    graph.update_state(
            config,
            {"feedback": user_feedback, "ready_to_post": is_approved},
        )
    graph.invoke(None, config=config)
    print("\nWorkflow finished.")
    return {"state": "Posted"}

if __name__ == "__main__":
    uvicorn.run("api:app", port=8000, reload=True)


from fastapi import APIRouter
from pydantic import BaseModel
from agents.chat.chat import agent

router = APIRouter(tags=["Chat Agent"])

# CHAT AGENT
class ChatRequest(BaseModel):
    message: str

@router.post("/chat/")
def chat_endpoint(data: ChatRequest):
    user_message = data.message

    try:
        response = agent.run(user_message)
        return {
            "response": response
        }
    except Exception as e:
        return {"error": str(e)}
    
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    print("Client connected")

    try:
        while True:
            data = await ws.receive_text()
            print("Received price:", data)

            for client in clients:
                await client.send_text(data)
    except:
        clients.remove(ws)
        print("Client disconnected")

@app.get("/")
def root():
    return {"status": "WebSocket server running"}



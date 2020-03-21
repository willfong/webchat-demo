import os
import asyncio
import aioredis
from fastapi import FastAPI, HTTPException
#from fastapi.responses import HTMLResponse
#from .routers import login, messages
#from .services import util, statsd
from .services import util, redis
from starlette.websockets import WebSocket
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, JSONResponse, HTMLResponse

app = FastAPI()

# This is only really for serving test files. We would probably serve static
# files from S3 directly.
app.mount("/static", StaticFiles(directory="/app/app/static"), name="static")

#app.include_router(login.router, prefix="/login")
#app.include_router(messages.router, prefix="/messages")

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:5000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


html_ps = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws_pub = new WebSocket("ws://localhost:5000/publish");
            var ws_sub = new WebSocket("ws://localhost:5000/subscribe");
            ws_sub.onmessage = function(event) {
                console.log(event)
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws_pub.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    #return HTMLResponse(html)
    return HTMLResponse(html_ps)

# original example from https://fastapi.tiangolo.com/advanced/websockets/
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")

'''
# Using two endpoints instead of one to demonstrate pub/sub use case
@app.websocket("/publish")
async def publish(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        util.logger.warning(data)
        await redis.publish('channel:1', data)

@app.websocket("/subscribe")
async def subscribe(websocket: WebSocket):
    await websocket.accept()
    r = await aioredis.create_redis_pool(os.environ.get('REDIS_ENDPOINT_URL') or 'redis://redis')
    ch1, ch2 = await r.subscribe('channel:1', 'channel:2')
    assert isinstance(ch1, aioredis.Channel)
    assert isinstance(ch2, aioredis.Channel)
    async def reader(channel):
        util.logger.warning(channel)
        async for message in channel.iter():
            util.logger.warning(f"Got message from channel: {message}")
            websocket.send_text(message)
    asyncio.get_running_loop().create_task(reader(ch1))
'''
# Using two endpoints instead of one to demonstrate pub/sub use case
@app.websocket("/publish")
async def publish(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        util.logger.warning(f"Publishing: {data}")
        redis.publish('chat', data)

@app.websocket("/subscribe")
async def subscribe(websocket: WebSocket):
    await websocket.accept()
    subscription = redis.subscribe('chat')
    while True:
        if subscription:
            payload = subscription.get_message()
            util.logger.warning(f"Received: {payload}")
            await websocket.send_text(payload.get('data'))

@app.get("/log-output-test")
#@statsd.statsd_root_stats
def log_output_test():
    util.logger.debug("logging debug")
    util.logger.info("logging info")
    util.logger.warn("logging warning")
    util.logger.error("logging error")
    return {"msg": "Logging output"}
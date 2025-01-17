"""
All this file does is take the requests and forwrads them but changes a single parameter which is body['n']
  and also truncates prompts that are too long (because open soruce models have a shorter context size than Codex (GitHub Copilot)

More functionality should be added later such as keep track of context of multiple files and maintaining a user session,
  but this would need lots of experimenting.

    pip install -U httpx -U fastapi -U uvicorn -U websockets
    python middleware.py --port 8000

"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import os

# Check if the platform is not Windows
if os.name != 'nt':
    from signal import SIGPIPE, SIG_DFL, signal
    signal(SIGPIPE,SIG_DFL)

app = FastAPI()


@app.post("/v1/engines/codegen/completions")
async def code_completion(body: dict):
    body["n"] = 1
    if "max_tokens" in body:
        del body["max_tokens"]

    # FIXME: this is just a hardcoded number, but this should actually use the tokenizer to truncate
    body["prompt"] = body["prompt"][-4000:]
    print("making request. body:", {k: v for k, v in body.items() if k != "prompt"})

    def code_completion_stream(body: dict):
        # define the generator for streaming
        async def stream_content():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for i in range(body["n"]):
                        async with client.stream(
                            "POST",
                            "http://localhost:5001/v1/codegen/completions",
                            json=body,
                            headers={
                                "Accept": "application/json",
                                "Content-type": "application/json",
                            },
                        ) as response:
                            # Check if the response status is not successful
                            if response.status_code != 200:
                                raise HTTPException(
                                    status_code=response.status_code,
                                    detail="Failed to fetch from the target endpoint",
                                )

                            # Stream the response content
                            async for chunk in response.aiter_bytes():
                                # print('getting chunk')
                                print(f"{chunk=}")
                                yield chunk
            except httpx.ReadTimeout:
                print("A timeout occurred while reading data from the server.")

        return StreamingResponse(stream_content(), media_type="application/json")

    if "stream" in body and body["stream"]:
        return code_completion_stream(body)
    else:
        raise NotImplementedError

def main():
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()

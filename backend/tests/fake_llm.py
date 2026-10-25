"""Protocol-faithful fakes for Ollama, OpenAI-compatible and Anthropic HTTP APIs."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

Responder = Callable[[dict], str]


def ollama_transport(
    reply: Responder | str, models=("llama-test:latest",), fail: int | None = None, calls: list | None = None
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.12.0"})
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": m,
                            "model": m,
                            "size": 2_000_000_000,
                            "details": {"family": "llama", "parameter_size": "3B"},
                        }
                        for m in models
                    ]
                },
            )
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            if calls is not None:
                calls.append(body)
            if fail:
                return httpx.Response(fail, json={"error": "boom"})
            text = reply(body) if callable(reply) else reply
            words = text.split(" ")
            lines = [
                json.dumps(
                    {
                        "message": {"role": "assistant", "content": w + (" " if i < len(words) - 1 else "")},
                        "done": False,
                    }
                )
                for i, w in enumerate(words)
            ]
            lines.append(
                json.dumps(
                    {
                        "message": {"role": "assistant", "content": ""},
                        "done": True,
                        "prompt_eval_count": 321,
                        "eval_count": len(words),
                    }
                )
            )
            return httpx.Response(
                200,
                content=("\n".join(lines) + "\n").encode(),
                headers={"content-type": "application/x-ndjson"},
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def openai_transport(reply: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "gpt-test"}]})
        if request.headers.get("authorization") != "Bearer sk-good":
            return httpx.Response(401, json={"error": {"message": "bad key"}})
        events = [
            f"data: {json.dumps({'choices': [{'delta': {'content': w + ' '}}]})}\n\n" for w in reply.split()
        ]
        events.append(
            f"data: {json.dumps({'choices': [], 'usage': {'prompt_tokens': 50, 'completion_tokens': 7}})}\n\n"
        )
        events.append("data: [DONE]\n\n")
        return httpx.Response(
            200, content="".join(events).encode(), headers={"content-type": "text/event-stream"}
        )

    return httpx.MockTransport(handler)


def anthropic_transport(reply: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["anthropic-version"] == "2023-06-01"
        body = json.loads(request.content)
        assert "system" in body and all(m["role"] != "system" for m in body["messages"])
        frames = [("message_start", {"type": "message_start", "message": {"usage": {"input_tokens": 40}}})]
        frames += [
            (
                "content_block_delta",
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": w + " "}},
            )
            for w in reply.split()
        ]
        frames.append(("message_delta", {"type": "message_delta", "usage": {"output_tokens": 9}}))
        frames.append(("message_stop", {"type": "message_stop"}))
        content = "".join(f"event: {e}\ndata: {json.dumps(d)}\n\n" for e, d in frames)
        return httpx.Response(200, content=content.encode(), headers={"content-type": "text/event-stream"})

    return httpx.MockTransport(handler)

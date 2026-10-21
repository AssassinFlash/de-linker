"""Debit each transport attempt, including SDK retries and model tool loops."""

from __future__ import annotations

import asyncio

import httpx
import httpx2
from linker_judges.budget import Provider, take


class Transport(httpx.BaseTransport):
    def __init__(
        self, provider: Provider, inner: httpx.BaseTransport | None = None
    ) -> None:
        self.provider = provider
        self.inner = inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        take(self.provider)
        return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()


class AsyncTransport(httpx.AsyncBaseTransport):
    def __init__(
        self, provider: Provider, inner: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.provider = provider
        self.inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await asyncio.to_thread(take, self.provider)
        return await self.inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self.inner.aclose()


class OpenAITransport(httpx2.AsyncBaseTransport):
    """The installed OpenAI SDK uses HTTPX 2; the direct clients use HTTPX 0.28."""

    def __init__(self, inner: httpx2.AsyncBaseTransport | None = None) -> None:
        self.inner = inner or httpx2.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        await asyncio.to_thread(take, "deepseek")
        return await self.inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self.inner.aclose()

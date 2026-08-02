"""Cloudflare-Python-Worker-Einstiegspunkt für GenericParser 0.3."""

import asgi
from workers import WorkerEntrypoint

from generic_parser.cloudflare_v03 import app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)

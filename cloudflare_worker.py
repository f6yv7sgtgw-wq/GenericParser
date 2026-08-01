"""Cloudflare-Python-Worker-Einstiegspunkt für GenericParser 0.2c."""

import asgi
from workers import WorkerEntrypoint

from generic_parser.cloudflare_app import app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)

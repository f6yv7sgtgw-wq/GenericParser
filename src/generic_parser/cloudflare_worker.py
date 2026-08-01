"""Cloudflare-Python-Worker-Einstiegspunkt für GenericParser 0.2d.1."""

import asgi
from workers import WorkerEntrypoint

from . import cloudflare_app

# Die Deployment-Fassung meldet die aktuelle Release-Candidate-Version.
cloudflare_app.VERSION = "0.2.0rc3"
app = cloudflare_app.app


class Default(WorkerEntrypoint):
    """ASGI-Brücke zwischen Cloudflare Workers und der FastAPI-Anwendung."""

    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)

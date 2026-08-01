"""Cloudflare-Python-Worker-Einstiegspunkt für GenericParser 0.2d."""

import asgi
from workers import WorkerEntrypoint

import generic_parser.cloudflare_app as cloudflare_app

# Die Deployment-Fassung meldet die Release-Candidate-Version von 0.2d.
cloudflare_app.VERSION = "0.2.0rc2"
app = cloudflare_app.app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)

"""Deployment entry: private project RPC plus the unchanged site engine app."""

from .app import app as legacy
from .planning.http_host import EngineApplications, configured_private_app

app = EngineApplications(legacy, configured_private_app())

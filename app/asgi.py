"""Entry point for uvicorn: uvicorn app.asgi:app"""
import logging

from .config import Settings
from .main import create_app
from .paystack import FakePaystack, PaystackClient
from .service import TicketService
from .store import build_store

logging.basicConfig(level=logging.INFO)

settings = Settings.from_env()
store = build_store(settings)
paystack = PaystackClient(settings.paystack_secret_key) if settings.paystack_mode == "paystack" else FakePaystack()
service = TicketService(store, paystack, settings)
app = create_app(service, settings)

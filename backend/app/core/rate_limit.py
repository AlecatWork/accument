"""A speed limit for the API, so nobody can hammer it with thousands of requests."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
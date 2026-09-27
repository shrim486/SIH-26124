"""Bounded login throttling for the single-process local API launcher."""
from collections import OrderedDict
from threading import Lock
from time import monotonic
from fastapi import HTTPException


class LoginAttempts:
    def __init__(self, limit=5, window=300):
        self.limit, self.window = limit, window
        self.entries, self.lock = OrderedDict(), Lock()

    def check(self, address):
        now = monotonic()
        with self.lock:
            attempts = [stamp for stamp in self.entries.pop(address, []) if now-stamp < self.window]
            self.entries[address] = attempts
            if len(attempts) >= self.limit:
                delay = max(1, int(self.window-(now-attempts[0]))+1)
                raise HTTPException(429, 'Too many sign-in attempts. Please wait and try again.', headers={'Retry-After':str(delay)})
            attempts.append(now)
            while len(self.entries) > 4096:
                self.entries.popitem(last=False)

    def clear(self, address):
        with self.lock:
            self.entries.pop(address, None)

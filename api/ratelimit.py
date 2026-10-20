"""Sign-in failure rate limiting (SCRUM-9).

Counts failed attempts in a sliding window, per client IP and per account,
and refuses further attempts once a limit is reached. A successful sign-in
clears the account's counter so a legitimate user is not locked out by
their own earlier typos.

State lives in this process. That is correct for a single API instance,
which is what Render runs today. If the API ever scales to several
instances the counters need a shared store (Redis); that is a separate card.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable

WINDOW_SECONDS = 15 * 60
MAX_FAILURES_PER_ACCOUNT = 5
MAX_FAILURES_PER_IP = 20


class FailureLimiter:
    """Sliding-window failure counter keyed by any string (an IP, an email)."""

    def __init__(
        self, limit: int, window: int = WINDOW_SECONDS, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window = window
        self.clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        events = self._events[key]
        cutoff = self.clock() - self.window
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    def retry_after(self, key: str) -> int:
        """Seconds until ``key`` may try again, or 0 if it is not limited."""
        events = self._prune(key)
        if len(events) < self.limit:
            return 0
        return max(1, int(events[0] + self.window - self.clock()) + 1)

    def record_failure(self, key: str) -> None:
        self._prune(key).append(self.clock())

    def clear(self, key: str) -> None:
        self._events.pop(key, None)


by_account = FailureLimiter(MAX_FAILURES_PER_ACCOUNT)
by_ip = FailureLimiter(MAX_FAILURES_PER_IP)

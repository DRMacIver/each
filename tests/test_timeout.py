import signal
import time

import pytest
from mock import MagicMock

from each.junkdrawer import Timeout, timeout


def test_does_not_attempt_to_reset_signal_if_signal_fails(monkeypatch):
    sig = MagicMock(side_effect=ValueError)

    monkeypatch.setattr(signal, "signal", sig)

    with pytest.raises(ValueError):
        with timeout(1):
            pass

    assert sig.call_count == 1


def test_will_time_out():
    start = time.monotonic()
    with pytest.raises(Timeout):
        with timeout(0.01):
            time.sleep(10)
    assert time.monotonic() <= start + 0.5


def test_will_recover_from_a_timeout_in_finally(monkeypatch):
    calls = 0

    def sig(*args):
        pass

    signal.signal(signal.SIGALRM, sig)

    assert signal.getsignal(signal.SIGALRM) is sig

    def setitimer(*args):
        nonlocal calls
        assert signal.getsignal(signal.SIGALRM) is not sig
        calls += 1
        if calls == 2:
            raise Timeout()

    monkeypatch.setattr(signal, "setitimer", setitimer)

    with timeout(1):
        assert signal.getsignal(signal.SIGALRM) is not sig

    assert signal.getsignal(signal.SIGALRM) is sig
    assert calls == 3

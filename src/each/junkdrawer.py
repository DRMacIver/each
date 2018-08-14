import signal
from contextlib import contextmanager


class Timeout(Exception):
    pass


def timeout_sigh(signum, frame):
    raise Timeout()


@contextmanager
def timeout(seconds):
    previous = None
    try:
        previous = signal.signal(signal.SIGALRM, timeout_sigh)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        while True:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
                if previous is not None:
                    signal.signal(signal.SIGALRM, previous)
                break
            except Timeout:
                pass

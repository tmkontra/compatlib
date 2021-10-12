import asyncio

from compatlib import compat

def coro():
    yield

@compat.after(3, 4)
def main() -> None:
    asyncio.get_event_loop().run_until_complete(coro())
    return 3.4

@compat.after(3, 7)
def main() -> None:
    asyncio.run(coro())
    return 3.7

assert main() == 3.4
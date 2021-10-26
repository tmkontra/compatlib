# compatlib

Easily write backwards-and-forwards compatible libraries.

# Overview

If you have a library, you may want it to run across multiple python release versions. You might want to _prefer_ certain features that aren't available in older versions. Use compatlib to keep your code clean.

# Usage

```python3
import asyncio
from compatlib import compat

@compat.after(3, 4)
def main() -> None:
    asyncio.get_event_loop().run_until_complete(coro())
    return 3.4

@compat.after(3, 7)
def main() -> None:
    asyncio.run(coro())
    return 3.7
```

compatlib will resolve the latest-usable version at runtime, by comparing the overloaded methods with the interpreter `sys.version_info`.

When running the above code on python 3.6, it will use the first `main`. If you run it on python 3.7 it will run the second `main`.

# Acknowledgement

Thanks to @wesselb for authoring the great [plum](https://github.com/wesselb/plum) multiple dispatch library, which `compatlib` uses as the basis of its decorator implementation. Instead of dispatching on type signatures, it dispatches on `sys.version_info` tuples.

# TODO

- Support dispatching on versions of libraries. 
- Support dispatching on the presence of an attribute (effectively, a _boolean_ dispatcher)

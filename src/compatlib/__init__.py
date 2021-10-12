from functools import wraps
import functools
import sys
from typing import Sequence
import plum
from plum import Dispatcher, ClassFunction, Function as _Function
from plum.function import _BoundFunction
from plum.util import *
import heapq

# cache the interpreter version info
sys_ver_info = sys.version_info

def _invoke_bound(self, ver_info):
    @wraps(self.f._f)
    def wrapped_method(*args, **kw_args):
        method = self.f.invoke(ver_info)
        return method(self.instance, *args, **kw_args)

    return wrapped_method

_BoundFunction.invoke = _invoke_bound

class Function(_Function):
    """Dispatch a function based on python version info
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def register(self, method, ver_info):
        self._pending.append((method, ver_info))

    def __call__(self, *args, **kw_args):
        # First resolve pending registrations, because the value of
        # `self._runtime_type_of` depends on it.
        if len(self._pending) != 0:
            self._resolve_pending_registrations()
        
        dispatch_version = kw_args.pop('override_ver_info', sys_ver_info)
        try:
            # Attempt to use cache. This will also be done in
            # `self.resolve_method`, but checking here as well speed up
            # cached calls significantly.
            method = self._cache[dispatch_version]
            return method(*args, **kw_args)
        except KeyError:
            method = self.resolve_method(dispatch_version)
            return method(*args, **kw_args)
    
    def invoke(self, ver_info):
        """Invoke a method for a particular sys.version_info.

        Args:
            ver_info: sys.version_info to resolve.

        Returns:
            function: Method.
        """
        method = self.resolve_method(ver_info)

        @wraps(self._f)
        def wrapped_method(*args, **kw_args):
            return method(*args, **kw_args)

        return wrapped_method

    def _get_method_for_version(self, ver_info):
        for ver_key, method in reversed(list(self._methods.items())):
            if ver_key <= ver_info:
                break
        return method

    def resolve_method(self, ver_info):
        """Get the method and return type corresponding to types of arguments.

        Args:
            *types (type): Types of arguments.

        Returns:
            tuple: Tuple containing method and return type.
        """
        # New registrations may invalidate cache, so resolve pending
        # registrations first.
        self._resolve_pending_registrations()

        # Attempt to use cache.
        try:
            return self._cache[ver_info]
        except KeyError:
            pass

        if self._owner:
            try:
                method = self._get_method_for_version(ver_info)
            except plum.NotFoundLookupError as e:
                method = None

                # Walk through the classes in the class's MRO, except for this
                # class, and try to get the method.
                for c in self._owner.mro()[1:]:
                    try:
                        method = getattr(c, self._f.__name__)

                        # Ignore abstract methods.
                        if (
                            hasattr(method, "__isabstractmethod__")
                            and method.__isabstractmethod__
                        ):
                            method = None
                            continue

                        # We found a good candidate. Break.
                        break
                    except AttributeError:
                        pass

                if method == object.__init__:
                    # The constructor of `object` has been found. This
                    # happens when there a constructor is called and no
                    # appropriate method can be found. Raise the original
                    # exception.
                    raise e

                if not method:
                    # If no method has been found after walking through the
                    # MRO, raise the original exception.
                    raise e
        else:
            # Not in a class. Simply resolve.
            method = self._get_method_for_version(ver_info)

        # Cache lookup.
        self._cache[ver_info] = method
        return method

    def _resolve_pending_registrations(self):
        # Keep track of whether anything registered.
        registered = False

        # Perform any pending registrations.
        for f, ver_info in self._pending:
            registered = True

            # If a method with the same signature has already been defined, then that
            # is fine: we simply overwrite that method.

            # If the return type is `object`, then set it to `default_obj_type`. This
            # allows for a fast check to speed up cached calls.

            self._methods[ver_info] = f
            # self._precedences[signature] = precedence

            # Add to resolved registrations.
            self._resolved.append((f, ver_info))

        if registered:
            methods = list(self._methods.items())
            heapq.heapify(methods)
            self._methods = dict(methods)
            self._pending = []

            # Clear cache.
            # TODO: Be more clever, but careful about the tracking of parametric types.
            self.clear_cache(reregister=False)

class Compat(Dispatcher):
    """A namespace for functions."""

    def __init__(self):
        self._functions = {}
        self._classes = {}

    def after(self, *ver: Sequence[int]):
        """Decorator for after a particular version.
        Args:
            precedence (int, optional): Precedence of the signature. Defaults to `0`.
        Returns:
            function: Decorator.
        """
        def decorate(func):
            def construct_function(owner):
                return self._add_method(
                    func,
                    owner=owner,
                    ver_info=tuple(ver)
                )

            # Defer the construction if `method` is in a class. We defer the construction to
            # allow the function to hold a reference to the class.
            if is_in_class(func):
                return ClassFunction(get_class(func), construct_function)
            else:
                return construct_function(None)
        return decorate

    def _get_function(self, method, owner) -> Function:
        name = method.__name__

        # If a class is the owner, use a namespace specific for that class. Otherwise,
        # use the global namespace.
        if owner:
            if owner not in self._classes:
                self._classes[owner] = {}
            namespace = self._classes[owner]
        else:
            namespace = self._functions

        # Create a new function only if the function does not already exist.
        if name not in namespace:
            namespace[name] = Function(method, owner=owner)

        return namespace[name]

    def _add_method(self, method, owner, ver_info):
        f = self._get_function(method, owner)
        f.register(method, ver_info)
        return f

    def clear_cache(self):
        """Clear cache."""
        for f in self._functions.values():
            f.clear_cache()


compat = Compat()

"""
Module:        repl.py
Description:   Provides conveinent functions for interactive 
               python (repl) sessions in ANSI terminals.

Author:        Nathan W. Barros
Date Created:  2026-10-13 21:37:01
Last Modified: 2026-10-27 16:18:35
Version:       1.0.1
License:       MIT License
Dependencies:  psutil

Usage:
    ~$ python3
    >>> import repl
    >>> repl.help()
"""

__author__ = "Nathan W. Barros"
__version__ = "1.0.1"



# Allow imports ONLY for interactive sessions
import sys
if not hasattr(sys, "ps1") and not sys.flags.interactive:
    raise ImportError( "repl is only for interactive sessions.")

# Check 3rd party dependency
try:
    import psutil
except ImportError:
    psutil = None
    print("WARNING> psutil not installed. repl.lsmem() not available.")
    
_DEFAULT_GLOBS: list[str] = [
    "__name__",
    "__doc__",
    "__package__",
    "__loader__",
    "__spec__",
    "__builtins__",
    "repl"
]

_PROTECTED_GLOBS: list[str] = []

# _real_sizeof() variables
_FUNC  = type(lambda: 0)
_CODE  = type((lambda: 0).__code__)
_ATOMS = (str, int, float, bool, bytes, bytearray, type(None))
_BOXES = (list, tuple, set, frozenset)

def help() -> None:
    doc = """
    REPL
    ===========================================================================

        help()              Display this message

        reset()             Remove all but protected & default global variables

        clear()            Erase the entire terminal screen & scrollback

        protect()           Protect a global variable from being reset

        unprotect()         Remove a global variable's protected status

        lsglob()            List all global variables and their type

        lsprot()            List all protected variables and their type

        lsfunc()            List all user-defined functions

        lsvars()            List all user-defined variables

        lsmods()            List all imported modules

        lsmem(verbose)      List memory usage; verbose: include every variable

        Notes
        -----------------------------------------------------------------------
        > REPL is only available during interactive python sessions
        > REPL does not support [import *]; use [import repl] instead
    """
    print(doc)

def reset() -> None:
    """ Reset global variables except initial & protected """

    ns = _ns()
    default_globs   = {glob: ns[glob] for glob in _DEFAULT_GLOBS if glob in ns}
    protected_globs = {glob: ns[glob] for glob in _PROTECTED_GLOBS if glob in ns}
    
    ns.clear()
    ns.update(default_globs)
    ns.update(protected_globs)

def clear() -> None:
    """ Clear the ANSI terminal screen """

    sys.stdout.write(
            "\033[1;1H" # cursor to top left
            "\033[2J"   # clear screen 
            "\033[3J"   # clear scrollback
    )
    sys.stdout.flush()

def protect(name: str) -> None:
    _PROTECTED_GLOBS.append(name)

def unprotect(name: str) -> None:
    _PROTECTED_GLOBS.remove(name)

def lsglob() -> None:
    """ display global vars with types to terminal """

    print(f"{'Name':<20} {'Type':<20}", "-"*40, sep="\n")
    for name, obj in sorted(_ns().items()):
        obj_type = type(obj).__name__ if name not in _DEFAULT_GLOBS else "default"
        print(f"{name:<20} {obj_type:<20}")

def lsprot() -> None:
    """ display protected vars with types to terminal"""

    ns = _ns()
    pdict = {glob: ns[glob] for glob in _PROTECTED_GLOBS if glob in ns}

    print("Protected Globals", "-"*40, sep="\n")
    for name, obj in sorted(pdict.items()):
        print(f"{name:<20} {type(obj).__name__:<20}")
    

def lsfunc() -> None:
    """ display user-defined functions to terminal """

    print("Functions", "-"*40, sep="\n")
    for name, obj in sorted(_ns().items()):
        if name in _DEFAULT_GLOBS: continue
        if type(obj).__name__ == "function":
            print(f"{name:<20}")


def lsvars() -> None:
    """ display user-defined variables with type to terminal """

    print("Variables", "-"*40, sep="\n")
    for name, obj in sorted(_ns().items()):
        if name in _DEFAULT_GLOBS: continue
        obj_type = type(obj).__name__
        if obj_type not in ("function", "module", "type"):
            print(f"{name:<20} {obj_type:<20}")


def lsmods() -> None:
    """ display user-imported modules to terminal """

    print("Modules", "-"*40, sep="\n")
    for name, obj in sorted(_ns().items()):
        if name in _DEFAULT_GLOBS: continue
        if type(obj).__name__ == "module":
            print(f"{name:<20}")

def lsmem(verbose: bool = False) -> None:
    """Displays memory usage. AI influenced."""

    if psutil is None:
        print("repl.lsmem() not available: psutil not installed.\n"
              "Run: pip install psutil")
        return
    
    rss = psutil.Process().memory_info().rss
    if not verbose:
        print(f"Process RSS: {_humanize_bytes(rss)} ({rss:,}) bytes")
        return
    
    seen = set()
    mods = {}
    for name, mod in list(sys.modules.items()):
        if name == "__main__" or type(mod).__name__ != "module":
            continue
        top = name.split(".")[0]
        mods[top] = mods.get(top, 0) + _module_size(mod, seen)

    skip = set(_DEFAULT_GLOBS)
    objs = []
    for name, obj in list(_ns().items()):
        obj_type = type(obj).__name__
        if name in skip or obj_type == "module":
            continue
        objs.append( (name, obj_type, _real_sizeof(obj, seen)))

    module_total = sum(mods.values())
    object_total = sum(size for _, _, size in objs)
    other_total  = max(0, rss - module_total - object_total)

    _mem_table("MODULES", [(n, "module", s) for n,s in mods.items()])
    _mem_table("USER VARIABLES", objs)

    print(
        f"\n{'Modules':<38}{_humanize_bytes(module_total):>12}\n"
        f"{'Variables':<38}{_humanize_bytes(object_total):>12}\n"
        f"{'Untracked':<38}{_humanize_bytes(other_total):>12}\n"
        f"{'TOTAL':<38}{_humanize_bytes(rss):>12}\n\n"
    
        "WARNING> Estimates from sys.getsizeof; C-extension memory not visible."
    )

def _ns() -> dict:
    """Return the main programs global namespace"""
    return sys.modules["__main__"].__dict__

def _mem_table(title, rows) -> None:
    """Display a table for lsmem() command output"""

    print(
        f"\n{title}\n"
        f"{'Name':<24}{'Type':<14}{'Size':>12}\n"
        f"{'-'*50}")
    for name, type_, size in sorted(rows, key=lambda r: r[2], reverse=True):
        print(f"{name:<24}{type_:<14}{_humanize_bytes(size):>12}")

def _humanize_bytes(size: int) -> str:
    """ convert bytes into human readable str """

    for unit in ("bytes", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}" if unit != "bytes" else f"{size} bytes"
        size /= 1024

def _real_sizeof(obj, seen: set) -> int:
    """Return the total memory used by an object. AI generated."""

    # Stop double counting
    oid = id(obj)
    if oid in seen: return 0
    seen.add(oid)

    size = sys.getsizeof(obj)

    if isinstance(obj, _ATOMS) or type(obj).__name__ == "module":
        return size
    if isinstance(obj, _BOXES):
        size += sum(_real_sizeof(x, seen) for x in obj)
    elif isinstance(obj, _CODE):
        size += sum(_real_sizeof(c, seen) for c in obj.co_consts)
        size += sum(_real_sizeof(n, seen) for n in obj.co_names)
    elif isinstance(obj, _FUNC):
        size += _real_sizeof(obj.__code__, seen)
        size += _real_sizeof(obj.__defaults__, seen)
        size += _real_sizeof(obj.__dict__, seen)
    elif isinstance(obj, dict):
        size += sum(_real_sizeof(k, seen) + _real_sizeof(v, seen) for k,v in obj.items())
    elif isinstance(obj, type):
        size += sum(_real_sizeof(v, seen) for v in vars(obj).values())
    else:
        if hasattr(obj, "__dict__"):
            size += _real_sizeof(obj.__dict__, seen)
        for cls in type(obj).__mro__:
            s = cls.__dict__.get("__slots__", ())
            for name in ((s,) if isinstance(s, str) else s):
                if hasattr(obj, name):
                    size += _real_sizeof(getattr(obj, name), seen)

    return size

def _module_size(mod, seen: set) -> int:
    """Return the total memory used by a module. AI generated."""

    name = mod.__name__
    book = mod.__dict__
    size = _real_sizeof(book, set()) if False else sys.getsizeof(book)

    for val in list(book.values()):
        if type(val).__name__ == "module":
            continue # counted under it's own name
        if not isinstance(val, _ATOMS) and getattr(val, "__module__", name) != name:
            continue # imported from elsewhere
        size += _real_sizeof(val, seen)
    
    return size

# EOF

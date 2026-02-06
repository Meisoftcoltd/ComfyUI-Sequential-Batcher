import sys
import os
import textwrap
import code

from . import register_node


@register_node
class Stringify:
    """Convert any input to str/repr."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "x": ("*", ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("str", "repr")
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Debug"

    def go(self, x):
        return (str(x), repr(x))


class RestoreStdStreams(object):
    # ComfyUI-Manager patches sys.stdout and sys.stder
    # which breaks GNU Readline support and makes the
    # REPL annoying to use. This context manager temporarily
    # puts back the originals.

    def __enter__(self):
        self._stdout, self._stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
        self._stdout.flush(); self._stderr.flush()

    def __exit__(self, exc_type, exc_value, traceback):
        _stdout, _stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = self._stdout, self._stderr
        _stdout.flush(); _stderr.flush()


EOF = 'Ctrl-Z plus Return' if os.sep == '\\' else 'Ctrl-D (i.e. EOF)'
MESSAGE = f"Press {EOF} to continue processing."


class Quitter:
    # Replace exit() and quit() to make sure the user exits with EOF
    # otherwise the whole server gets terminated.

    def __repr__(self):
        return MESSAGE

    def __call__(self):
        print(MESSAGE)


@register_node
class Interact:
    """
    Opens an interactive REPL whenever the node is evaluated.

    SECURITY WARNING: This node allows arbitrary code execution.
    To enable it, you must set the environment variable:
    COMFYUI_SB_ENABLE_INTERACTIVE_DEBUG=1
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {},
            "optional": {x: "*" for x in ('a', 'b', 'c', 'd')},
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "interact"
    CATEGORY = "🔁 Sequential Batcher/Debug"
    OUTPUT_NODE = True

    def interact(self, **kwargs):
        if os.environ.get("COMFYUI_SB_ENABLE_INTERACTIVE_DEBUG", "").lower() not in ("true", "1", "yes"):
            print(f"[{self.__class__.__name__}] Interactive debugging is disabled. Set COMFYUI_SB_ENABLE_INTERACTIVE_DEBUG=1 to enable.")
            return ()

        if sys.__stdout__.isatty():
            with RestoreStdStreams():
                code.interact(
                    banner=textwrap.dedent(f"""
                        Interactive debugging started.
                        Try `print(a)`.
                        {MESSAGE}
                    """),
                    exitmsg="Resuming workflow...",
                    local={
                        **kwargs,
                        'quit': Quitter(),
                        'exit': Quitter()
                    }
                )
        else:
            # Don't block the server if there is no tty.
            print("Skipping interactive prompt because there is no tty.")
        return ()

import collections
import itertools
import csv
import os

from . import register_node


@register_node
class MakeBatch:
    """Turns a sequence into a batch with one attribute."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "sequence": ("SEQUENCE", ),
                "name": ("STRING", {"default": ''}),
            },
        }

    RETURN_TYPES = ("BATCH", "INT")
    RETURN_NAMES = ("batch", "count")
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Batch"

    def merge_dicts(self, *dicts):
        #return collections.ChainMap(*reversed(dicts))
        return dict(itertools.chain.from_iterable(d.items() for d in dicts))

    def go(self, sequence, name):
        result = [{name: value} for value in sequence]
        return (result, len(result))


@register_node
class CombineBatches(MakeBatch):
    """Combines multiple batches."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "a": ("BATCH", ),
                "method": (("zip", "product"), {"default": "zip"}),
            },
            "optional": {
                x: ("BATCH", ) for x in ('b', 'c', 'd', 'e')
            }
        }

    def go(self, method, **kwargs):
        method = {'product': itertools.product, 'zip': zip}[method]
        result = [self.merge_dicts(*steps) for steps in method(*kwargs.values())]
        return (result, len(result))


@register_node
class EnumerateBatch(MakeBatch):
    """Combines multiple batches."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "batch": ("BATCH", ),
                "name": ("STRING", {"default": ''}),
            },
        }

    def go(self, batch, name):
        result = [self.merge_dicts(step, {name: n}) for n, step in enumerate(batch)]
        return (result, len(result))


@register_node
class GetBatchStep:
    """Gets the batch step by number."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "batch": ("BATCH", ),
                "step": ("INT", {"default": 0}),
                "wrap": (("repeat", "clamp"), {"default": "repeat"}),
            },
        }
    RETURN_TYPES = ("ATTRIBUTES", )
    RETURN_NAMES = ("attributes", )
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Batch"

    def go(self, batch, step, wrap):
        if wrap == 'repeat':
            while step < 0:
                step += len(batch)
            step = step % len(batch)
        elif wrap == 'clamp':
            step = max(min(step, len(batch)-1), 0)
        return (batch[step], )


@register_node
class FormatAttributes:
    """Applies attributes to a format string."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "attributes": ("ATTRIBUTES",),
                "format": ("STRING", {'default': '', 'multiline': True, "dynamicPrompts": False})
            },
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("string", )
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Batch"

    def go(self, attributes, format):
        return (format.format(**attributes), )


class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


@register_node
class GetAttribute:
    """Gets a named attribute from a step."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "attributes": ("ATTRIBUTES", ),
                "name": ("STRING", {"default": ''}),
            },
        }

    RETURN_TYPES = (AnyType("*"), )
    RETURN_NAMES = ("value", )
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Batch"

    def go(self, attributes, name):
        return (attributes[name], )


# Dynamically register typed attribute getters to avoid wildcard bug
# https://github.com/comfyanonymous/ComfyUI/pull/770
for t in ('INT', 'FLOAT', 'STRING'):
    register_node(type(
        'GetAttribute'+t.title(),
        (GetAttribute, ),
        {
            'RETURN_TYPES': (t, ),
        }
    ))




@register_node
class LoadCSV:
    """Loads a CSV file into a batch."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "path": ("STRING", {"default": "prompt.csv"}),
                "delimiter": (["comma", "tab", "semicolon"], {"default": "comma"}),
                "quotechar": (["\"", "'"], {"default": "\""}),
            },
            "optional": {
                "index": ("INT", {"default": -1, "min": -1, "max": 999999}),
            }
        }

    RETURN_TYPES = ("BATCH", "ATTRIBUTES", "INT")
    RETURN_NAMES = ("batch", "current_attributes", "count")
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Batch"

    def go(self, path, delimiter, quotechar, index=-1):
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV file not found: {path}")

        delim = {
            "comma": ",",
            "tab": "\t",
            "semicolon": ";",
        }[delimiter]

        batch = []
        with open(path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=delim, quotechar=quotechar)
            for row in reader:
                # Clean up keys and values
                clean_row = {k.strip() if k else k: v.strip() if v else v for k, v in row.items()}
                batch.append(clean_row)

        count = len(batch)
        current_attributes = batch[index % count] if count > 0 and index != -1 else (batch[0] if count > 0 else {})

        return (batch, current_attributes, count)


@register_node
class BatchToList:
    """Converts a batch into a list."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "batch": ("BATCH",),
            },
        }

    RETURN_TYPES = ("ATTRIBUTES",)
    RETURN_NAMES = ("attributes",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Batch"

    def go(self, batch):
        return (batch,)

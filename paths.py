import pathlib
import glob
from folder_paths import folder_names_and_paths
from . import register_node


folder_types = tuple(sorted(folder_names_and_paths.keys()))
folder_default = "checkpoint" if "checkpoint" in folder_types else folder_types[0]

@register_node
class ModelFinder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filenames": ("SEQUENCE", ),
                "model_type": (folder_types, {"default": folder_default}),
                "recursive": ("BOOLEAN", {"default": True}),
                "skip_missing": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("SEQUENCE", "SEQUENCE")
    RETURN_NAMES = ("paths", "stems")
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Sequence"

    def find_models(self, fn, paths, recursive):
        for p in paths:
            for f in (p.rglob(fn) if recursive else p.glob(fn)):
                yield f.relative_to(p)

    def go(self, filenames, model_type, recursive, skip_missing):
        paths = [pathlib.Path(folder) for folder in folder_names_and_paths[model_type][0]]

        available_files = []
        file_index = {}
        for p in paths:
            for f in (p.rglob('*') if recursive else p.glob('*')):
                try:
                    rel = f.relative_to(p)
                    available_files.append(rel)
                    if rel.name not in file_index:
                        file_index[rel.name] = []
                    file_index[rel.name].append(rel)
                except ValueError:
                    pass

        result = []
        for fn in filenames:
            if '..' in fn:
                raise Exception(f'".." is not allowed: {fn}.')

            candidates = []
            if glob.has_magic(fn):
                for f in available_files:
                    if f.match(fn):
                        candidates.append(f)
            else:
                potential = file_index.get(pathlib.Path(fn).name, [])
                for f in potential:
                    if f.match(fn):
                        candidates.append(f)

            if candidates:
                result.extend(candidates)
            elif not skip_missing:
                raise Exception(f'Could not find file: {fn}')

        return ([str(f) for f in result], [f.stem for f in result])

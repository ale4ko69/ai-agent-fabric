"""Run the Fabric CLI directly from a development checkout.

Installed releases use their global launcher for normal operations. This helper is the
source-versioned installer entry point for first installation, reviewed cross-version
bootstrap and launcher delegation. It does not itself create state without an invoked
state-changing command.
"""

import sys


if sys.argv[1:3] == ["project", "install"]:
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise SystemExit("project install requires python -I -S -B scripts/run-fabric.py")

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# Project-only bootstrap читает .py напрямую: -B запрещает запись, но не чтение чужого .pyc.
if sys.argv[1:3] == ["project", "install"]:
    import stat
    from importlib.abc import MetaPathFinder
    from importlib.machinery import PathFinder, SourceFileLoader

    class SourceOnlyLoader(SourceFileLoader):
        def get_code(self, fullname):
            # Проверка до первого runtime-импорта: связанный src не должен успеть исполниться.
            origin = Path(self.path)
            for path in (*reversed(origin.parents), origin):
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise ImportError("Fabric source imports cannot use links or reparse points")
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ImportError("Fabric source imports require regular, non-hard-linked files")
            return self.source_to_code(origin.read_bytes(), self.path)

    class FabricSourceFinder(MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "ai_agent_fabric" or fullname.startswith("ai_agent_fabric."):
                spec = PathFinder.find_spec(fullname, path)
                if spec is not None:
                    if not isinstance(spec.loader, SourceFileLoader):
                        raise ImportError("Fabric source imports require versioned Python source")
                    spec.loader = SourceOnlyLoader(fullname, spec.origin)
                return spec
            return None

    sys.meta_path.insert(0, FabricSourceFinder())
sys.path.insert(0, str(ROOT / "src"))

from ai_agent_fabric.__main__ import main


if __name__ == "__main__":
    main()

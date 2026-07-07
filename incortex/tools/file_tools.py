"""File tools — sandboxed read and write (Design_Doc §18.3).

Both tools are confined to a root directory: any path that resolves
outside it — traversal tricks, absolute paths, symlink hops — is rejected
at validation time, before anything touches the filesystem.
"""

from pathlib import Path

from incortex.tools.base_tool import BaseTool

DEFAULT_MAX_READ_BYTES = 1_000_000


class _SandboxedFileTool(BaseTool):
    def __init__(self, root):
        self._root = Path(root).resolve()

    def _resolve(self, relative_path):
        """The sandbox wall: the resolved target must stay under the root."""
        target = (self._root / relative_path).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError(f"{self.name}: path escapes the sandbox")
        return target

    def _validate_path(self, request):
        path = request.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"{self.name}: 'path' must be a non-empty string")
        self._resolve(path)


class ReadFileTool(_SandboxedFileTool):
    name = "read_file"
    description = "read a text file inside the sandbox"
    permission_level = 1  # read-only action (Design_Doc §12.9)
    harm_probability = 0.05
    impact = 0.1

    def __init__(self, root, max_bytes=DEFAULT_MAX_READ_BYTES):
        super().__init__(root)
        self._max_bytes = max_bytes

    def validate(self, request):
        super().validate(request)
        self._validate_path(request)

    def _execute(self, request):
        target = self._resolve(request["path"])
        if target.stat().st_size > self._max_bytes:
            raise ValueError(f"file too large (over {self._max_bytes} bytes)")
        return {"path": request["path"],
                "content": target.read_text(errors="replace")}


class WriteFileTool(_SandboxedFileTool):
    name = "write_file"
    description = "write a text file inside the sandbox"
    permission_level = 2  # local safe write (Design_Doc §12.9)
    harm_probability = 0.1
    impact = 0.3

    def validate(self, request):
        super().validate(request)
        self._validate_path(request)
        if not isinstance(request.get("content"), str):
            raise ValueError(f"{self.name}: 'content' must be a string")

    def _execute(self, request):
        target = self._resolve(request["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(request["content"])
        return {"path": request["path"],
                "bytes_written": len(request["content"].encode("utf-8"))}

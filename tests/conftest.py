"""Pytest config + a Windows compatibility shim for gltest's direct runner.

gltest 0.29.2's direct loader wires the GenVM message onto fd 0 by dup2'ing a
temp file, then unconditionally `os.unlink()`s that temp file while fd 0 still
holds it open (see gltest/direct/loader.py::_inject_message_to_fd0). On POSIX,
unlinking an open file is legal; on Windows it raises PermissionError
[WinError 32], which aborts every direct-mode deploy.

By the time the unlink runs, fd 0 is already correctly pointing at the encoded
message, so the failure is cleanup-only. We wrap that single loader function and
swallow the Windows-only PermissionError; the tiny temp file is released and
reclaimed by the OS once fd 0 is restored / the process exits.

This shim is a no-op on non-Windows platforms and does not touch any GenLayer
contract API — it only patches a temp-file cleanup path in the test harness.
"""

import os


def _install_windows_fd0_shim() -> None:
    if os.name != "nt":
        return
    from gltest.direct import loader

    if getattr(loader, "_seedling_fd0_shim", False):
        return

    _original = loader._inject_message_to_fd0

    def _safe(vm):
        try:
            _original(vm)
        except PermissionError:
            # fd 0 is already wired to the message; only the temp-file
            # unlink failed (Windows can't delete a still-open file).
            pass

    loader._inject_message_to_fd0 = _safe
    loader._seedling_fd0_shim = True


_install_windows_fd0_shim()

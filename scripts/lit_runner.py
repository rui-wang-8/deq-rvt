#!/usr/bin/env python3
"""lit wrapper with in-process (sequential) execution for -j1.

lit >= 18 always creates a multiprocessing.Pool, even for a single worker,
and the pool needs POSIX named semaphores (backed by /dev/shm). In
environments where /dev/shm is unavailable (containers, sandboxes), pool
creation fails with PermissionError. When the requested parallelism is 1,
this wrapper runs the tests directly in the lit process instead, which is
semantically equivalent and avoids multiprocessing entirely.

Usage: python3 lit_runner.py <lit arguments...>
"""
import sys
import time

import lit.main
import lit.run
import lit.worker


def _execute_sequential(self, deadline):
    self._increase_process_limit()
    # Same shared data the pool workers would receive.
    lit.worker.initialize(self.lit_config, {})
    for test in self.tests:
        if time.time() >= deadline:
            raise lit.run.TimeoutError()
        lit.worker.execute(test)
        self.progress_callback(test)
        if test.isFailure():
            self.failures += 1
            if self.failures == self.max_failures:
                raise lit.run.MaxFailuresError()


def requested_workers(argv):
    """Return the value of the last -j/--workers argument (argparse uses
    the last occurrence), or None if not given."""
    workers = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-j", "--workers") and i + 1 < len(argv):
            try:
                workers = int(argv[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        elif arg.startswith("--workers="):
            try:
                workers = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg.startswith("-j") and len(arg) > 2 and arg[2:].isdigit():
            workers = int(arg[2:])
        i += 1
    return workers


def main():
    if (requested_workers(sys.argv[1:]) or 1) == 1:
        lit.run.Run._execute = _execute_sequential
    lit.main.main()


if __name__ == "__main__":
    main()

from contextlib import contextmanager
import warnings

import dask
from .threadpoolexecutor import secede, rejoin
from .worker import thread_state, get_client, get_worker
from .utils import parse_timedelta


@contextmanager
def worker_client(timeout=None, separate_thread=True):
    """Get client for this thread

    This context manager is intended to be called within functions that we run
    on workers.  When run as a context manager it delivers a client
    ``Client`` object that can submit other tasks directly from that worker.

    Parameters
    ----------
    timeout: Number or String
        Timeout after which to error out
        default: dash.config.get(distributed.comm.timeouts.connect)
        Ex: get_client(timeout=10) or get_client(timeout="10s")
    separate_thread: bool, optional
        Whether to run this function outside of the normal thread pool
        defaults to True

    Examples
    --------
    >>> def func(x):
    ...     with worker_client() as c:  # connect from worker back to scheduler
    ...         a = c.submit(inc, x)     # this task can submit more tasks
    ...         b = c.submit(dec, x)
    ...         result = c.gather([a, b])  # and gather results
    ...     return result

    >>> future = client.submit(func, 1)  # submit func(1) on cluster

    See Also
    --------
    get_worker
    get_client
    secede
    """

    if timeout is None:
        timeout = dask.config.get("distributed.comm.timeouts.connect")

    timeout = parse_timedelta(timeout, "s")

    worker = get_worker()
    client = get_client(timeout=timeout)
    if separate_thread:
        secede()  # have this thread secede from the thread pool
        worker.loop.add_callback(
            worker.transition, worker.tasks[thread_state.key], "long-running"
        )

    yield client

    if separate_thread:
        rejoin()


def local_client(*args, **kwargs):
    warnings.warn("local_client has moved to worker_client")
    return worker_client(*args, **kwargs)

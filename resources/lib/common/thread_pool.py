import concurrent.futures
from functools import reduce
from resources.lib.common import tools
from resources.lib.modules.globals import g


class ThreadPoolExecutor(concurrent.futures.ThreadPoolExecutor):
    """
    Extends the ThreadPoolExecutor to support cancelling futures on shutdown.
    """

    import queue

    def shutdown(self, wait=True, *, cancel_futures=False):
        """
        Clean-up the resources associated with the Executor.

        :param wait: If True, shutdown will not return until all running futures have finished executing and the
                     resources used by the executor have been reclaimed.
        :param cancel_futures: If True, cancels all pending futures that the executor has not started running.
                               Completed or running futures won’t be cancelled.
        """
        with self._shutdown_lock:
            self._shutdown = True
            if cancel_futures:
                # Drain all work items from the queue and cancel their associated futures.
                while True:
                    try:
                        work_item = self._work_queue.get_nowait()
                    except self.queue.Empty:
                        break
                    if work_item is not None:
                        work_item.future.cancel()

            # Prevent threads from blocking permanently.
            self._work_queue.put(None)
        if wait:
            for t in self._threads:
                t.join()


class ThreadPool:
    """
    Helper class to simplify creating and managing a thread pool.
    """

    # Worker scaling levels: Default, Low, Medium, High, Extreme
    scaled_workers = [20, 10, 20, 40, 80]

    def __init__(self):
        self.limiter = g.get_bool_runtime_setting("threadpool.limiter")
        self.workers = self.scaled_workers[g.get_int_setting("general.threadpoolScale", -1) + 1]
        self.max_workers = 1 if self.limiter else self.workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.tasks = []

    def __del__(self):
        self.executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _handle_results(results):
        """
        Handle results from futures and merge or collect them appropriately.
        
        :param results: An iterable of results from futures.
        :return: Merged or collected results.
        """
        result_iter = iter(results)

        for result in result_iter:
            if result is not None:
                break
        else:
            return None

        if isinstance(result, dict):
            return reduce(tools.smart_merge_dictionary, result_iter, result)
        elif isinstance(result, (list, set)):
            result_list = list(result)
            for result in result_iter:
                if result is not None:
                    if isinstance(result, list):
                        result_list.extend(result)
                    else:
                        result_list.append(result)
            return result_list
        else:
            return [result for result in result_iter if result is not None]

    def put(self, func, *args, **kwargs):
        """
        Adds a task to the executor and starts it running.

        :param func: The function to run as a task.
        :type func: callable
        :param args: Arguments for the function.
        :param kwargs: Keyword arguments for the function.
        """
        self.tasks.append(self.executor.submit(func, *args, **kwargs))

    def wait_completion(self):
        """
        Waits for the completion of all tasks, raises any exceptions if present, and returns the results.

        :return: The results of all tasks.
        :raises: The first exception raised if any task fails.
        """
        try:
            for task in concurrent.futures.as_completed(self.tasks):
                if exception := task.exception():
                    self.executor.shutdown(wait=False, cancel_futures=True)
                    raise exception

            results = self._handle_results(task.result() for task in self.tasks if task)
            self.tasks.clear()
            return results
        except Exception:
            g.log_stacktrace()
            self.executor.shutdown(wait=False, cancel_futures=True)
            raise

    def map_results(self, func, args_iterable=None, kwargs_iterable=None):
        """
        Takes iterables for args and kwargs, runs func with them, gathers the results, and returns them in order.

        :param func: The function to execute.
        :param args_iterable: An iterable of argument tuples.
        :param kwargs_iterable: An iterable of keyword argument dictionaries.
        :return: The results.
        """
        try:
            return self._handle_results(
                self.executor.map(lambda args, kwargs: func(*args, **kwargs), args_iterable, kwargs_iterable)
                if args_iterable and kwargs_iterable
                else self.executor.map(lambda kwargs: func(**kwargs), kwargs_iterable)
                if kwargs_iterable
                else self.executor.map(lambda args: func(*args), args_iterable)
            )
        except Exception:
            self.executor.shutdown(wait=False, cancel_futures=True)
            g.log_stacktrace()
            raise

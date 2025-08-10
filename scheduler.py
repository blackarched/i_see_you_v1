"""
A robust, thread-safe task scheduler for running periodic functions.

This module provides a Scheduler class that can manage multiple background
tasks, ensuring they can be started, stopped, and removed cleanly.
"""

import threading
import time
import logging

class Scheduler:
    """Manages periodic execution of tasks in background threads."""

    def __init__(self):
        """Initializes the Scheduler."""
        self.tasks = {}  # Stores tasks with a unique name
        self.lock = threading.Lock()
        self.logger = logging.getLogger('scheduler')

    def add_task(self, name: str, func, interval: int):
        """
        Adds a function to be executed periodically.

        If a task with the same name already exists, it will be replaced.

        Args:
            name (str): A unique name to identify the task.
            func: The function to execute.
            interval (int): The interval in seconds between executions.
        """
        if not callable(func):
            self.logger.error("Provided task for '%s' is not a callable function.", name)
            return

        if not isinstance(interval, int) or interval <= 0:
            self.logger.error("Invalid interval for task '%s'. Must be a positive integer.", name)
            return

        # Stop existing task with the same name, if any
        self.remove_task(name)

        task_info = {
            "function": func,
            "interval": interval,
            "stop_event": threading.Event(),
            "thread": None
        }

        def wrapper():
            """The target function for the task's thread."""
            stop_event = task_info["stop_event"]
            while not stop_event.is_set():
                try:
                    func()
                except Exception as e:
                    self.logger.error("Error executing task '%s': %s", name, e, exc_info=True)

                # Wait for the interval, checking stop_event periodically
                if stop_event.wait(timeout=interval):
                    break

        thread = threading.Thread(target=wrapper, name=f"Scheduler-{name}", daemon=True)
        with self.lock:
            task_info["thread"] = thread
            self.tasks[name] = task_info
            thread.start()
            self.logger.info("Task '%s' started, running every %d seconds.", name, interval)

    def remove_task(self, name: str):
        """
        Stops and removes a task by its name.

        Args:
            name (str): The name of the task to remove.
        """
        with self.lock:
            if name in self.tasks:
                task_info = self.tasks.pop(name)
                task_info["stop_event"].set()
                thread = task_info.get("thread")
                if thread and thread.is_alive():
                    thread.join(timeout=2.0)  # Wait for the thread to finish
                self.logger.info("Task '%s' has been removed.", name)
            else:
                self.logger.debug("Task '%s' was not found in scheduler.", name)

    def shutdown(self):
        """Stops all running tasks and waits for them to exit."""
        self.logger.info("Shutting down all scheduled tasks...")
        with self.lock:
            task_names = list(self.tasks.keys())

        for name in task_names:
            self.remove_task(name)

        self.logger.info("Scheduler shutdown complete.")

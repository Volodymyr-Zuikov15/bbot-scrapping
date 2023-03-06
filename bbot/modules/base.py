import queue
import logging
import threading
import traceback
from sys import exc_info
from datetime import datetime
from contextlib import suppress

from ..core.helpers.threadpool import ThreadPoolWrapper
from ..core.errors import ScanCancelledError, ValidationError, WordlistError


class BaseModule:
    # Event types to watch
    watched_events = []
    # Event types to produce
    produced_events = []
    # Module description, etc.
    meta = {"auth_required": False, "description": "Base module"}
    # Flags, must include either "passive" or "active"
    flags = []

    # python dependencies (pip install ____)
    deps_pip = []
    # apt dependencies (apt install ____)
    deps_apt = []
    # other dependences as shell commands
    # uses ansible.builtin.shell (https://docs.ansible.com/ansible/latest/collections/ansible/builtin/shell_module.html)
    deps_shell = []
    # list of ansible tasks for when other dependency installation methods aren't enough
    deps_ansible = []
    # Whether to accept incoming duplicate events
    accept_dupes = False
    # Whether to block outgoing duplicate events
    suppress_dupes = True

    # Scope distance modifier - accept/deny events based on scope distance
    # None == accept all events
    # 2 == accept events up to and including the scan's configured search distance plus two
    # 1 == accept events up to and including the scan's configured search distance plus one
    # 0 == accept events up to and including the scan's configured search distance
    # -1 == accept events up to and including the scan's configured search distance minus one
    #       (this is the default setting because when the scan's configured search distance == 1
    #       [the default], then this is equivalent to in_scope_only)
    # -2 == accept events up to and including the scan's configured search distance minus two
    scope_distance_modifier = -1
    # Only accept the initial target event(s)
    target_only = False
    # Only accept explicitly in-scope events (scope distance == 0)
    # Use this options if your module is aggressive or if you don't want it to scale with
    #   the scan's search distance
    in_scope_only = False

    # Options, e.g. {"api_key": ""}
    options = {}
    # Options description, e.g. {"api_key": "API Key"}
    options_desc = {}
    # Maximum concurrent instances of handle_event() or handle_batch()
    max_event_handlers = 1
    # Max number of concurrent calls to submit_task()
    max_threads = 10
    # Batch size
    # If batch size > 1, override handle_batch() instead of handle_event()
    batch_size = 1
    # Seconds to wait before force-submitting batch
    batch_wait = 10
    # Use in conjunction with .request_with_fail_count() to set_error_state() after this many failed HTTP requests
    failed_request_abort_threshold = 5
    # When set to false, prevents events generated by this module from being automatically marked as in-scope
    # Useful for low-confidence modules like speculate and ipneighbor
    _scope_shepherding = True
    # Exclude from scan statistics
    _stats_exclude = False
    # outgoing queue size (None == infinite)
    _qsize = None
    # Priority of events raised by this module, 1-5, lower numbers == higher priority
    _priority = 3
    # Name, overridden automatically
    _name = "base"
    # Type, for differentiating between normal modules and output modules, etc.
    _type = "scan"

    def __init__(self, scan):
        self.scan = scan
        self.errored = False
        self._log = None
        self._incoming_event_queue = None
        # seconds since we've submitted a batch
        self._last_submitted_batch = None
        # wrapper around shared thread pool to ensure that a single module doesn't hog more than its share
        max_workers = self.config.get("max_threads", self.max_threads)
        self.thread_pool = ThreadPoolWrapper(self.scan._thread_pool, max_workers=max_workers)
        self._internal_thread_pool = ThreadPoolWrapper(
            self.scan._internal_thread_pool.executor, max_workers=self.max_event_handlers
        )
        # additional callbacks to be executed alongside self.cleanup()
        self.cleanup_callbacks = []
        self._cleanedup = False
        self._watched_events = None

        self._lock = threading.RLock()
        self.event_received = threading.Condition(self._lock)

        # string constant
        self._custom_filter_criteria_msg = "it did not meet custom filter criteria"

        # track number of failures (for .request_with_fail_count())
        self._request_failures = 0

    def setup(self):
        """
        Perform setup functions at the beginning of the scan.
        Optionally override this method.

        Must return True or False based on whether the setup was successful
        """
        return True

    def handle_event(self, event):
        """
        Override this method if batch_size == 1.
        """
        pass

    def handle_batch(self, *events):
        """
        Override this method if batch_size > 1.
        """
        pass

    def filter_event(self, event):
        """
        Accept/reject events based on custom criteria

        Override this method if you need more granular control
        over which events are distributed to your module
        """
        return True

    def finish(self):
        """
        Perform final functions when scan is nearing completion

        For example,  if your module relies on the word cloud, you may choose to wait until
        the scan is finished (and the word cloud is most complete) before running an operation.

        Note that this method may be called multiple times, because it may raise events.
        Optionally override this method.
        """
        return

    def report(self):
        """
        Perform a final task when the scan is finished, but before cleanup happens

        This is useful for modules that aggregate data and raise summary events at the end of a scan
        """
        return

    def cleanup(self):
        """
        Perform final cleanup after the scan has finished
        This method is called only once, and may not raise events.
        Optionally override this method.
        """
        return

    def get_watched_events(self):
        """
        Override if you need your watched_events to be dynamic
        """
        if self._watched_events is None:
            self._watched_events = set(self.watched_events)
        return self._watched_events

    def submit_task(self, *args, **kwargs):
        return self.thread_pool.submit_task(self.catch, *args, **kwargs)

    def catch(self, *args, **kwargs):
        return self.scan.manager.catch(*args, **kwargs)

    def _postcheck_and_run(self, callback, event):
        acceptable, reason = self._event_postcheck(event)
        if not acceptable:
            if reason:
                self.debug(f"Not accepting {event} because {reason}")
            return
        return callback(event)

    def _handle_batch(self, force=False):
        if self.batch_size <= 1:
            return
        if self.num_queued_events > 0 and (force or self.num_queued_events >= self.batch_size):
            self.batch_idle(reset=True)
            on_finish_callback = None
            events, finish, report = self.events_waiting
            if finish:
                on_finish_callback = self.finish
            elif report:
                on_finish_callback = self.report
            checked_events = []
            for e in events:
                acceptable, reason = self._event_postcheck(e)
                if not acceptable:
                    if reason:
                        self.debug(f"Not accepting {e} because {reason}")
                    continue
                checked_events.append(e)
            if checked_events:
                self.debug(f"Handling batch of {len(events):,} events")
                if not self.errored:
                    self._internal_thread_pool.submit_task(
                        self.catch,
                        self.handle_batch,
                        *checked_events,
                        _on_finish_callback=on_finish_callback,
                    )
                return True
        return False

    def make_event(self, *args, **kwargs):
        raise_error = kwargs.pop("raise_error", False)
        try:
            event = self.scan.make_event(*args, **kwargs)
        except ValidationError as e:
            if raise_error:
                raise
            self.warning(f"{e}")
            return
        if not event.module:
            event.module = self
        return event

    def emit_event(self, *args, **kwargs):
        event_kwargs = dict(kwargs)
        for o in ("on_success_callback", "abort_if", "quick"):
            event_kwargs.pop(o, None)
        event = self.make_event(*args, **event_kwargs)
        if event is None:
            return
        # nerf event's priority if it's likely not to be in scope
        if event.scope_distance > 0:
            event_in_scope = self.scan.whitelisted(event) and not self.scan.blacklisted(event)
            if not event_in_scope:
                event.module_priority += event.scope_distance
        if event:
            # Wait for parent event to resolve (in case its scope distance changes)
            while 1:
                if self.scan.stopping:
                    return
                resolved = event.source._resolved.wait(timeout=0.1)
                if resolved:
                    # update event's scope distance based on its parent
                    event.scope_distance = event.source.scope_distance + 1
                    break
            self.scan.manager.incoming_event_queue.put((event, kwargs))

    @property
    def events_waiting(self):
        """
        yields all events in queue, up to maximum batch size
        """
        events = []
        finish = False
        report = False
        while self.incoming_event_queue:
            if len(events) > self.batch_size:
                break
            try:
                event = self.incoming_event_queue.get_nowait()
                if event.type == "FINISHED":
                    finish = True
                else:
                    events.append(event)
            except queue.Empty:
                break
        return events, finish, report

    @property
    def num_queued_events(self):
        ret = 0
        if self.incoming_event_queue:
            ret = self.incoming_event_queue.qsize()
        return ret

    def start(self):
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _setup(self):
        status_codes = {False: "hard-fail", None: "soft-fail", True: "success"}

        status = False
        self.debug(f"Setting up module {self.name}")
        try:
            result = self.setup()
            if type(result) == tuple and len(result) == 2:
                status, msg = result
            else:
                status = result
                msg = status_codes[status]
            self.debug(f"Finished setting up module {self.name}")
        except Exception as e:
            self.set_error_state()
            if isinstance(e, WordlistError):
                status = None
            msg = f"{e}"
            self.trace()
        return status, str(msg)

    @property
    def _force_batch(self):
        """
        Determine whether a batch should be forcefully submitted
        """
        # if we've been idle long enough
        if self.batch_idle() >= self.batch_wait:
            return True
        # if scan is finishing
        if self.scan.status == "FINISHING":
            return True
        # if there's a batch stalemate
        batch_modules = [m for m in self.scan.modules.values() if m.batch_size > 1]
        if all([(not m.running) for m in batch_modules]):
            return True
        return False

    def batch_idle(self, reset=False):
        now = datetime.now()
        if self._last_submitted_batch is None or reset:
            self._last_submitted_batch = now
        delta = now - self._last_submitted_batch
        return delta.total_seconds()

    def _worker(self):
        try:
            while not self.scan.stopping:
                # hold the reigns if our outgoing queue is full
                if self._qsize and self.outgoing_event_queue_qsize >= self._qsize:
                    with self.event_received:
                        self.event_received.wait(timeout=0.1)
                    continue

                if self.batch_size > 1:
                    force = self._force_batch
                    submitted = self._handle_batch(force=force)
                    if not submitted:
                        with self.event_received:
                            self.event_received.wait(timeout=0.1)

                else:
                    try:
                        if self.incoming_event_queue:
                            e = self.incoming_event_queue.get(timeout=0.1)
                        else:
                            self.debug(f"Event queue is in bad state")
                            return
                    except queue.Empty:
                        continue
                    self.debug(f"Got {e} from {getattr(e, 'module', e)}")
                    # if we receive the special "FINISHED" event
                    if e.type == "FINISHED":
                        self._internal_thread_pool.submit_task(self.catch, self.finish)
                    else:
                        if self._type == "output":
                            self.catch(self._postcheck_and_run, self.handle_event, e)
                        else:
                            self._internal_thread_pool.submit_task(
                                self.catch, self._postcheck_and_run, self.handle_event, e
                            )

        except KeyboardInterrupt:
            self.debug(f"Interrupted")
            self.scan.stop()
        except ScanCancelledError as e:
            self.verbose(f"Scan cancelled, {e}")
        except Exception as e:
            self.set_error_state(f"Exception ({e.__class__.__name__}) in module {self.name}:\n{e}")
            self.trace()

    @property
    def max_scope_distance(self):
        if self.in_scope_only or self.target_only:
            return 0
        return max(0, self.scan.scope_search_distance + self.scope_distance_modifier)

    def _event_precheck(self, event):
        """
        Check if an event should be accepted by the module
        Used when putting an event INTO the modules' queue
        """
        # special signal event types
        if event.type in ("FINISHED",):
            return True, ""
        if self.errored:
            return False, f"module is in error state"
        # exclude non-watched types
        if not any(t in self.get_watched_events() for t in ("*", event.type)):
            return False, "its type is not in watched_events"
        if self.target_only:
            if "target" not in event.tags:
                return False, "it did not meet target_only filter criteria"
        # if event is an IP address that was speculated from a CIDR
        source_is_range = getattr(event.source, "type", "") == "IP_RANGE"
        if (
            source_is_range
            and event.type == "IP_ADDRESS"
            and str(event.module) == "speculate"
            and self.name != "speculate"
        ):
            # and the current module listens for both ranges and CIDRs
            if all([x in self.watched_events for x in ("IP_RANGE", "IP_ADDRESS")]):
                # then skip the event.
                # this helps avoid double-portscanning both an individual IP and its parent CIDR.
                return False, "module consumes IP ranges directly"
        return True, ""

    def _event_postcheck(self, event):
        """
        Check if an event should be accepted by the module
        Used when taking an event FROM the module's queue (immediately before it's handled)
        """
        if event.type in ("FINISHED",):
            return True, ""

        if self.in_scope_only:
            if event.scope_distance > 0:
                return False, "it did not meet in_scope_only filter criteria"
        if self.scope_distance_modifier is not None:
            if event.scope_distance < 0:
                return False, f"its scope_distance ({event.scope_distance}) is invalid."
            elif event.scope_distance > self.max_scope_distance:
                return (
                    False,
                    f"its scope_distance ({event.scope_distance}) exceeds the maximum allowed by the scan ({self.scan.scope_search_distance}) + the module ({self.scope_distance_modifier}) == {self.max_scope_distance}",
                )

        # custom filtering
        try:
            filter_result = self.filter_event(event)
            msg = str(self._custom_filter_criteria_msg)
            with suppress(ValueError, TypeError):
                filter_result, reason = filter_result
                msg += f": {reason}"
            if not filter_result:
                return False, msg
        except ScanCancelledError:
            return False, "Scan cancelled"
        except Exception as e:
            self.error(f"Error in filter_event({event}): {e}")
            self.trace()

        return True, ""

    def _cleanup(self):
        if not self._cleanedup:
            self._cleanedup = True
            for callback in [self.cleanup] + self.cleanup_callbacks:
                if callable(callback):
                    self.catch(callback, _force=True)

    def queue_event(self, event):
        if self.incoming_event_queue in (None, False):
            self.debug(f"Not in an acceptable state to queue event")
            return
        acceptable, reason = self._event_precheck(event)
        if not acceptable:
            if reason and reason != "its type is not in watched_events":
                self.debug(f"Not accepting {event} because {reason}")
            return
        self.scan.stats.event_consumed(event, self)
        try:
            self.incoming_event_queue.put(event)
        except AttributeError:
            self.debug(f"Not in an acceptable state to queue event")
        with self.event_received:
            self.event_received.notify()

    def set_error_state(self, message=None):
        if not self.errored:
            if message is not None:
                self.warning(str(message))
            self.debug(f"Setting error state for module {self.name}")
            self.errored = True
            # clear incoming queue
            if self.incoming_event_queue:
                self.debug(f"Emptying event_queue")
                with suppress(queue.Empty):
                    while 1:
                        self.incoming_event_queue.get_nowait()
                # set queue to None to prevent its use
                # if there are leftover objects in the queue, the scan will hang.
                self._incoming_event_queue = False

    @property
    def name(self):
        return str(self._name)

    @property
    def helpers(self):
        return self.scan.helpers

    @property
    def status(self):
        main_pool = self.thread_pool.num_tasks
        internal_pool = self._internal_thread_pool.num_tasks
        pool_total = main_pool + internal_pool
        incoming_qsize = 0
        if self.incoming_event_queue:
            incoming_qsize = self.incoming_event_queue.qsize()
        status = {
            "events": {"incoming": incoming_qsize, "outgoing": self.outgoing_event_queue_qsize},
            "tasks": {"main_pool": main_pool, "internal_pool": internal_pool, "total": pool_total},
            "errored": self.errored,
        }
        status["running"] = self._is_running(status)
        return status

    def request_with_fail_count(self, *args, **kwargs):
        r = self.helpers.request(*args, **kwargs)
        if r is None:
            self._request_failures += 1
        else:
            self._request_failures = 0
        if self._request_failures >= self.failed_request_abort_threshold:
            self.set_error_state(f"Setting error state due to {self._request_failures:,} failed HTTP requests")
        return r

    @staticmethod
    def _is_running(module_status):
        for pool, count in module_status["tasks"].items():
            if count > 0:
                return True
        for direction, qsize in module_status["events"].items():
            if qsize > 0:
                return True
        return False

    @property
    def running(self):
        """
        Indicates whether the module is currently processing data.
        """
        return self._is_running(self.status)

    @property
    def config(self):
        config = self.scan.config.get("modules", {}).get(self.name, {})
        if config is None:
            config = {}
        return config

    @property
    def incoming_event_queue(self):
        if self._incoming_event_queue is None:
            self._incoming_event_queue = queue.PriorityQueue()
        return self._incoming_event_queue

    @property
    def outgoing_event_queue_qsize(self):
        return self.scan.manager.incoming_event_queue.modules.get(str(self), 0)

    @property
    def priority(self):
        return int(max(1, min(5, self._priority)))

    @property
    def auth_required(self):
        return self.meta.get("auth_required", False)

    @property
    def log(self):
        if getattr(self, "_log", None) is None:
            self._log = logging.getLogger(f"bbot.modules.{self.name}")
        return self._log

    def __str__(self):
        return self.name

    def stdout(self, *args, **kwargs):
        self.log.stdout(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def debug(self, *args, **kwargs):
        self.log.debug(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def verbose(self, *args, **kwargs):
        self.log.verbose(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def hugeverbose(self, *args, **kwargs):
        self.log.hugeverbose(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def info(self, *args, **kwargs):
        self.log.info(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def hugeinfo(self, *args, **kwargs):
        self.log.hugeinfo(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def success(self, *args, **kwargs):
        self.log.success(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def hugesuccess(self, *args, **kwargs):
        self.log.hugesuccess(*args, extra={"scan_id": self.scan.id}, **kwargs)

    def warning(self, *args, **kwargs):
        self.log.warning(*args, extra={"scan_id": self.scan.id}, **kwargs)
        self.trace()

    def hugewarning(self, *args, **kwargs):
        self.log.hugewarning(*args, extra={"scan_id": self.scan.id}, **kwargs)
        self.trace()

    def error(self, *args, **kwargs):
        self.log.error(*args, extra={"scan_id": self.scan.id}, **kwargs)
        self.trace()

    def trace(self):
        e_type, e_val, e_traceback = exc_info()
        if e_type is not None:
            self.log.trace(traceback.format_exc())

    def critical(self, *args, **kwargs):
        self.log.critical(*args, extra={"scan_id": self.scan.id}, **kwargs)
        self.trace()

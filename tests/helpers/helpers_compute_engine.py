import contextlib
import datetime

import jam.libs.compute_engine


def make_info_instantly_stale(instance):
    instance.info_ts -= datetime.timedelta(
        milliseconds=2 * jam.libs.compute_engine.ComputeEngineInstance.DEFAULT_STALE_AFTER_MS
    )


@contextlib.contextmanager
def no_pause():
    saved_wait_op = jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_OPERATION
    saved_wait_st = jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_STATUS
    saved_stale = jam.libs.compute_engine.ComputeEngineInstance.DEFAULT_STALE_AFTER_MS

    jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_OPERATION = 0
    jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_STATUS = 0
    jam.libs.compute_engine.ComputeEngineInstance.DEFAULT_STALE_AFTER_MS = 1
    try:
        yield
    finally:
        jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_OPERATION = saved_wait_op
        jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_STATUS = saved_wait_st
        jam.libs.compute_engine.ComputeEngineInstance.DEFAULT_STALE_AFTER_MS = saved_stale

import errno
import os
import select
import threading
import time

from scheme import Integer, Text
from spire.core import Configuration, Unit, configured_property
from spire.support.logs import LogHelper

log = LogHelper(__name__)

try:
    from os import mkfifo

except ImportError:

    class Idler(Unit):
        configuration = Configuration({
            'timeout': Integer(default=30),
        })

        timeout = configured_property('timeout')

        def idle(self, timeout=None):
            time.sleep(timeout or self.timeout)

        def interrupt(self):
            pass

else:

    class Idler(Unit):
        configuration = Configuration({
            'fifo': Text(default='/tmp/platoon-idler'),
            'timeout': Integer(default=5),
        })

        fifo = configured_property('fifo')

        def __init__(self):
            self.fd = None
            self.poller = None
            self.timeout = self.configuration['timeout'] * 1000

        def idle(self, timeout=None):
            if not self.poller:
                self._prepare_idler()
            if not self.fd:
                self._open_fifo()

            if timeout is not None:
                poll_timeout = timeout * 1000
            else:
                poll_timeout = self.timeout

            try:
                events = self.poller.poll(poll_timeout)
            except select.error, exception:
                if exception.args[0] == errno.EINTR:
                    return
                else:
                    raise

            interrupted = False
            try:
                fd, event = events[0]
            except IndexError:
                return
            
            if event & select.POLLIN:
                os.read(fd, 64)
                interrupted = True
                log('debug', 'interrupted')
            if event & select.POLLHUP:
                self._open_fifo()
                if not interrupted:
                    self.idle(timeout)

        def interrupt(self):
            try:
                fd = os.open(self.fifo, os.O_WRONLY | os.O_NONBLOCK)
            except OSError, exception:
                if exception.args[0] in (errno.ENOENT, errno.ENXIO):
                    return
                else:
                    raise

            try:
                os.write(fd, '\x00')
                log('debug', 'attempting to interrupt')
            except OSError, exception:
                if exception.args[0] in (errno.EAGAIN, errno.EPIPE):
                    return
                else:
                    raise
            finally:
                os.close(fd)

        def _open_fifo(self):
            if self.fd:
                self.poller.unregister(self.fd)
                os.close(self.fd)

            self.fd = os.open(self.fifo, os.O_RDONLY | os.O_NONBLOCK)
            self.poller.register(self.fd, select.POLLIN)

        def _prepare_idler(self):
            self.poller = select.poll()
            try:
                mkfifo(self.fifo)
            except OSError, exception:
                if exception.args[0] != errno.EEXIST:
                    raise

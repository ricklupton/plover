#!/usr/bin/env python

import threading
from engine import PloverEngine
from gi.repository import IBus, GLib
import traceback


# class ProcessEventsTimer(wxTimer):
#     """
#     Timer that tells wx to process pending events.

#     This is necessary on OS X, probably due to a bug in wx, if we want
#     wxCallAfters to be handled when modal dialogs, menus, etc. are open.
#     """
#     def __init__(self, main_context):
#         wxTimer.__init__(self)
#         self.context = main_context

#     def Notify(self):
#         """
#         Called repeatedly by wx event loop.
#         """
#         self.wxapp.ProcessPendingEvents()



class EngineFactory(IBus.Factory):
    """Create a new IBus engine when requested by ibus-daemon."""

    BUS_PATH_PATTERN = "/org/freedesktop/IBus/Plover/Engine/%d"

    def __init__(self, plover_app, bus):
        super(EngineFactory, self).__init__(connection=bus.get_connection(),
                                            object_path=IBus.PATH_FACTORY)
        self._plover_app = plover_app
        self._bus = bus
        self._id = 0

    def do_create_engine(self, engine_name):
        if engine_name == "plover":
            self._id += 1
            bus_name = self.BUS_PATH_PATTERN % self._id
            try:
                return PloverEngine(self._plover_app, self._bus, bus_name)
            except:
                traceback.print_exc()
        else:
            return super(EngineFactory, self).do_create_engine(engine_name)


class IBusComponentThread(threading.Thread):
    """Run IBus DBus mainloop in own thread and register engine."""

    # def __init__(self, plover_app):
    #     super(IBusComponentThread, self).__init__()
    #     self._plover_app = plover_app

    def run(self):
        # IBus needs a GLib mainloop to process events in
        try:
            self._context = GLib.MainContext()
            self._context.push_thread_default()
            # self._mainloop = GLib.MainLoop(self._context)
            self._bus = IBus.Bus()
            self._bus.connect("connected", self._bus_connected_cb)
            self._bus.connect("disconnected", self._bus_disconnected_cb)

            print("Global default context:", GLib.MainContext.default())
            print("Thread default context:", GLib.MainContext.get_thread_default())
            print("New context:", self._context)
            
            # Need a way of signalling to the thread to stop when app quits
            self._stop_request = threading.Event()
            GLib.timeout_add(1000, self._check_stop)

            # Start the mainloop running - blocks
            print("Starting mainloop", threading.current_thread())
            # self._mainloop.run()
            while not self._stop_request.is_set():
                self._context.iteration(True)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _check_stop(self):
        print("Checking stop...", threading.current_thread())
        if self._stop_request.is_set():
            print("STOPPING!!!!")
            self._mainloop.quit()
        return True

    def join(self, timeout=None):
        self._stop_request.set()  # Signal to mainloop to quit
        super(IBusComponentThread, self).join(timeout)

    def _bus_connected_cb(self, bus):
        # Wait until the bus is connected (here) before trying to
        # register things.
        print("Bus connected")
        self._factory = EngineFactory(self._plover_app, self._bus)
        self._component = IBus.Component(
            name="org.freedesktop.IBus.Plover",
            description="Plover IBus",
            version="0.1.0",
            license="GPL",
            author="Rick Lupton",
            homepage="",
            textdomain="")
        engine = IBus.EngineDesc(
            name="plover",
            longname="plover longname",
            description="plover description",
            language="en",
            license="GPL",
            author="Rick Lupton",
            icon="",
            layout="en")
        self._component.add_engine(engine)
        print("Registering", self._component)
        self._bus.register_component(self._component)

    def _bus_disconnected_cb(self, bus):
        self._mainloop.quit()

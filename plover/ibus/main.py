#import dbus
import threading
from gi.repository import IBus
from gi.repository import GLib
from gi.repository import GObject

from plover.ibus.engine import EnginePlover

# gobject.threads_init()
# #dbus.glib.threads_init()


##### THIS SHOULD BE INTEGRATED INTO MAIN APP #######
import plover.config
import plover.steno as steno
import plover.translation as translation
from plover.dictionary.loading_manager import manager as dict_manager
from plover.exception import InvalidConfigurationError,DictionaryLoaderException


def load_config():
    config = plover.config.Config()
    config.target_file = plover.config.CONFIG_FILE
    with open(config.target_file, 'rb') as f:
        config.load(f)
    return config


def get_dicts(config):
    """Initialize a StenoEngine from a config object."""
    dictionary_file_names = config.get_dictionary_file_names()
    try:
        dicts = dict_manager.load(dictionary_file_names)
    except DictionaryLoaderException as e:
        raise InvalidConfigurationError(unicode(e))
    return dicts


def init_engine(engine):
    config = load_config()
    engine.set_dicts(get_dicts(config))
    # Set up logging...

#####################################################

class EngineFactory(IBus.Factory):
    def __init__(self, bus):
        self.__bus = bus
        super(EngineFactory, self).__init__(object_path=IBus.PATH_FACTORY,
                                            connection=bus.get_connection())
        self.__id = 0

    def do_create_engine(self, engine_name):
        if engine_name == "plover":
            self.__id += 1
            print engine_name, self.__id
            bus_name = "%s/%d" % ("/org/freedesktop/IBus/Plover/Engine",
                                  self.__id)
            e = Engine(self.__bus, bus_name)
            init_engine(e)
            return e
        return super(EngineFactory, self).do_create_engine(engine_name)


class IBusPloverComponent:
    """Registers the component with IBus"""
    def __init__(self, exec_by_ibus=False):
        #engine_name = "plover" if exec_by_ibus else "plover (direct)"
        self.__component = IBus.Component("org.freedesktop.IBus.Plover",
                                              "Plover IBus",
                                          "0.1.0",
                                          "GPL",
                                          "Rick Lupton",
                                          "http://example.com",
                                          "/usr/bin/true",
                                          "ibus-plover")
        self.__component.add_engine(
            IBus.EngineDesc.new("plover",
                                "plover",
                                "Plover",
                                "en",
                                "GPL",
                                "Rick Lupton",
                                "",
                                "en"))
        #self.__mainloop = GLib.MainLoop()
        self.__bus = IBus.Bus()
        self.__bus.connect("disconnected", self.__bus_disconnected_cb)
        self.__factory = EngineFactory(self.__bus)
        #self.__bus.request_name('org.freedesktop.IBus.Plover', 0)
        self.__bus.register_component(self.__component)
        # self.__bus.set_global_engine_async(
        #     "plover", -1, None, None, None)

    def run(self):
        self.__mainloop.run()

    def __bus_disconnected_cb(self, bus):
        self.__mainloop.quit()


def launch_ibus_component():
    print "Starting IBus component..."
    IBus.init()
    c = IBusPloverComponent()
    #threading.Thread(target=c.run).start()
    #c.run()

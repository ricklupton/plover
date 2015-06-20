from __future__ import print_function
from gi.repository import IBus
from gi.repository import GLib


class PloverEngine(IBus.Engine):
    """IBus engine for Plover stenography"""
    def __init__(self, plover_app, bus, object_path):
        super(PloverEngine, self).__init__(connection=bus.get_connection(),
                                           object_path=object_path)
        self._app = plover_app
        self._dbus_path = object_path
        self._is_invalidated = False
        self._preedit_string = u""
        self._aux_string = u""

    def do_process_key_event(self, keyval, keycode, state):
        """Handle key events from IBus"""
        print("Key", keyval, keycode, state)
        return False

    def __invalidate(self):
        """Schedule an update"""
        if self._is_invalidated:
            return
        self._is_invalidated = True
        GLib.idle_add(self._update, priority=GLib.PRIORITY_LOW)

    def __commit_string(self, text):
        """Send commited text to IBus"""
        self.commit_text(IBus.Text.new_from_string(text))
        self._preedit_string = u""
        self._update()

    def __update(self):
        """Update preedit, auxiliary and lookup table text"""

        # Auxiliary text
        self.update_auxiliary_text(
            IBus.Text.new_from_string(self._aux_string),
            len(self._aux_string) > 0)

        # Show preedit text (not currently used)
        # preedit_len = len(self._preedit_string)
        # attrs = IBus.AttrList()
        # if preedit_len > 0:
        #     attrs.append(IBus.attr_foreground_new(0xff0000, 0, preedit_len))
        #     attrs.append(
        #       IBus.AttributeUnderline(pango.UNDERLINE_SINGLE, 0, preedit_len))
        # self.update_preedit_text(ibus.Text(self._preedit_string, attrs),
        #                          preedit_len, preedit_len > 0)

        # Lookup table
        table_visible = self._lookup_table.get_number_of_candidates() > 0
        self.update_lookup_table(self._lookup_table, table_visible)

        self._is_invalidated = False

    def do_focus_in(self):
        print("focus in %s" % self._dbus_path)

        # Signal that surrounding text is needed
        self.get_surrounding_text()

        # self._reset_translator()

    def do_reset(self):
        """Handle reset signal"""
        # XXX When is this sent by IBus?
        print("RESET %s" % self._dbus_path)

    def do_enable(self):
        # Signal that surrounding text is needed
        self.get_surrounding_text()

        print("enable %s" % self._dbus_path)

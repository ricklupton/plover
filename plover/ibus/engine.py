import sys
from os.path import commonprefix

from gi.repository import GLib
from gi.repository import IBus
from gi.repository import Pango

keysyms = IBus
modifier = IBus.ModifierType

from plover.machine.ibus import Stenotype
from plover.oslayer.keyboardcontrol import KeyboardEmulation
from plover import steno, translation
import aware_formatter
#from key_combinations import parse_key_combinations


class EnginePlover(IBus.Engine):
    """IBus Engine representing a Steno pipeline.

    There is one of these for each input context - separate history of
    strokes, undo, etc.

    """

    __gtype_name__ = 'EnginePlover'
    def __init__(self):
        super(EnginePlover, self).__init__()
        self.__is_invalidate = False
        self.__preedit_string = u""
        self.__aux_string = u""
        #self.__lookup_table = ibus.LookupTable()
        # self.__prop_list = ibus.PropList()
        # self.__prop_list.append(ibus.Property(u"test", icon = u"ibus-locale"))
        self.__init_plover()

    def __init_plover(self):
        print "Init plover"

        # Pipeline
        self.machine = Stenotype({'arpeggiate': False})
        self.translator = translation.Translator()
        self.formatter = aware_formatter.AwareFormatter()

        # Link up pipeline callbacks
        self.machine.add_stroke_callback(self._stroke_notify)
        self.translator.add_listener(self.formatter.format)
        self.formatter.set_output(self)
        self.machine.start_capture()
        # self.machine.add_state_callback(self._machine_state_callback)

        self.keyboard_control = KeyboardEmulation()

        # This should go outside - 1 logger for all pipelines
        # self.logger = Logger()
        # self.translator.add_listener(self.logger.log_translation)
        # self.machine.add_stroke_callback(self.logger.log_stroke)

        # Set up translator; this seems like a reasonable number. If
        # this becomes a problem it can be parameterized.
        self.translator.set_min_undo_length(10)

    def set_dicts(self, dicts):
        self.translator.get_dictionary().set_dicts(dicts)

    # IBus signals
    def do_process_key_event(self, keyval, keycode, state):
        # ignore key presses with modifiers (e.g. Control-C)
        if (state & ~IBus.ModifierType.RELEASE_MASK):
            return False

        is_press = ((state & IBus.ModifierType.RELEASE_MASK) == 0)
        try:
            if is_press:
                handled = self.machine.key_down(keycode)
            else:
                handled = self.machine.key_up(keycode)

            # # Show steno keys
            if self.__aux_string:
                self.__aux_string = ""
                self.__invalidate()
            # self.__aux_string = self.steno.get_steno_string()
            # self.__invalidate()
        except:
            import traceback
            traceback.print_exc()

        # Don't pass through key presses corresponding to steno keys
        if not handled:
            print "...", keyval, keycode, state
        return handled

        # XXX Should these things be handled specially?
        # if self.__preedit_string:
        #     if keyval == keysyms.Return:
        #         self.__commit_string(self.__preedit_string)
        #         return True
        #     elif keyval == keysyms.Escape:
        #         self.__preedit_string = u""
        #         self.__update()
        #         return True
        #     elif keyval == keysyms.BackSpace:
        #         self.__preedit_string = self.__preedit_string[:-1]
        #         self.__invalidate()
        #         return True
        #     elif keyval == keysyms.space:
        #         # if self.__lookup_table.get_number_of_candidates() > 0:
        #         #     self.__commit_string(
        #         #         self.__lookup_table.get_current_candidate().text)
        #         # else:
        #         #     self.__commit_string(self.__preedit_string)
        #         self.__commit_string(self.__preedit_string)
        #         return False
        #     elif keyval == keysyms.Left or keyval == keysyms.Right:
        #         return True
        # if keyval in xrange(keysyms.a, keysyms.z + 1) or \
        #     keyval in xrange(keysyms.A, keysyms.Z + 1):
        #     if state & (modifier.CONTROL_MASK | modifier.ALT_MASK) == 0:
        #         self.__preedit_string += unichr(keyval)
        #         self.__invalidate()
        #         return True
        # else:
        #     if keyval < 128 and self.__preedit_string:
        #         self.__commit_string(self.__preedit_string)
        # return False

    def __invalidate(self):
        if self.__is_invalidate:
            return
        self.__is_invalidate = True
        GLib.idle_add(self.__update)

    def __commit_string(self, text):
        self.commit_text(IBus.Text.new_from_string(text))
        self.__preedit_string = u""
        self.__update()

    def __update(self):
        text = IBus.Text.new_from_string(self.__aux_string)
        #text.set_attributes(attrs)
        self.update_auxiliary_text(text, len(self.__aux_string) > 0)

        preedit_len = len(self.__preedit_string)
        attrs = IBus.AttrList()
        if preedit_len > 0:
            attrs.append(IBus.Attribute.new(IBus.AttrType.FOREGROUND,
                                            0xff0000, 0, preedit_len))
            attrs.append(IBus.Attribute.new(IBus.AttrType.UNDERLINE,
                                            IBus.AttrUnderline.SINGLE, 0,
                                            preedit_len))
        text = IBus.Text.new_from_string(self.__preedit_string)
        text.set_attributes(attrs)
        self.update_preedit_text(text, preedit_len, preedit_len > 0)
        self.__is_invalidate = False

    def do_focus_in(self):
        print "focus in %s" % self.__proxy._object_path
        sys.stdout.flush()
        #self.register_properties(self.__prop_list)

    def do_focus_out(self):
        pass

    def do_reset(self):
        pass

    def do_enable(self):
        # Tell IBus we want to use surrounding text later
        print "enable %s" % self.__proxy._object_path
        sys.stdout.flush()
        self.get_surrounding_text()

    def do_property_activate(self, prop_name):
        print "PropertyActivate(%s)" % prop_name

    def __plover_update_status(self, state):
        print "Plover update status:", state

    def __plover_consume_command(self, command):
        print "Plover consume command:", command

    # Plover pipeline callbacks
    def _stroke_notify(self, steno_keys):
        s = steno.Stroke(steno_keys)
        try:
            self.translator.translate(s)
        except aware_formatter.StateMismatch:
            self.show_message("Resetting state")
            self.translator.clear_state()
            # Resend last stroke
            self.translator.translate(s)

    # Plover output callbacks
    def change_string(self, before, after):
        # Check if surrounding text matches text to delete
        s, p = self.get_surrounding_text()
        current_text = s.get_text()[p - len(before):p]
        if current_text != before:
            print "MISMATCH: '%s' != '%s'" % (before, current_text)
            return False
        offset = len(commonprefix([before, after]))
        print "____", offset, "___", before, '->', after
        #print "Changing ok: '%s'" % t
        delete_length = len(before[offset:])
        self.delete_surrounding_text(-delete_length, delete_length)
        self.__preedit_string += after[offset:]
        self.__commit_string(self.__preedit_string)
        return True

    def send_key_combination(self, c):
        print "**** Send key comb:", c
        # Does it need to be delayed?
        # wx.CallAfter(self.keyboard_control.send_key_combination, c)

        # Does it need to be protected so it's not picked up again? In
        # theory yes; but as long as key combos aren't sending steno
        # key codes it'll be ok.
        self.keyboard_control.send_key_combination(c)

    # TODO: test all the commands now
    def send_engine_command(self, c):
        print "**** Send engine command:", c
        result = self.engine_command_callback(c)
        # if result and not self.engine.is_running:
        #     self.engine.machine.suppress = self.send_backspaces

    def show_message(self, message):
        def set_message():
            self.__aux_string = message
            self.__invalidate()
        GLib.idle_add(set_message)

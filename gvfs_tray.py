#!/usr/bin/env python3
# coding=utf-8

"""
Creates status icons for mounted removable volumes.

Looks for removable volumes and creates a status icon for each one. These
usually appear in the tray, depending on your desktop environment.
"""

import argparse
import sys

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Notify

from cgi import escape as htmlEscape
from pprint import pprint

__author__  = 'Laurence Gonsalves <laurence@xenomachina.com>'

def dump_to_stdout(*args, **kwargs):
    pprint({"Args": args})
    pprint({"KWArgs": kwargs})

def print_volume_identifiers(volume):
    for identifier in volume.enumerate_identifiers():
        print("    %s: %r" % (identifier, volume.get_identifier(identifier)))

def dump_event(event, mount):
    mount_path = mount.get_root().get_path()
    print("%s %s" % (mount_path, event))

class IconManager:
    def __init__(self):
        self.icons = {}
        self.menu_items = (
                ("Open", "open"),
                ("Eject", "eject"),
            )

    def on_mount_added(self, volume_monitor, mount, *user_args):
        dump_event("added", mount)
        self.create_icon(mount)

    def on_mount_changed(self, volume_monitor, mount, *user_args):
        dump_event("changed", mount)
        # TODO: rebuild icon?

    def on_mount_pre_unmount(self, volume_monitor, mount, *user_args):
        dump_event("pre-unmount", mount)

    def on_mount_removed(self, volume_monitor, mount, *user_args):
        dump_event("removed", mount)
        # TODO: delete menu if it's for this mount?
        del self.icons[mount.get_root().get_path()]

    def create_icon(self, mount):
        label = mount.get_name()
        path = mount.get_root().get_path()
        icon = Gtk.StatusIcon.new_from_gicon(mount.get_icon())
        icon.set_tooltip_markup("%s <tt>%s</tt>"
                % tuple(map(htmlEscape, (label, path))))
        icon.set_visible(True)

        icon.connect("activate", self.on_activate, mount)
        icon.connect("popup-menu", self.on_popup_menu, mount)

        self.icons[path] = icon

    def on_popup_menu(self, status_icon, button, activate_time, mount):
        menu = self.menu = Gtk.Menu()
        for label, command in self.menu_items:
            item = Gtk.MenuItem()
            item.set_label(label)
            item.connect("activate", self.on_menu_item_activated, command,
                    mount)
            menu.append(item)
        menu.connect("deactivate", self.on_menu_deactivate)
        menu.show_all()

        pos = Gtk.StatusIcon.position_menu
        menu.popup(None, None, pos, status_icon, button, activate_time)

    def on_menu_deactivate(self, *args):
        del self.menu

    def on_menu_item_activated(self, *args):
        print("\nMENU ITEM ACTIVATE")
        dump_to_stdout(*args)

    def on_activate(self, status_icon, mount):
        print("\nACTIVATE")
        print("status_icon\t", status_icon)
        print("mount\t", mount)

class UserError(Exception):
    def __init__(self, message):
        self.message = message

def create_parser():
    description, epilog = __doc__.strip().split('\n', 1)
    parser = argparse.ArgumentParser(description=description, epilog=epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter)
    return parser

def main(args):
    tray = IconManager()
    vm = Gio.VolumeMonitor.get()
    connections = []
    connections.append(vm.connect("mount-added", tray.on_mount_added, 1))
    connections.append(vm.connect("mount-changed", tray.on_mount_changed, 1))
    connections.append(vm.connect("mount-pre-unmount", tray.on_mount_pre_unmount, 1))
    connections.append(vm.connect("mount-removed", tray.on_mount_removed, 1))

    # Synthesize mount-added events for pre-existing mounts
    for mount in vm.get_mounts():
        tray.on_mount_added(vm, mount, 0)

    GObject.MainLoop().run()

if __name__ == '__main__':
    error = None
    parser = create_parser()
    try:
        args = parser.parse_args()
        main(args)
    except FileExistsError as exc:
        error = '%s: %r' % (exc.strerror, exc.filename)
    except UserError as exc:
        error = exc.message

    if error is not None:
        print(('%s: error: %s' % (parser.prog, error)), file=sys.stderr)
        sys.exit(1)

"""Owned RViz mouse input for isolated R00-B evaluation."""

import argparse
import ctypes
import json
import math
import re
import subprocess
import time
from pathlib import Path

import yaml




class RvizInput:
    def __init__(self, workspace, required_size=(1500, 900)):
        tree = subprocess.check_output(['xwininfo', '-root', '-tree'], text=True)
        main = next(l for l in tree.splitlines() if 'au9_nav2.rviz' in l and ' - RViz' in l)
        canvas = next(l for l in tree.splitlines() if '"rviz2": ("rviz2" "rviz2")' in l)
        self.window = int(re.search(r'0x[0-9a-f]+', main).group(), 16)
        geometry = re.compile(r'(\d+)x(\d+)[+-]\d+[+-]\d+\s+([+-]\d+)([+-]\d+)')
        self.main = tuple(map(int, geometry.search(main).groups()))
        if self.main[:2] != required_size:
            raise RuntimeError('RViz layout differs from the explicitly required size: '+str(required_size))
        self.canvas = tuple(map(int, geometry.search(canvas).groups()))
        config = yaml.safe_load((workspace / 'config/rviz2/au9_nav2.rviz').read_text())
        self.view = config['Visualization Manager']['Views']['Current']
        self.x11 = ctypes.CDLL('libX11.so.6')
        self.xtst = ctypes.CDLL('libXtst.so.6')
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError('No X display')
        self.x11.XFlush.argtypes = [ctypes.c_void_p]
        self.x11.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x11.XFree.argtypes = [ctypes.c_void_p]
        self.x11.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)), ctypes.POINTER(ctypes.c_uint)]
        self.x11.XSetInputFocus.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        self.xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                                 ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
        self.xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                                 ctypes.c_int, ctypes.c_ulong]
        # Focus alone does not raise a window hidden behind Gazebo. Raise the
        # WM frame, not only the reparented Qt client inside that frame.
        frame = self.window
        while True:
            root, parent = ctypes.c_ulong(), ctypes.c_ulong()
            children, count = ctypes.POINTER(ctypes.c_ulong)(), ctypes.c_uint()
            self.x11.XQueryTree(self.display, frame, ctypes.byref(root), ctypes.byref(parent),
                               ctypes.byref(children), ctypes.byref(count))
            if children:
                self.x11.XFree(children)
            if parent.value == root.value or not parent.value:
                break
            frame = parent.value
        self.x11.XRaiseWindow(self.display, frame)
        self.frame = frame
        # Ask the window manager to activate the client; setting X focus alone
        # may be reverted by the WM while another application stays on top.
        class MessageData(ctypes.Union):
            _fields_ = [('l', ctypes.c_long * 5)]
        class ClientMessage(ctypes.Structure):
            _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong),
                ('send_event', ctypes.c_int), ('display', ctypes.c_void_p),
                ('window', ctypes.c_ulong), ('message_type', ctypes.c_ulong),
                ('format', ctypes.c_int), ('data', MessageData)]
        class Event(ctypes.Union):
            _fields_ = [('client', ClientMessage), ('pad', ctypes.c_long * 24)]
        self.x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.x11.XInternAtom.restype = ctypes.c_ulong
        self.x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                       ctypes.c_int, ctypes.c_long, ctypes.POINTER(Event)]
        event = Event()
        event.client.type = 33
        event.client.display = self.display
        event.client.window = self.window
        event.client.message_type = self.x11.XInternAtom(self.display, b'_NET_ACTIVE_WINDOW', 0)
        event.client.format = 32
        event.client.data.l[0] = 2
        self.activation_event = event
        self.root_window = root.value
        self.x11.XSendEvent(self.display, root.value, 0, (1 << 20) | (1 << 19), ctypes.byref(event))
        self.x11.XFlush(self.display)
        time.sleep(0.6)
        self.x11.XGetInputFocus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong),
                                           ctypes.POINTER(ctypes.c_int)]
        focus, revert = ctypes.c_ulong(), ctypes.c_int()
        self.x11.XGetInputFocus(self.display, ctypes.byref(focus), ctypes.byref(revert))
        if not self.owns(focus.value):
            raise RuntimeError('Window manager did not activate the owned RViz window')

    def owns(self, window):
        for _ in range(12):
            if window == self.window:
                return True
            root, parent = ctypes.c_ulong(), ctypes.c_ulong()
            children, count = ctypes.POINTER(ctypes.c_ulong)(), ctypes.c_uint()
            self.x11.XQueryTree(self.display, window, ctypes.byref(root), ctypes.byref(parent),
                               ctypes.byref(children), ctypes.byref(count))
            if children:
                self.x11.XFree(children)
            if not parent.value or parent.value == root.value:
                return False
            window = parent.value
        return False

    def move(self, x, y):
        self.last_pointer_target = (round(x), round(y))
        self.xtst.XTestFakeMotionEvent(self.display, -1, round(x), round(y), 0)
        self.x11.XFlush(self.display)
        time.sleep(0.10)

    def button(self, down):
        if down:
            self.x11.XSendEvent(self.display, self.root_window, 0,
                               (1 << 20) | (1 << 19), ctypes.byref(self.activation_event))
            self.x11.XFlush(self.display)
            time.sleep(0.3)
        focus, revert = ctypes.c_ulong(), ctypes.c_int()
        self.x11.XGetInputFocus(self.display, ctypes.byref(focus), ctypes.byref(revert))
        if down and not self.owns(focus.value):
            self.x11.XRaiseWindow(self.display, self.frame)
            self.x11.XSetInputFocus(self.display, self.window, 1, 0)
            self.x11.XFlush(self.display)
            time.sleep(0.2)
            self.x11.XGetInputFocus(self.display, ctypes.byref(focus), ctypes.byref(revert))
            if not self.owns(focus.value):
                raise RuntimeError('RViz lost focus; refusing to click another application')
        if down:
            self.x11.XRaiseWindow(self.display, self.frame)
            self.x11.XSetInputFocus(self.display, self.window, 1, 0)
            self.x11.XFlush(self.display)
            time.sleep(0.3)
            self.x11.XQueryPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint)]
            root, parent = ctypes.c_ulong(), ctypes.c_ulong()
            children, count = ctypes.POINTER(ctypes.c_ulong)(), ctypes.c_uint()
            self.x11.XQueryTree(self.display, self.frame, ctypes.byref(root), ctypes.byref(parent), ctypes.byref(children), ctypes.byref(count))
            if children: self.x11.XFree(children)
            self.xtst.XTestFakeMotionEvent(self.display, -1, *self.last_pointer_target, 0)
            self.x11.XFlush(self.display)
            returned, child = ctypes.c_ulong(), ctypes.c_ulong()
            rx, ry, wx, wy, mask = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_uint()
            self.x11.XQueryPointer(self.display, root.value, ctypes.byref(returned), ctypes.byref(child), ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(mask))
            if child.value != self.frame:
                raise RuntimeError(f'Pointer outside owned RViz frame: child={child.value:#x}, frame={self.frame:#x}, root={root.value:#x}, pointer=({rx.value},{ry.value}), main={self.main}')
        self.xtst.XTestFakeButtonEvent(self.display, 1, int(down), 0)
        self.x11.XFlush(self.display)
        time.sleep(0.10)

    def click(self, local_x, local_y):
        self.move(self.main[2] + local_x, self.main[3] + local_y)
        self.button(True)
        try:
            time.sleep(0.15)
        finally:
            self.button(False)

    def point(self, x, y):
        angle, scale = self.view['Angle'], self.view['Scale']
        dx, dy = x - self.view['X'], y - self.view['Y']
        return (self.canvas[2] + self.canvas[0] / 2 + scale * (math.cos(angle) * dx + math.sin(angle) * dy),
                self.canvas[3] + self.canvas[1] / 2 + scale * (math.sin(angle) * dx - math.cos(angle) * dy))

    def waypoint(self, x, y):
        self.click(710, 40)
        self.move(*self.point(x, y))
        self.button(True)
        try:
            time.sleep(0.15)
        finally:
            self.button(False)

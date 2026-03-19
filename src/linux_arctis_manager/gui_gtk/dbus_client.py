import asyncio
import json
import logging
from threading import Thread

from dbus_next.aio.message_bus import MessageBus
from dbus_next.aio.proxy_object import ProxyInterface
from dbus_next.constants import MessageType
from dbus_next.message import Message

from gi.repository import GLib

from linux_arctis_manager.constants import (DBUS_BUS_NAME,
                                            DBUS_SETTINGS_INTERFACE_NAME,
                                            DBUS_SETTINGS_OBJECT_PATH,
                                            DBUS_STATUS_INTERFACE_NAME,
                                            DBUS_STATUS_OBJECT_PATH)

logger = logging.getLogger('GtkDbusClient')

class GtkDbusClient:
    def __init__(self, on_status_cb, on_settings_cb):
        self.on_status_cb = on_status_cb
        self.on_settings_cb = on_settings_cb
        
        self._status_iface: ProxyInterface|None = None
        self._settings_iface: ProxyInterface|None = None
        self._loop = None
        self._stop_future = None

    async def get_status_iface(self):
        if not self._status_iface:
            bus = await MessageBus().connect()
            introspection = await bus.introspect(DBUS_BUS_NAME, DBUS_STATUS_OBJECT_PATH)
            obj = bus.get_proxy_object(DBUS_BUS_NAME, DBUS_STATUS_OBJECT_PATH, introspection)
            self._status_iface = obj.get_interface(DBUS_STATUS_INTERFACE_NAME)
        return self._status_iface

    async def get_settings_iface(self):
        if not self._settings_iface:
            bus = await MessageBus().connect()
            introspection = await bus.introspect(DBUS_BUS_NAME, DBUS_SETTINGS_OBJECT_PATH)
            obj = bus.get_proxy_object(DBUS_BUS_NAME, DBUS_SETTINGS_OBJECT_PATH, introspection)
            self._settings_iface = obj.get_interface(DBUS_SETTINGS_INTERFACE_NAME)
        return self._settings_iface

    def start(self):
        self.request_status()
        self.request_settings()

        Thread(target=self._run_signal_loop, daemon=True).start()

    def _run_signal_loop(self):
        asyncio.run(self._async_signal_loop())

    async def _async_signal_loop(self):
        def callback(status_str: str) -> None:
            data = json.loads(status_str) or {}
            GLib.idle_add(self.on_status_cb, data)

        iface = await self.get_status_iface()
        iface.on_status_changed(callback)

        self._loop = asyncio.get_running_loop()
        self._stop_future = self._loop.create_future()
        await self._stop_future

    def stop(self):
        if self._loop and self._stop_future and not self._stop_future.done():
            self._loop.call_soon_threadsafe(self._stop_future.set_result, None)

    def request_status(self):
        Thread(target=lambda: asyncio.run(self._request_status_async()), daemon=True).start()

    async def _request_status_async(self):
        iface = await self.get_status_iface()
        result = await iface.call_get_status()
        data = json.loads(result) or {}
        GLib.idle_add(self.on_status_cb, data)

    def request_settings(self):
        Thread(target=lambda: asyncio.run(self._request_settings_async()), daemon=True).start()

    async def _request_settings_async(self):
        iface = await self.get_settings_iface()
        result = await iface.call_get_settings()
        data = json.loads(result) or {}
        GLib.idle_add(self.on_settings_cb, data)

    def request_list_options(self, list_name: str, callback):
        Thread(target=lambda: asyncio.run(self._request_list_options_async(list_name, callback)), daemon=True).start()

    async def _request_list_options_async(self, list_name: str, callback):
        bus = await MessageBus().connect()
        reply = await bus.call(Message(
            destination=DBUS_BUS_NAME,
            path=DBUS_SETTINGS_OBJECT_PATH,
            interface=DBUS_SETTINGS_INTERFACE_NAME,
            member='GetListOptions',
            message_type=MessageType.METHOD_CALL,
            signature='s',
            body=[list_name],
        ))
        if reply and reply.message_type != MessageType.ERROR:
            opts = json.loads(reply.body[0]) or []
            GLib.idle_add(callback, list_name, opts)

    def change_setting(self, name: str, value):
        Thread(target=lambda: asyncio.run(self._change_setting_async(name, value)), daemon=True).start()

    async def _change_setting_async(self, name: str, value):
        bus = await MessageBus().connect()
        await bus.call(Message(
            destination=DBUS_BUS_NAME,
            path=DBUS_SETTINGS_OBJECT_PATH,
            interface=DBUS_SETTINGS_INTERFACE_NAME,
            member='SetSetting',
            message_type=MessageType.METHOD_CALL,
            signature='ss',
            body=[name, json.dumps(value)],
        ))

#!/usr/bin/env python

import asyncio
import sys

import websockets
from websockets.server import serve
import serial
import json

CONNECTIONS = set()


def serial_ports(glob=None):
    """ Lists serial port names
        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


ser = serial.Serial()


async def echo(websocket, path):
    global ser
    CONNECTIONS.add(websocket)
    try:
        async for message in websocket:
            splits = message.split(";")
            cmd = splits[0]
            match cmd:
                case "serial_ports":
                    await websocket.send(json.dumps(serial_ports()))
                case "serial_connect":
                    await websocket.send("Connecting to serial port")
                    port = splits[1]
                    ser = serial.Serial(port, 9600, timeout=1)
                    await websocket.send("Connected to serial port")
                case "serial_send":
                    await websocket.send("Sending to serial port")
                    data = splits[1]
                    ser.write(data.encode())
                    await websocket.send("Sent to serial port")
                case "serial_read":
                    await websocket.send("Reading from serial port")
                    data = ser.readline().decode("utf-8")
                    await websocket.send("Read from serial port")
                    await websocket.send(data)
                case "serial_close":
                    await websocket.send("Closing serial port")
                    ser.close()
                    await websocket.send("Closed serial port")
                case _:
                    await websocket.send("Unknown cmd")
    finally:
        CONNECTIONS.remove(websocket)


async def startWSServer():
    async with serve(echo, "localhost", 8765):
        await asyncio.Future()  # run forever


async def SerialListener():
    # Check if ser is open
    while not ser.isOpen():
        await asyncio.sleep(1)
    # Loop forever
    while ser.isOpen():
        # Read from serial
        data = ser.readline().decode("utf-8")
        if data != "":
            # Send to websocket
            websockets.broadcast(CONNECTIONS, data)
        # Wait for 1 second
        await asyncio.sleep(0.1)


async def start():
    await asyncio.gather(startWSServer(), SerialListener())


if __name__ == "__main__":
    asyncio.run(start())

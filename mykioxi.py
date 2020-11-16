#!/usr/bin/env python3
import asyncio
import argparse
import sys

import bleak

CHARACTERISTIC_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"

class LogHandler:
    def __init__(self):
        self.last_bpm = -1
        self.last_spo2 = -1

    def data_handler(self, bpm, spo2):
        if bpm != self.last_bpm or spo2 != self.last_spo2:
            print_bpm = '---' if bpm == 255 else str(bpm).rjust(3)
            print_spo2 = '---' if spo2 == 127 else str(spo2).rjust(3)
            print("BPM: {}, SpO2: {}".format(print_bpm, print_spo2))
            self.last_bpm, self.last_spo2 = bpm, spo2

def make_handler(user_handler):
    def raw_handler(sender, data):
        bpm = data[3] | ((data[2] & 64) << 1)
        spo2 = data[4]
        user_handler(bpm, spo2)
    return raw_handler

async def discover():
    devices = await bleak.discover()
    for d in devices:
        if d.name == "BerryMed" or d.address.startswith("00:A0:50"):
            return d

async def read_data(address, done, handler):
    async with bleak.BleakClient(address) as client:
        x = await client.is_connected()
        print("Connected: {0}".format(x))

        notification_handler = make_handler(handler)
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        await done.wait()
        print('Disconnecting ...')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", help="Device address")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    if not args.device:
        dev = loop.run_until_complete(discover())
        if dev is None:
            print("No device found")
            sys.exit(1)
        print("Found: {} ({})".format(dev.address, dev.name))
        address = dev.address
    else:
        address = args.device

    done = asyncio.Event()
    lh = LogHandler()
    task = loop.create_task(read_data(address, done, lh.data_handler))
    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        done.set()

    loop.run_until_complete(task)

if __name__ == "__main__":
    main()

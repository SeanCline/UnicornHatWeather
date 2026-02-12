import asyncio
import collections
import struct
from dataclasses import dataclass
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from .WeatherCollector import WeatherCollector, WeatherStatus, Datapoint

TEMPEST_SERVICE_UUID = "6a223200-4f03-41b0-ce48-7b3880d357d6"
TEMPEST_CHARACTERISTIC_UUID = "6a223201-4f03-41b0-ce48-7b3880d357d6"

@dataclass
class PacketFormat:
    packet_type: int
    layout : struct.Struct
    fields : tuple[str, ...]

STATUS_PACKET = PacketFormat(0x1A,
    struct.Struct('<B 16x H x'),
    ('packet_type', 'voltagex1000'),
)

SKY_PACKET = PacketFormat(0x52, # precip in the 4x padding?
    struct.Struct('<B 6x I H 4x H'),
    ('packet_type', 'illuminance_lux', 'uv_indexx100', 'solar_radiation'),
)

WIND_AVG_PACKET = PacketFormat(0x53,
    struct.Struct('<B 6x h h h h 3x'),
    ('packet_type', 'wind_speed_avgx100', 'wind_dir_avg', 'wind_lullx100', 'wind_gustx100')
)

AIR_PACKET = PacketFormat(0x54,
    struct.Struct('<B 6x h h B x B I'),
    ('packet_type', 'temperaturex100', 'humidityx100', 'lightning_strike_count', 'lightning_avg_distance', 'pressurex100'),
)

#WIND_INSTANT_PACKET = PacketFormat(0x18,
#    struct.Struct('<B 6x h h'),
#    ('packet_type', 'wind_speedx100', 'wind_dir'),
#)

def _unpack_packet(pkt : PacketFormat, data : bytearray):
    type = data[0]
    if (pkt.packet_type != type):
        raise RuntimeError("TempestBleCollector - Unexpected packet type. Expecting {pkt.packet_type:02x} but got {type:02x}")
    FieldData = collections.namedtuple('FieldData', pkt.fields)
    return FieldData._make(pkt.layout.unpack_from(data))

class TempestBleCollector(WeatherCollector):
    def __init__(self, config : dict):
        super().__init__()
        self._station_mac = config["station_mac"].upper()
        self.status = WeatherStatus()

    def _decode_notify(self, data : bytearray):
        if len(data) == 0:
            return
        
        packet_type = data[0]
        decoded = None
        if packet_type == STATUS_PACKET.packet_type:
            decoded = _unpack_packet(STATUS_PACKET, data)
        elif packet_type == SKY_PACKET.packet_type:
            decoded = _unpack_packet(SKY_PACKET, data)
            self.status.illuminance_lux = Datapoint(decoded.illuminance_lux, 1.0)
            self.status.uv_index = Datapoint(decoded.uv_indexx100 / 100.0, 1.0)
            self.status.solar_radiation_wpm2 = Datapoint(decoded.solar_radiation, 1.0)
        elif packet_type == WIND_AVG_PACKET.packet_type:
            decoded = _unpack_packet(WIND_AVG_PACKET, data)
            self.status.wind_avg_mps = Datapoint(decoded.wind_speed_avgx100 / 100.0, 1.0)
            #decoded.wind_dir_avg
            #decoded.wind_lullx100 / 100.0
            #decoded.wind_gustx100 / 100.0
        elif packet_type == AIR_PACKET.packet_type:
            decoded = _unpack_packet(AIR_PACKET, data)
            self.status.temp_c = Datapoint(decoded.temperaturex100 / 100.0, 1.0)
            self.status.humidity_pct = Datapoint(decoded.humidityx100 / 100.0, 1.0)
            self.status.lightning_count = Datapoint(decoded.lightning_strike_count, 1.0)
            self.status.lightning_distance = Datapoint(decoded.lightning_avg_distance, 1.0)
            self.status.pressure_mb = Datapoint(decoded.pressurex100 / 100.0, 1.0)
        #elif packet_type == WIND_INSTANT_PACKET.packet_type:
        #    decoded = _unpack_packet(WIND_INSTANT_PACKET, data)

        # TODO: Figure out how to subscribe for wind events.
        # TODO: Figure out how to subscribe to lightning events.
        # TODO: Figure out where precipitation type and amount are stored.
        # TODO: Generate conditionstring and icon.

        if decoded is not None:
            # Got a new packet. Do some housekeeping.
            self.status.host_timestamp = self.status.source_timestamp = datetime.now(timezone.utc)
            self.status.source = 'TempestBleCollector'
            self._deliver_update(self.status)

    async def _notification_handler(self, sender : BleakGATTCharacteristic, data : bytearray):
        print(f"Notify from {self._station_mac} {sender.service_uuid}: {data.hex()} len={len(data)}")
        self._decode_notify(data)

    async def listen(self):
        """Starts listening for BLE notifications from the Tempest. This will run until cancelled."""
        while True:
            try:
                async with BleakClient(self._station_mac) as client:
                    print("Connected to TempestBLE")

                    await client.start_notify(
                        TEMPEST_CHARACTERISTIC_UUID,
                        self._notification_handler
                    )

                    while client.is_connected:
                        await asyncio.sleep(15000)
            except Exception as ex:
                print("Error in bluetooth connection. {ex}")
                await asyncio.sleep(60000) # Try to recover from the error later.
            print("Disconnected from TempestBLE")
            

async def debug_status():
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
    import config

    bleCollector = TempestBleCollector(config.tempest_ble_config)
    bleCollector.register_callback(lambda status: print(status))

    from WeatherCollectors.TempestUdpCollector import TempestUdpCollector
    udpCollector = TempestUdpCollector(config.tempest_udp_config)
    udpCollector.register_callback(lambda status: print(status))

    await asyncio.gather(bleCollector.listen(), udpCollector.listen()) # Run forever for debugging.

if __name__ == "__main__":
    ws = WeatherStatus()
    asyncio.run(debug_status())

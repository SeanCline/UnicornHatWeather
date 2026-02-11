import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from .WeatherCollector import WeatherCollector, WeatherStatus, Datapoint

UDP_PORT = 50222
OBS_ST_MAX_AGE = timedelta(seconds=120)

OBS_AIR_IDX = {
    "Time Epoch"                    : 0, # Seconds
    "Station Pressure"              : 1, # MB
    "Air Temperature"               : 2, # C
    "Relative Humidity"             : 3, # %
    "Lightning Strike Count"        : 4, 
    "Lightning Strike Avg Distance" : 5, # km
    "Battery"                       : 6, 
    "Report Interval"               : 7, # Minutes
}

OBS_SKY_IDX = {
    "Time Epoch"                  : 0,  # Seconds
    "Illuminance"                 : 1,  # Lux
    "UV"                          : 2,  # Index
    "Rain amount"                 : 3,  # (over previous minute) mm/minute
    "Wind Lull"                   : 4,  # (minimum 3 second sample) m/s
    "Wind Avg"                    : 5,  # (average over report interval) m/s
    "Wind Gust"                   : 6,  # (maximum 3 second sample) m/s
    "Wind Direction"              : 7,  # Degrees
    "Battery"                     : 8,  # Volts
    "Report Interval"             : 9,  # Minutes
    "Solar Radiation"             : 10, # W/m^2
    "Local Day Rain Accumulation" : 11, # mm
    "Precipitation Type"          : 12, # 0 = none, 1 = rain, 2 = hail
    "Wind Sample Interval"        : 13, # seconds
}

OBS_ST_IDX = {
    "Time Epoch"                    : 0,  # Seconds
    "Wind Lull"                     : 1,  # (minimum 3 second sample) m/s
    "Wind Avg"                      : 2,  # (average over report interval) m/s
    "Wind Gust"                     : 3,  # (maximum 3 second sample) m/s
    "Wind Direction"                : 4,  # Degrees
    "Wind Sample Interval"          : 5,  # seconds
    "Station Pressure"              : 6,  # MB
    "Air Temperature"               : 7,  # C
    "Relative Humidity"             : 8,  # %
    "Illuminance"                   : 9,  # Lux
    "UV"                            : 10, # Index
    "Solar Radiation"               : 11, # W/m^2
    "Rain amount"                   : 12, # (over previous minute) mm/minute
    "Precipitation Type"            : 13, # 0 = none, 1 = rain, 2 = hail, 3 = rain + hail (experimental)
    "Lightning Strike Avg Distance" : 14, # km
    "Lightning Strike Count"        : 15, 
    "Battery"                       : 16, # Volts
    "Report Interval"               : 17, # Minutes
}

ICONS = (
    "clear sky",
    "scattered clouds",
    "cloudy",
    "shower rain",
    "rain",
    "lightning",
    "snow",
    "fog",
)


class TempestUdpCollector(WeatherCollector):
    def __init__(self, config : dict):
        super().__init__()
        self.status = WeatherStatus()
        self._udp_transport = None
        self._config = config

    def _decode_precipitation(self, v) -> str:
        """Converts the Weatherflow precipitation type code to a human readable string."""
        return {0: "none", 1: "rain", 2: "hail", 3: "hail"}.get(v) or "none" # 3 == rain|hail, but it's experimental and rare, so just call it hail.

    def _handle_obs_air(self, obs, idx = OBS_AIR_IDX):
        self.status.source = "obs_air"
        self.status.host_timestamp = datetime.now(timezone.utc)
        self.status.source_timestamp = datetime.fromtimestamp(obs[idx["Time Epoch"]], tz=timezone.utc)
        self.status.temp_c = Datapoint(obs[idx["Air Temperature"]], 1.0) # Air temp and other direct readings are reliable, so quality=1.0
        self.status.humidity_pct = Datapoint(obs[idx["Relative Humidity"]], 1.0)
        self.status.pressure_mb = Datapoint(obs[idx["Station Pressure"]], 1.0)
        self.status.lightning_count = Datapoint(obs[idx["Lightning Strike Count"]], 1.0)
        self.status.lightning_distance = Datapoint(obs[idx["Lightning Strike Avg Distance"]], 1.0)
        
    def _handle_obs_sky(self, obs, idx = OBS_SKY_IDX):
        self.status.source = "obs_sky"
        self.status.host_timestamp = datetime.now(timezone.utc)
        self.status.source_timestamp = datetime.fromtimestamp(obs[idx["Time Epoch"]], tz=timezone.utc)
        self.status.illuminance_lux = Datapoint(obs[idx["Illuminance"]], 1.0)
        self.status.uv_index = Datapoint(obs[idx["UV"]], 1.0)
        self.status.wind_avg_mps = Datapoint(obs[idx["Wind Avg"]], 1.0)
        self.status.rain_mm = Datapoint(obs[idx["Rain amount"]], 0.5) # Instantaneous rain amount is a bit noisy.
        self.status.precip_type = Datapoint(self._decode_precipitation(obs[idx["Precipitation Type"]]), 1.0)
        
    def _handle_obs_st(self, obs):
        # obs_st packets contain readings from both obs_air and obs_sky.
        # We can reuse the same handlers, with the indexes from OBS_ST_IDX.
        self._handle_obs_air(obs, idx = OBS_ST_IDX)
        self._handle_obs_sky(obs, idx = OBS_ST_IDX)
        self.status.source = "obs_st"

    def _calculate_condition_string(self, ws : WeatherStatus) -> Optional[Datapoint[str]]:
        """
        Determines the condition_string based on the current readings.
        This is mostly a wild guess at the moment. Good condition estimates
        require far more inputs, and/or historical data.
        """

        # First, see if there should be a lightning icon.
        if (ws.lightning_count and ws.lightning_count.value > 0
        and ws.lightning_distance and ws.lightning_distance.value < 12):
            return Datapoint("lightning", 1.0)

        # Next, consider precipication.
        if ws.precip_type and ws.precip_type.value == "rain":
            if ws.rain_mm is not None and ws.rain_mm.value < 0.5:
                return Datapoint("shower rain", 0.5)
            else:
                return Datapoint("rain", 1.0)
        elif ws.precip_type and ws.precip_type.value == "hail":
            return Datapoint("snow", 0.0) # Best we can do.

        # See if there's a chance of mist (fog), otherwise, fall back on whether it's cloudy.
        if ws.illuminance_lux:
            if (ws.humidity_pct and ws.humidity_pct.value >= 95 and ws.illuminance_lux.value < 20000):
                return Datapoint("mist", 0.0)
            else:
                if ws.illuminance_lux.value > 100000:
                    return Datapoint("clear sky", 0.0) # If it's bright enough, we can be pretty sure it's clear.
                elif ws.illuminance_lux.value > 5000:
                    return Datapoint("scattered clouds", -1.0) # Less reliable when it's night bright. Could be dawn/dusk/winter.
                elif ws.illuminance_lux.value > 500:
                    return Datapoint("cloudy", -1.0)
                else:
                    return None # If its completely dark outside, there's no way to know cloud cover.

    def _calculate_openweathermap_icon(self, ws : WeatherStatus) -> Optional[Datapoint[str]]:
        """
        Use the condition_string to determines the closest openweathermap_icon.
        """
        if not ws.condition_string or not ws.condition_string.value:
            return None
        mapping = {
            "clear sky": "01",
            "scattered clouds": "02",
            "cloudy": "03",
            "shower rain": "09",
            "rain": "10",
            "lightning": "11",
            "snow": "13",
            "mist": "50",
        }

        icon_number = mapping[ws.condition_string.value]
        icon_daynight = "d" if ws.illuminance_lux is None or ws.illuminance_lux.value > 5000 else "n"
        return Datapoint(icon_number + icon_daynight, ws.condition_string.quality)

    def _update_condition_and_icon(self, ws : WeatherStatus):
        ws.condition_string = self._calculate_condition_string(ws)
        ws.openweathermap_icon = self._calculate_openweathermap_icon(ws)

    def _is_packet_from_allowed_source(self, msg, addr) -> bool:
        if self._config is None:
            return True # No filtering configured.
        
        try:
            if 'allowed_hub_ips' in self._config:
                if not isinstance(addr, tuple) or addr[0] not in self._config['allowed_hub_ips']:
                    print(f'Received message from IP not in allowed list: {addr}')
                    return False
                
            if 'allowed_hub_sns' in self._config:
                hub_sn = msg.get('hub_sn')
                if hub_sn is None or hub_sn not in self._config['allowed_hub_sns']:
                    print(f'Received message from hub_sn not in allowed list: {hub_sn}')
                    return False
                
            if 'allowed_station_sns' in self._config:
                station_sn = msg.get('serial_number')
                if station_sn is None or station_sn not in self._config['allowed_station_sns']:
                    print(f'Received message from station_sn not in allowed list: {station_sn}')
                    return False
        except Exception as e:
            print(f'Error checking allowed source lists: {e}')
            return False
    
        return True

    def _process_packet(self, msg):
        t = msg.get("type")
        obs = msg.get("obs")
        if not obs:
            return

        # obs is a list of lists. Unwrap it.
        obs = obs[0]

        if t == "obs_st":
            self._handle_obs_st(obs)
        elif t == "obs_air":
            if (self.status.source != "obs_st"
              or self.status.host_timestamp is None or
              (datetime.now(timezone.utc) - self.status.host_timestamp) > OBS_ST_MAX_AGE):
                self._handle_obs_air(obs)
        elif t == "obs_sky" and self.status.source != "obs_st":
            if (self.status.source != "obs_st"
              or self.status.host_timestamp is None or
              (datetime.now(timezone.utc) - self.status.host_timestamp) > OBS_ST_MAX_AGE):
                self._handle_obs_sky(obs)
        else:
            return False # No new data.

        self._update_condition_and_icon(self.status)
        return True # New data in self.status.

    class _DatagramProtocol(asyncio.DatagramProtocol):
        def __init__(self, collector):
            self.collector = collector

        def datagram_received(self, data, addr):
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                return # Malformed packet, ignore.
            
            if not self.collector._is_packet_from_allowed_source(msg, addr):
                return # Packet not from an allowed source.

            # Process the packet and deliver updates to callbacks if there is new data.
            if self.collector._process_packet(msg):
                self.collector._deliver_update(self.collector.status)

    async def listen(self):
        """Starts listening for UDP packets from the Tempest. This will run until cancelled."""
        self._udp_transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: self._DatagramProtocol(self),
            local_addr=("0.0.0.0", UDP_PORT),
        )

        while True:
            try:
                await asyncio.sleep(1000)
            except asyncio.CancelledError:
                self._udp_transport.close()
                raise # Propagate the cancellation to the awaiter.

async def debug_status():
    import config
    collector = TempestUdpCollector(config.tempest_udp_config)
    collector.register_callback(lambda status: print(status))
    await collector.listen() # Run forever for debugging.

if __name__ == "__main__":
    ws = WeatherStatus()
    asyncio.run(debug_status())

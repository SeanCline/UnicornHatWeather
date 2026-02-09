from typing import Callable, List
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Optional, TypeVar

DatapointT = TypeVar("DatapointT")
@dataclass
class Datapoint(Generic[DatapointT]):
    value: DatapointT = None
    quality: float = 0.0 # Negative for untrusted values, 0.0 for acceptable, positive for very reliable.


@dataclass
class WeatherStatus:
    source: Optional[str] = None # Weatherflow: ("obs_air", "obs_sky", "obs_st"), OpenWeatherMap: "openweathermap", etc.
    host_timestamp: Optional[datetime] = None
    source_timestamp: Optional[datetime] = None
    
    # Air
    temp_c: Optional[Datapoint[float]] = None
    humidity_pct: Optional[Datapoint[float]] = None
    pressure_mb: Optional[Datapoint[float]] = None

    # Sky
    illuminance_lux: Optional[Datapoint[float]] = None
    uv_index: Optional[Datapoint[float]] = None
    wind_avg_mps: Optional[Datapoint[float]] = None

    # Precip / lightning
    precip_type: Optional[Datapoint[str]] = None # "rain", "hail", None
    rain_mm: Optional[Datapoint[float]] = None
    lightning_count: Optional[Datapoint[int]] = None
    lightning_distance: Optional[Datapoint[float]] = None

    # Inferred readings.
    condition_string: Optional[Datapoint[str]] = None
    openweathermap_icon: Optional[Datapoint[str]] = None


class WeatherCollector:
    def __init__(self):
        self._callbacks : List[Callable[[WeatherStatus], None]] = []

    async def start_listening(self):
        """Client code calls this override to request that the collector to start collecting data and delivering callbacks."""
        pass

    async def stop_listening(self):
        """Client code calls this override to request that the collector stop collecting data."""
        pass

    def register_callback(self, callback):
        """Registers a callback for when new weather data is received. The callback will be called with the new WeatherStatus as an argument."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback):
        """Unregisters a previously registered callback. The callback will no longer be called when new weather data is received."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _deliver_update(self, status : WeatherStatus):
        """Delivers a new weather update to all registered callbacks. This should be called by the collector implementation when new data is received."""
        for callback in self._callbacks:
            if callback is not None:
                callback(status)

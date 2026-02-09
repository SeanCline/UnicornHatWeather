from ast import List, Tuple
import asyncio
from dataclasses import dataclass, fields
from datetime import datetime
import typing
from .WeatherCollector import WeatherCollector, WeatherStatus, Datapoint

def is_datapoint(field) -> bool:
    # First, see if it's directly a Datapoint.
    if typing.get_origin(field.type) is Datapoint:
        return True
    # Next, see if it's Optional[Datapoint]
    if typing.get_origin(field.type) is typing.Union:
        args = typing.get_args(field.type)
        if len(args) == 2 and typing.get_origin(args[0]) is Datapoint and args[1] is type(None):
            return True
    return False

class AggregateCollector(WeatherCollector):
    """Collects weather data from multiple sources and aggregates it based on age and quality."""

    @dataclass
    class CollectorData:
        """Represents the data from a single collector."""
        status : WeatherStatus
        callback : typing.Callable[[WeatherStatus], None] # Need to hold onto the callback so we can unregister it later.

    def __init__(self, collectors : list[WeatherCollector] = None, quality_decay : float = .005):
        super().__init__()
        self._collectors  = {}
        for c in collectors or []:
            self._collectors[c] = self.CollectorData(None, lambda status, c=c: self._update_collector_status(c, status)) # No data yet.
            c.register_callback(self._collectors[c].callback)
        self._quality_decay = quality_decay # Every second, reduce the quality of each datapoint by this amount.
        self._is_listening = False

    async def register_collector(self, collector : WeatherCollector):
        """Registers a WeatherCollector as a source of data to aggregate."""
        if collector in self._collectors.keys():
            return # Already registered.
        
        self._collectors[collector] = self.CollectorData(None, lambda status: self._update_collector_status(collector, status)) # No data yet.
        collector.register_callback(self._collectors[collector].callback)
        if self._is_listening:
            collector.start_listening() # Start the collector if we're already listening for updates.

    def unregister_collector(self, collector : WeatherCollector):
        """Unregisters a WeatherCollector so it is no longer a source of data."""
        if collector not in self._collectors.keys():
            return # Not registered.
        
        collector.unregister_callback(self._collectors[collector].callback)
        if collector in self._collectors.keys():
            del self._collectors[collector]

    async def start_listening(self):
        """Starts all registered collectors and begins delivering aggregate updates."""
        if self._is_listening:
            return # Already listening.
        
        self._is_listening = True
        for collector in self._collectors.keys():
            await asyncio.gather(*(collector.start_listening() for collector in self._collectors.keys()))

    async def stop_listening(self):
        """Stops all registered collectors and stops delivering updates."""
        if not self._is_listening:
            return # Not currently listening.
        
        self._is_listening = False
        await asyncio.gather(*(collector.stop_listening() for collector in self._collectors.keys()))

    def _update_collector_status(self, collector : WeatherCollector, status : WeatherStatus):
        """Updates the status for a given collector and recomputes the aggregate status."""
        if collector not in self._collectors.keys():
            return # Not registered. Collector might be mid-register/unregister.
        
        self._collectors[collector].status = status
        aggregate_status = self._generate_aggregate_status()
        self._deliver_update(aggregate_status)

    def _generate_aggregate_status(self):
        """Generates an aggregate WeatherStatus based on the current data from all collectors."""
        aggregate = WeatherStatus()
        aggregate.host_timestamp = datetime.now()

        # For each Datapoint field in WeatherStatus, find the highest-quality datapoint from all collectors.
        for f in fields(WeatherStatus):
            candidates : List[Tuple[Datapoint, float]] = []
            for collector_data in self._collectors.values():
                status = collector_data.status
                if status is None:
                    continue
                
                if not is_datapoint(f):
                    continue # Skip non-datapoint fields.

                datapoint = getattr(status, f.name)
                if datapoint is None or datapoint.value is None or not isinstance(datapoint, Datapoint):
                    continue # No data for this field. Skip it.
                
                # Decay the datapoint quality based on how old it is. This will make a good, but old datapoint eventually
                # fall out of favour compared to a newer but lower-quality datapoint.
                age_seconds = (datetime.now(tz=status.host_timestamp.tzinfo) - status.host_timestamp).total_seconds()
                aged_quality = datapoint.quality - age_seconds * self._quality_decay
                
                candidates.append((datapoint, aged_quality))
            
            # Combine the field values into a single datapoint for the aggregate status.
            if len(candidates) == 0:
                setattr(aggregate, f.name, None) # No data for this field from any collector.
                continue

            # Sort by aged quality, highest first.
            candidates.sort(key=lambda c: c[1], reverse=True)
            best_datapoint = candidates[0][0] # Take the highest-quality datapoint.
            setattr(aggregate, f.name, Datapoint(best_datapoint.value, best_datapoint.quality))

        return aggregate
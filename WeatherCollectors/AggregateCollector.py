import asyncio
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
import typing
from typing import Optional, List, Tuple
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
        status : Optional[WeatherStatus]
        callback : typing.Callable[[WeatherStatus], None] # Need to hold onto the callback so we can unregister it later.

    def __init__(self, collectors : Optional[List[WeatherCollector]] = None, datapoint_max_age : Optional[timedelta] = None, quality_decay : float = .001):
        super().__init__()
        self._collectors  = {}
        self._datapoint_max_age = datapoint_max_age
        for c in collectors or []:
            self._collectors[c] = self.CollectorData(None, lambda status, c=c: self._update_collector_status(c, status)) # No data yet.
            c.register_callback(self._collectors[c].callback)
        self._quality_decay = quality_decay # Every second, reduce the quality of each datapoint by this amount.

    async def listen(self):
        """Starts all registered collectors and begins delivering aggregate updates."""
        await asyncio.gather(*(collector.listen() for collector in self._collectors.keys()))

    def _update_collector_status(self, collector : WeatherCollector, status : WeatherStatus):
        """Updates the status for a given collector and recomputes the aggregate status."""
        if collector not in self._collectors.keys():
            return # Not registered. Collector might be mid-register/unregister.
        
        print(f'{type(collector).__name__} received new status: {status}')

        self._collectors[collector].status = status
        aggregate_status = self._generate_aggregate_status()
        self._deliver_update(aggregate_status)

    def _generate_aggregate_status(self) -> WeatherStatus:
        """Generates an aggregate WeatherStatus based on the current data from all collectors."""
        aggregate = WeatherStatus()
        aggregate.source = 'aggregate'
        aggregate.host_timestamp = datetime.now(timezone.utc)

        # For each Datapoint field in WeatherStatus, find the highest-quality datapoint from all collectors.
        for f in fields(WeatherStatus):
            if not is_datapoint(f):
                continue # Skip non-datapoint fields.

            candidates : List[Tuple[Datapoint, float]] = []
            for collector_data in self._collectors.values():
                status = collector_data.status
                if status is None:
                    continue
                
                datapoint = getattr(status, f.name)
                if not isinstance(datapoint, Datapoint) or datapoint.value is None:
                    continue # No data for this field. Skip it.
                
                # Decay the datapoint quality based on how old it is. This will make a good, but old datapoint eventually
                # fall out of favour compared to a newer but lower-quality datapoint.
                age_seconds = (datetime.now(tz=status.host_timestamp.tzinfo) - status.host_timestamp).total_seconds()
                if self._datapoint_max_age is None or timedelta(seconds=age_seconds) < self._datapoint_max_age:
                    aged_quality = datapoint.quality - age_seconds * self._quality_decay
                    candidates.append((datapoint, aged_quality))
            
            # Combine the field values into a single datapoint for the aggregate status.
            if len(candidates) == 0:
                setattr(aggregate, f.name, None) # No data for this field from any collector.
                continue

            # Sort by aged quality, highest first.
            candidates.sort(key=lambda c: c[1], reverse=True)
            # Find the max quality element in linear time
            best_datapoint = max(candidates, key=lambda c: c[1])[0]
            best_datapoint = candidates[0][0] # Take the highest-quality datapoint.
            setattr(aggregate, f.name, Datapoint(best_datapoint.value, best_datapoint.quality))

        return aggregate
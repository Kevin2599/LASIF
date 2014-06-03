#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .component import Component


class QueryComponent(Component):
    """
    This component is responsible for making queries across the different
    components and integrating them in a meaningful way.

    :param communicator: The communicator instance.
    :param component_name: The name of this component for the communicator.

    It should thus be initialized fairly late as it needs access to a number
    of other components via the communicator.
    """
    def get_all_stations_for_event(self, event_name):
        """
        Returns a list of all stations for one event.

        A station is considered to be available for an event if at least one
        channel has raw data and an associated station file. Furthermore it
        must be possible to derive coordinates for the station.

        :type event_name: str
        :param event_name: Name of the event.

        >>> import pprint
        >>> comm = getfixture('query_comm')
        >>> pprint.pprint(comm.query.get_all_stations_for_event(
        ...     "GCMT_event_TURKEY_Mag_5.1_2010-3-24-14-11")) \
        # doctest: +NORMALIZE_WHITESPACE
        {u'HL.ARG': {'elevation_in_m': 170.0, 'latitude': 36.216,
                     'local_depth_in_m': 0.0, 'longitude': 28.126},
         u'HT.SIGR': {'elevation_in_m': 93.0, 'latitude': 39.2114,
                      'local_depth_in_m': 0.0, 'longitude': 25.8553},
         u'KO.KULA': {'elevation_in_m': 915.0, 'latitude': 38.5145,
                      'local_depth_in_m': 0.0, 'longitude': 28.6607},
         u'KO.RSDY': {'elevation_in_m': 0.0, 'latitude': 40.3972,
                      'local_depth_in_m': 0.0, 'longitude': 37.3273}}


        Raises a :class:`~lasif.LASIFNotFoundError` if the event does not
        exist.

        >>> comm.query.get_all_stations_for_event("RandomEvent")
        Traceback (most recent call last):
            ...
        LASIFNotFoundError: ...
        """
        event = self.comm.events.get(event_name)

        # Collect information from all the different places.
        waveform_metadata = self.comm.waveforms.get_metadata_raw(event_name)
        station_coordinates = self.comm.stations.get_all_channels_at_time(
            event["origin_time"])
        inventory_coordinates = self.comm.inventory_db.get_all_coordinates()

        stations = {}
        for waveform in waveform_metadata:
            station_id = "%s.%s" % (waveform["network"], waveform["station"])
            if station_id in stations:
                continue

            try:
                stat_coords = station_coordinates[waveform["channel_id"]]
            except KeyError:
                # No station file for channel.
                continue

            # First attempt to retrieve from the station files.
            if stat_coords["latitude"] is not None:
                stations[station_id] = stat_coords
                continue
            # Then from the waveform metadata in the case of a sac file.
            elif waveform["latitude"] is not None:
                stations[station_id] = waveform
                continue
            # If that still does not work, check if the inventory database
            # has an entry.
            elif station_id in inventory_coordinates:
                coords = inventory_coordinates[station_id]
                # Otherwise already queried for, but no coordinates found.
                if coords["latitude"]:
                    stations[station_id] = coords
                continue

            # The last resort is a new query via the inventory database.
            coords = self.comm.inventory_db.get_coordinates(station_id)
            if coords["latitude"]:
                stations[station_id] = coords
        return stations
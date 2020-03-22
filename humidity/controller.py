import asyncio
import logging
import os
import re
import statistics
from typing import List, Tuple

import pendulum
from matplotlib import pyplot as plt
from matplotlib import dates
import serial
import sqlite3

from humidity.definitions import Sensor, Database, TempidityError, TempidityDataPoint

log = logging.getLogger(__name__)


class TempidityController:
    def __init__(self, sensor: Sensor, database: Database):
        if not isinstance(sensor, Sensor):
            raise TempidityError('sensor must be of type Sensor.')

        if not isinstance(database, Database):
            raise TempidityError('database must be of type Database.')

        self.sensor = sensor
        self.database = database
        self.is_humidifier_on = False
        self.recording_task = None

    async def start_recording(self, is_humidifier_on: bool):
        if self.recording_task is not None:
            raise TempidityError('Already recording.')

        self.is_humidifier_on = is_humidifier_on
        log.info(f'Reporting that humidifier is on: {self.is_humidifier_on}')

        self.recording_task = asyncio.create_task(self._start_recording_task())

    async def stop_recording(self):
        await self._cleanup_task()

    async def plot_data(self, start_datetime: pendulum.DateTime, stop_datetime: pendulum.DateTime):
        rows = await self._query_data_points_between(start_datetime, stop_datetime)

        x = []
        y_humidity = []
        y_temperature = []
        y_humidifier_on = []

        for row in rows:
            timestamp_value = row[0]
            humidity_percent = row[1]
            temperature_celsius = row[2]
            humidifier_on = row[3]

            x_value = dates.date2num(pendulum.from_timestamp(timestamp_value))

            x.append(x_value)
            y_humidity.append(humidity_percent)
            y_temperature.append(temperature_celsius)
            y_humidifier_on.append(humidifier_on)

        num_points = len(x)
        if num_points > 0:
            log.info(f'Plotting {num_points} points.')
            
            figure = plt.figure()

            axis = figure.add_subplot(3, 1, 1)
            axis.plot_date(x, y_humidity, tz='UTC')
            axis.set_title('Humidity (%)')

            axis = figure.add_subplot(3, 1, 2)
            axis.plot_date(x, y_temperature, tz='UTC')
            axis.set_title('Temperature (C)')

            axis = figure.add_subplot(3, 1, 3)
            axis.plot_date(x, y_humidifier_on, tz='UTC')
            axis.set_title('Humidifier On')

            plt.show()
        else:
            log.warning('Could not find any points.')

    async def get_recent_data(self, num_points: int):
        rows = await self._query_most_recent_points(num_points)

        output = []
        for row in rows:
            timestamp_value = row[0]
            humidity_percent = row[1]
            temperature_celsius = row[2]
            humidifier_on = row[3]

            entry = {
                'timestamp': f'{pendulum.from_timestamp(timestamp_value)}',
                'humidity_percent': humidity_percent,
                'temperature_celsius': temperature_celsius,
                'humidifier_on': bool(humidifier_on)
            }

            output.append(entry)

        return output

    async def _create_database(self):
        log.info(f'Creating database {self.database.name}.')

        with sqlite3.connect(self.database.name) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """CREATE TABLE sensor_data (
                    timestamp_value real,
                    humidity real,
                    temperature real,
                    humidifier_on integer)""")

            connection.commit()

    async def _write_to_database(self, datapoint: TempidityDataPoint):
        if not isinstance(datapoint, TempidityDataPoint):
            raise TempidityError('datapoint must be of type TempidityDataPoint.')

        if not os.path.isfile(self.database.name):
            await self._create_database()

        timestamp = pendulum.DateTime.utcnow().timestamp()
        humidity = datapoint.humidity_percent
        temperature = datapoint.temperature_celsius
        is_humidifier_on = self.is_humidifier_on

        args = (timestamp, humidity, temperature, is_humidifier_on)

        log.info(f'Adding datapoint: {args}')

        with sqlite3.connect(self.database.name) as connection:
            cursor = connection.cursor()

            cursor.execute(
                'INSERT INTO sensor_data VALUES (?,?,?,?)', args)

            connection.commit()

    async def _query_data_points_between(self, start_datetime: pendulum.DateTime, stop_datetime: pendulum.DateTime) -> List[Tuple]:
        log.info(f'Querying database for datapoints between {start_datetime} and {stop_datetime}.')

        start_timestamp = start_datetime.timestamp()
        stop_timestamp = stop_datetime.timestamp()

        with sqlite3.connect(self.database.name) as connection:
            cursor = connection.cursor()

            args = (start_timestamp, stop_timestamp)

            cursor.execute(
                'SELECT * FROM sensor_data WHERE timestamp_value BETWEEN ? AND ?', args)

            rows = cursor.fetchall()

            return rows

    async def _query_most_recent_points(self, num_points: int) -> List[Tuple]:
        log.info(f'Querying database for {num_points} most recent datapoints.')

        with sqlite3.connect(self.database.name) as connection:
            cursor = connection.cursor()

            # We're creating a tuple with only one value.
            args = (num_points, )

            cursor.execute(
                'SELECT * FROM sensor_data ORDER BY timestamp_value DESC LIMIT ?', args)

            rows = cursor.fetchall()

            return rows


    async def _start_recording_task(self):
        """Start the asynchronous recording task.

        Algorithm:
        1. Collect datapoints from the Arduino for 1 minute and store
           the datapoints into a list. After 1 minute, we should have
           20-30 datapoints.
        2. Store the following into a database:
               - Timestamp
               - Median temperature
               - Median humidity
               - Is the humidifier on
            The goal is to store 1 datapoint a minute, so out of all
            those datapoints, only 1 gets saved.
        3. Erase all the datapoints.
        4. Go to step 1.
        """
        try:
            while True:
                # This sleep is important because it allows
                # views.start_recording to return a response right away.
                await asyncio.sleep(1)
                duration = pendulum.Duration(minutes=1)
                datapoints = await self._read_datapoints(duration)
                chosen_datapoint = await self._process_datapoints(datapoints)
                await self._write_to_database(chosen_datapoint)
        except asyncio.CancelledError:
            log.info(f'Cancelling task.')
            raise
        except Exception as e:
            log.error(f'Exception: {e}')
            raise
        finally:
            self.recording_task = None

    async def _read_datapoints(self, duration):
        start_time = pendulum.DateTime.utcnow()
        datapoints = []

        log.info(f'Reading datapoints for {duration.total_minutes()} minutes.')

        arduino = serial.Serial(
            port=self.sensor.serial_port,
            baudrate=self.sensor.baud_rate_bps,
            timeout=self.sensor.serial_timeout_seconds)

        with arduino:
            while pendulum.DateTime.utcnow() - start_time <= duration:
                try:
                    # This sleep is important because it allows the
                    # cancel command to get through in a timely manner.
                    await asyncio.sleep(1)
                    raw_data = arduino.readline()
                    datapoint = TempidityDataPoint.from_raw_data(raw_data)
                    log.debug(f'Received datapoint: {datapoint}')
                    datapoints.append(datapoint)
                except TempidityError as e:
                    log.debug(f'Error while decoding datapoint: {e}')

        log.info(f'Read {len(datapoints)} datapoints.')
        return datapoints

    async def _process_datapoints(self, datapoints):
        humidities = [x.humidity_percent for x in datapoints]
        temperatures = [x.temperature_celsius for x in datapoints]

        humidity_percent = statistics.median(humidities)
        temperature_celsius = statistics.median(temperatures)

        return TempidityDataPoint(humidity_percent, temperature_celsius)
        
    async def _cleanup_task(self):
        if self.recording_task is None:
            return

        try:
            if self.recording_task.done():
                self.recording_task.result()
            else:
                self.recording_task.cancel()
                await self.recording_task               
        except asyncio.CancelledError:
            log.info('Task was cancelled.')
        except Exception as e:
            log.error(f'Exception was thrown during task: {e}')
        finally:
            self.recording_task = None

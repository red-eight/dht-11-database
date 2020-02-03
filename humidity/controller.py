import asyncio
import logging

import pendulum
import re
import serial

from humidity.definitions import Sensor, Database, TempidityError, TempidityDataPoint

log = logging.getLogger(__name__)


class TempidityController:
    def __init__(self, sensor, database):
        if not isinstance(sensor, Sensor):
            raise TempidityError('sensor must be of type Sensor.')

        if not isinstance(database, Database):
            raise TempidityError('database must be of type Database.')

        self.sensor = sensor
        self.database = database
        self.is_humidifier_on = False
        self.recording_task = None

    async def start_recording(self):
        if self.recording_task is not None:
            raise TempidityError('Already recording.')

        self.recording_task = asyncio.create_task(self._start_recording_task())

    async def stop_recording(self):
        await self._cleanup_task()

    async def set_humidifier_status(self, is_humidifier_on):
        await self.stop_recording
        self.is_humidifier_on = is_humidifier_on
        await self.start_recording

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
                await self._write_datapoints(datapoints)
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

    async def _write_datapoints(self, datapoints):
        pass
        
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

import attr
import pendulum
import re


class TempidityError(Exception):
    pass


@attr.s(frozen=True, slots=True)
class Sensor:
    serial_port = attr.ib()
    baud_rate_bps = attr.ib()
    serial_timeout_seconds = attr.ib()


@attr.s(frozen=True, slots=True)
class Database:
    name = attr.ib()


@attr.s(slots=True)
class TempidityDataPoint:
    humidity_percent = attr.ib()
    temperature_celsius = attr.ib()

    @classmethod
    def from_raw_data(cls, raw_data):
        """Extract data from Arduino.

        Arduino messages look like this:
        b'Humidity (%): 49.0, Temperature (C): 23.5, Checksum: 77, Valid checksum: 1'
        """
        try:
            data = raw_data.decode('utf-8').rstrip()
        except UnicodeDecodeError as e:
            raise TempidityError(f'Could not decode raw data: {raw_data}, exception: {e}') from e
        
        pattern = r'[^:]*: (.*), [^:]*: (.*), [^:]*: (.*), [^:]*: (.*)'

        match = re.fullmatch(pattern, data)

        if match is None:
            raise TempidityError(f'Could not parse: {data}')

        humidity_percent = float(match.group(1))
        temperature_celsius = float(match.group(2))

        checksum = int(match.group(3))

        valid_checksum = match.group(4) == '1'
        if not valid_checksum:
            raise TempidityError(f'Checksum failed for: {data}')

        return cls(humidity_percent, temperature_celsius)

# dht-11-database
Reads humidity and temperature from a dht-11 sensor and saves it in an sqlite database.
This application is a web server with a REST interface.
The REST endpoints allow you to:

- Start reading and saving points into a database
- Stop reading and saving points into a database
- Plot points from a start datetime to a stop datetime
- View the n most recent points stored in the database

The original purpose of this project was to see if the humidifier I bought actually made my living room more humid.

## Arduino Instructions

1. Hook up a dht-11 sensor to an Arduino.
2. Start a new Arduino project within the Arduino IDE.
3. Add my run_dht11.ino file to the project.
4. Import [my version](https://github.com/red-eight/dht11) of the dht11.h library.
   - Sketch -> Include Library -> Add .ZIP Library OR (even easier)
   - Copy my dht11 libary into your Arduino/libraries folder
5. Upload the run_dht11.ino sketch to your Arduino.

## Python Dependencies

```
pip install aiohttp
pip install attrs
pip install matplotlib
pip install pendulum
pip install pyserial
pip install toml
```

## Python Instructions
1. Edit the config.toml file to your liking.
   Most importantly, make sure the `serial_port` argument points to your Arduino device.
2. Run the application with `python -m main`
3. In a different terminal, use your favorite web client (curl, httpie) to call the REST endpoints of the application.

## REST Endpoint Examples Using [httpie](https://httpie.org/)

```
# Start recording
# If you own a humidifier and you want to track whether it's on or off, you can set the `is_humidifier_on` variable to `true` or `false`.
# If you don't care, just leave the value as `false`.
http post localhost:8080/v1/start-recording is_humidifier_on:=false

# Stop recording
http post localhost:8080/v1/stop-recording

# Plot data between a start datetime and stop datetime
# The format for start and stop can be anything that pendulum.parse accepts.
# This example shows start and stop as dates, but a full datetime may be used for both fields.
http post localhost:8080/v1/plot-data start=2020-02-03 stop=2020-04-01

# Get recent datapoints in a JSON response
# You can set n to however many datapoints you want, but you may get less than n.
http localhost:8080/v1/recent-data n==5
```

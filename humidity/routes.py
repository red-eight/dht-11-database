from aiohttp import web

from humidity.controller import TempidityController
from humidity.definitions import Sensor, Database
from humidity import views


def get_application(config):
    sensor = Sensor(**config['sensor'])
    database = Database(**config['database'])

    controller = TempidityController(sensor, database)

    app = web.Application()
    app['controller'] = controller

    app.router.add_post('/start-recording', views.start_recording)
    app.router.add_post('/stop-recording', views.stop_recording)

    return app

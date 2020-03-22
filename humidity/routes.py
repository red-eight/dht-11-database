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

    app.router.add_get('/v1/recent-data', views.get_recent_data)
    app.router.add_post('/v1/start-recording', views.start_recording)
    app.router.add_post('/v1/stop-recording', views.stop_recording)
    app.router.add_post('/v1/plot-data', views.plot_data)

    return app

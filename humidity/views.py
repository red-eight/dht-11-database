import logging

from aiohttp import web
import pendulum

log = logging.getLogger(__name__)


async def start_recording(request):
    log.info('Received request to start recording.')

    data = await request.json()
    is_humidifier_on = data['is_humidifier_on']

    controller = request.app['controller']
    await controller.start_recording(is_humidifier_on)

    return web.json_response(data={})


async def stop_recording(request):
    log.info('Received request to stop recording.')

    controller = request.app['controller']
    await controller.stop_recording()
    
    return web.json_response(data={})


async def plot_data(request):
    log.info('Received request to plot humidity.')

    data = await request.json()
    start_datetime = pendulum.parse(data['start'])
    stop_datetime = pendulum.parse(data['stop'])

    controller = request.app['controller']
    await controller.plot_data(start_datetime, stop_datetime)

    return web.json_response(data={})


async def get_recent_data(request):
    log.info('Received request for recent data.')

    num_points = request.rel_url.query.get('n', 1)

    controller = request.app['controller']
    points = await controller.get_recent_data(num_points)

    return web.json_response(data=points)

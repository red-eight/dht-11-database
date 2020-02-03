import logging

from aiohttp import web

log = logging.getLogger(__name__)


async def start_recording(request):
    log.info('Received request to start recording.')

    controller = request.app['controller']
    await controller.start_recording()

    return web.json_response(data={})


async def stop_recording(request):
    log.info('Received request to stop recording.')

    controller = request.app['controller']
    await controller.stop_recording()
    
    return web.json_response(data={})


async def set_humidifier_status(request):
    log.info('Received request to set humidifier status.')

    controller = request.app['controller']
    data = await request.json()

    log.info(f'Data received for setting the humidifier status: {data}')

    is_humidifier_on = data['is_humidifier_on']
    await controller.set_humidifier_status(is_humidifier_on)

    return web.json_response(data={})
    
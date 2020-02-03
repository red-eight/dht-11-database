import logging

from aiohttp import web

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

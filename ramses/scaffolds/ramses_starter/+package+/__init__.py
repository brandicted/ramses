from pyramid.config import Configurator


def main(global_config, **settings):
    # Update settings with global_config to allow overriding
    # config file params with console params
    settings.update(global_config)
    config = Configurator(settings=settings)
    config.include('ramses')
    return config.make_wsgi_app()

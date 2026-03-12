from django.apps import AppConfig


class FitnessConfig(AppConfig):
    name = 'fitness'

    def ready(self):
        import fitness.signals

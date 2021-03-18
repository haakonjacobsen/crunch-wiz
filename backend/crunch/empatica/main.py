from .api import MockApi
from .handler import DataHandler
from .measurements import compute_engagement, compute_arousal, \
    compute_emotional_regulation, compute_entertainment, compute_stress


def start_empatica(api=MockApi):
    """
    start the empatica process control flow.
    TODO change default api argument to realAPI, and use MockApi when integration testing only
    """
    # Instantiate the api
    api = api()

    # Instantiate the arousal data handler and subscribe to the api
    arousal_handler = DataHandler(measurement_func=compute_arousal,
                                  measurement_path="arousal.csv",
                                  window_length=121, window_step=40)
    api.add_subscriber(arousal_handler, "EDA")

    # Instantiate the engagement data handler and subscribe to the api
    engagement_handler = DataHandler(measurement_func=compute_engagement,
                                     measurement_path="engagement.csv",
                                     window_length=121, window_step=40)
    api.add_subscriber(engagement_handler, "EDA")

    # Instantiate the emotional regulation data handler and subscribe to the api
    emreg_handler = DataHandler(measurement_func=compute_emotional_regulation,
                                measurement_path="emotional_regulation.csv",
                                window_length=12, window_step=12)
    api.add_subscriber(emreg_handler, "IBI")

    # Instantiate the entertainment data handler and subscribe to the api
    entertainment_handler = DataHandler(measurement_func=compute_entertainment,
                                        measurement_path="entertainment.csv",
                                        window_length=20, window_step=20)
    api.add_subscriber(entertainment_handler, "HR")

    # Instantiate the stress data handler and subscribe to the api
    stress_handler = DataHandler(measurement_func=compute_stress,
                                 measurement_path="stress.csv",
                                 window_length=10, window_step=10)
    api.add_subscriber(stress_handler, "TEMP")

    # start up the api
    api.connect()
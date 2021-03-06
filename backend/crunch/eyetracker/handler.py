from collections import deque

from crunch import util

from .measurements.information_processing_index import compute_ipi_thresholds


class DataHandler:
    """
    Class that subscribes to a specific raw data stream,
    handles storing the data,
    calculating measurements from the data,
    and calculate baseline and writes to csv.

    The class has two phases:
        1. the baseline phase where measurement results are stored
        and we eventually take the average of these values as baseline.
        2. the csv_phase where the ratio of measurement results and the
        baseline is written to csv.
    """

    def __init__(self,
                 measurement_func=None,
                 measurement_path=None,
                 subscribed_to=None,
                 window_length=None,
                 window_step=None,
                 baseline_length=None,
                 calculate_baseline=True):
        """
        :param measurement_func: the function we call to compute measurements from the raw data
        :type measurement_func: (list) -> float
        :param measurement_path: path to the output csv file
        :type measurement_path: str
        :param window_length: length of the window, i.e number of data points for the function
        :type window_length: int
        :param window_step: how many steps for a new window, i.e for 6 steps,
        a new measurement is computed every 6 data points
        :type window_step: int
        :param baseline_length: How many measurement values used to calculate baseline
        :type baseline_length: int
        :param calculate_baseline: Should baseline be calculated? Skip if False
        :type calculate_baseline: bool
        """
        assert window_length and window_step and measurement_func and subscribed_to, \
            "Need to supply the required parameters"

        self.data_queues = {key: deque(maxlen=window_length) for key in subscribed_to}
        self.data_counter = 0
        self.window_step = window_step
        self.window_length = window_length
        self.measurement_func = measurement_func
        self.measurement_path = measurement_path
        self.subscribed_to = subscribed_to

        self.phase_func = self.baseline_phase if calculate_baseline else self.csv_phase
        self.calculate_baseline = calculate_baseline
        self.baseline = 0
        self.list_of_baseline_values = []
        self.baseline_length = baseline_length

    def add_data_point(self, datapoint):
        """
        This is the only function in Datahandler that is called from the API. It appends the
        values in datapoint and checks if we have enough data points to calculate to call
         phase_func. In the beginning, phase_func is set to baseline_phase.

        :param datapoint: A fixation data point
        :type datapoint: dictionary of floats
        """
        self.data_counter += 1
        for key, value in datapoint.items():
            self.data_queues[key].append(value)
        if (self.data_counter % self.window_step == 0
                and all(len(queue) == self.window_length for _, queue in self.data_queues.items())):
            self.phase_func()

    def baseline_phase(self):
        """
        Appends a value to be used for calculating the baseline, then checks if we have enough data points
        to transition to next phase.
        """
        measurement = self.measurement_func(**{key: list(queue) for key, queue in self.data_queues.items()})
        self.list_of_baseline_values.append(measurement)
        if len(self.list_of_baseline_values) >= self.baseline_length:
            self.transition_to_csv_phase()

    def transition_to_csv_phase(self):
        """Compute baseline and set phase_func to csv_phase"""
        self.baseline = float(sum(self.list_of_baseline_values) / len(self.list_of_baseline_values))
        self.phase_func = self.csv_phase
        assert 0 <= self.baseline < float('inf') and type(self.baseline) == float

    def csv_phase(self):
        """Calculate measurement and write the ratio relative to baseline to csv file"""
        measurement = self.measurement_func(**{key: list(queue) for key, queue in self.data_queues.items()})
        if self.calculate_baseline:
            measurement = round(measurement / self.baseline, 6)
        util.write_csv(self.measurement_path, [measurement])


class ThresholdDataHandler(DataHandler):
    """
    Computing the information processing index requires 3 phases, as threshold values are needed to
    compute the first measurement value. This makes a specialized handler necessary.
    IpiHandler inherits from DataHandler as the baseline_phase and csv_phase are very similar
    """

    def __init__(self,
                 measurement_func,
                 measurement_path=None,
                 subscribed_to=None,
                 window_length=None,
                 window_step=None,
                 baseline_length=None,
                 threshold_length=None
                 ):
        """
        :param measurement_func: the function we call to compute measurements from the raw data
        :type measurement_func: (list) -> float
        :param measurement_path: path to the output csv file
        :type measurement_path: str
        """
        DataHandler.__init__(self,
                             measurement_func=measurement_func,
                             measurement_path=measurement_path,
                             subscribed_to=subscribed_to,
                             window_length=window_length,
                             window_step=window_step,
                             baseline_length=baseline_length,
                             calculate_baseline=True)
        self.phase_func = self.threshold_phase

        self.short_threshold = None
        self.long_threshold = None

        #  threshold phase
        self.thresholds = {key: [] for key in subscribed_to}
        self.threshold_length = threshold_length

    def add_data_point(self, datapoint):
        """
        Receive a new data point and call phase func (threshold_phase in the beginning)

        :param datapoint: A fixation data point
        :type datapoint: dictionary of floats
         """

        self.phase_func(datapoint)

    def threshold_phase(self, datapoint):
        """
        Store data point and check if we have enough data to transition to baseline

        :param datapoint: A fixation data point
        :type datapoint: dictionary of floats
        """
        for key, value in datapoint.items():
            self.thresholds[key].append(value)

        # check if we have enough values to transition to baseline phase
        if len(self.thresholds["initTime"]) >= self.threshold_length:
            self.transition_to_baseline_phase()

    def transition_to_baseline_phase(self):
        """Compute and set threshold values, set phase_func to baseline_phase"""
        self.short_threshold, self.long_threshold = compute_ipi_thresholds(**self.thresholds)
        assert type(float(self.short_threshold)) == float
        assert type(float(self.long_threshold)) == float
        assert self.short_threshold < self.long_threshold

        # transition to baseline phase
        self.phase_func = self._baseline_phase

    def _baseline_phase(self, datapoint):
        """
        Appends values to data queues, then checks if we have enough data points calculate a measurement.
        If yes, it also checks if we have calculated enough measurement values to transition to csv phase.

        :param datapoint: A fixation data point
        :type datapoint: dictionary of floats
        """
        for key, value in datapoint.items():
            self.data_queues[key].append(value)
        self.data_counter += 1
        if self.data_counter % self.window_step == 0 and len(self.data_queues["initTime"]) == self.window_length:
            argument_dictionary = {key: list(queue) for key, queue in self.data_queues.items()}
            argument_dictionary["short_threshold"] = self.short_threshold
            argument_dictionary["long_threshold"] = self.long_threshold
            measurement = self.measurement_func(**argument_dictionary)
            self.list_of_baseline_values.append(measurement)
            if len(self.list_of_baseline_values) >= self.baseline_length:
                self.transition_to_csv_phase()

    def transition_to_csv_phase(self):
        """Compute baseline and set phase_func to _csv_phase"""
        self.baseline = float(sum(self.list_of_baseline_values) / len(self.list_of_baseline_values))
        self.phase_func = self._csv_phase
        assert 0 <= self.baseline < float('inf') and type(self.baseline) == float

    def _csv_phase(self, datapoint):
        """
        Appends values to data queues, then checks if we have enough data points calculate a measurement.
        If yes, it writes the ratio of the measurement and the baseline to a csv-file.

        :param datapoint: A fixation data point
        :type datapoint: dictionary of floats
        """
        for key, value in datapoint.items():
            self.data_queues[key].append(value)
        self.data_counter += 1
        if self.data_counter % self.window_step == 0 and len(self.data_queues["initTime"]) == self.window_length:
            argument_dictionary = {key: list(queue) for key, queue in self.data_queues.items()}
            argument_dictionary["short_threshold"] = self.short_threshold
            argument_dictionary["long_threshold"] = self.long_threshold
            measurement = self.measurement_func(**argument_dictionary)
            if self.calculate_baseline:
                measurement = round(measurement / self.baseline, 6)
            util.write_csv(self.measurement_path, [measurement])

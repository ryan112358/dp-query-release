"""
Base class for iterative algorithms
"""
import os
import time
import torch
import pickle
import numpy as np
from abc import ABC, abstractmethod

from dp_query_release.utils.utils_general import get_errors

class IterativeAlgorithm(ABC):
    """
    Arguments:
        qm (QueryManager): query manager for defining queries and calculating answers
        T (int): Number of rounds to run algorithm
        eps0 (float): Privacy budget per round (zCDP)
        alpha (float, optional): Changes the allocation of the per-round privacy budget
            Selection mechanism uses ``alpha * eps0`` and Measurement mechanism uses ``(1-alpha) * eps0``.
            If given, it must be between 0 and 1.
        default_dir (string, optional): Path for saving the class state. If None is passed, a random directory is generated.
        verbose (boolean, optional): Flag for whether to print progress while fitting to true answers
        seed (int, optional): seed for reproducibility

    Attributes:
        errors: TODO: perhaps we should write a separate class for logging/keeping track of errors?
    """
    def __init__(self, qm, T, eps0,
                 alpha=0.5, default_dir=None, verbose=False, seed=None):
        assert 0 <= alpha <= 1, "alpha must be between 0 and 1"

        self.qm = qm
        self.T = T
        self.eps0 = eps0
        self.alpha = alpha
        self.default_dir = default_dir
        self.verbose = verbose
        self.seed = seed

        self.sampled_max_errors = []
        self.true_max_errors = []
        self.true_mean_errors = []
        self.true_mean_squared_errors = []

        self.past_workload_idxs = [] # only used for sensitivity trick implementations
        self.past_query_idxs = []
        self.past_measurements = []

        # validate QueryManager is correct
        assert isinstance(self.qm, self._valid_qm()), \
            "QueryManager must be chosen from the following classes: {}".format(
                ", ".join([x.__name__ for x in self._valid_qm()]))

        # create directory for saving algo files
        if self.default_dir is None:
            self.default_dir = "./save/{}/{}".format(self.__class__.__name__, hash(time.time()))
        if not os.path.exists(self.default_dir):
            os.makedirs(self.default_dir)
        print("Saving algorithm files to: {}".format(self.default_dir))

        # set seed for reproducibility
        if self.seed is not None:
            self._set_seed()

    def _set_seed(self):
        np.random.seed(self.seed)

    """
    Save current state
    Input:
        path (string): file path to save to
    """
    def save(self, filename, directory=None):
        if directory is None:
            directory = self.default_dir
        path = os.path.join(directory, filename)
        with open(path, 'wb') as handle:
            pickle.dump(self.__dict__, handle)

    """
    Load state
    Input:
        path (string): file path to load from
    """
    def load(self, filename, directory=None):
        if directory is None:
            directory = self.default_dir
        path = os.path.join(directory, filename)
        with open(path, 'rb') as handle:
            tmp_dict = pickle.load(handle)
        self.__dict__.update(tmp_dict)

    def record_errors(self, true_answers, fake_answers):
        errors_dict = get_errors(true_answers, fake_answers)
        self.true_max_errors.append(errors_dict['max'])
        self.true_mean_errors.append(errors_dict['mean'])
        self.true_mean_squared_errors.append(errors_dict['mean_squared'])

    """
    Returns tuple of valid QueryManager classes
    """
    @abstractmethod
    def _valid_qm(self):
        pass

    """
    Algorithm fits to a list of answers.
    Input:
        true_answers (np.array): true answers the algorithm is fitting to
    """
    @abstractmethod
    def fit(self, true_answers):
        pass

    """
    Uses differentially private mechanism to sample query
    Input:
        scores (np.array): score function applied to each query
    """
    @abstractmethod
    def _sample(self, scores):
        pass

    """
    Uses differentially private mechanism to get a noisy measure of query answers
    Input:
        answers (np.array): true answers that the noisy measurements are approximating 
    """
    @abstractmethod
    def _measure(self, answers):
        pass

    """
    Returns synthetic data in some form
    """
    @abstractmethod
    def get_syndata(self):
        pass

class IterativeAlgorithmTorch(IterativeAlgorithm):
    def __init__(self, qm, T, eps0,
                 alpha=0.5, default_dir=None, verbose=False, seed=None):
        super().__init__(qm, T, eps0,
                         alpha=alpha, default_dir=default_dir, verbose=verbose, seed=seed)

        # convert these lists into tensors for Pytorch code
        self.past_workload_idxs = torch.tensor([]).long() # only used for sensitivity trick implementations
        self.past_query_idxs = torch.tensor([]).long()
        self.past_measurements = torch.tensor([])

    def _set_seed(self):
        super()._set_seed()
        torch.manual_seed(self.seed)

import heapq

import attr
import numpy as np
import numpy.random as npr


@attr.s(slots=True)
class PredictedRuntime:
    simulations = attr.ib()
    mean = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.mean = np.mean(self.simulations)

    def percentile(self, q):
        return np.percentile(self.simulations, q)


def predict_timing(historical_times, current_queue, remaining_tasks, seed=0):
    parallelism = len(current_queue)
    current_queue = np.array(current_queue)
    current_predictions = npr.exponential(current_queue)
    task_times = np.concatenate((current_predictions, np.array(historical_times)))

    npr.seed(seed)

    def simulate():
        runtimes = npr.choice(task_times, size=remaining_tasks)
        runtimes = np.concatenate((current_predictions, npr.exponential(runtimes)))

        schedules = []
        for t in runtimes[:parallelism]:
            heapq.heappush(schedules, t)

        clock = 0.0

        for t in runtimes[parallelism:]:
            clock = heapq.heappop(schedules)
            heapq.heappush(schedules, t + clock)

        return max(schedules)

    simulations = np.array([simulate() for _ in range(200)])

    return PredictedRuntime(simulations)

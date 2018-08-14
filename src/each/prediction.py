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


def predict_timing(historical_times, parallelism, remaining_tasks, seed=0):
    task_times = np.array(historical_times)
    npr.seed(seed)

    def simulate():
        runtimes = npr.choice(task_times, size=remaining_tasks)
        runtimes = npr.exponential(1 / runtimes)

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

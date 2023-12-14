import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random
from policy import Policy

class SRTFPolicy(Policy):
    def __init__(self, seed=None):
        self._name = 'SRTF'
        self._allocation = {}
        self._scale_factors = {}
        self.remaining_times = {}
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def update_remaining_times(self, throughputs):
        # Update remaining_times with the remaining time of each job
        for job_id, job_data in throughputs.items():
            self.remaining_times[job_id] = job_data.remaining_time

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)
        queue = []

        # Update scale_factors
        for job_id in scale_factors:
            self._scale_factors[job_id] = scale_factors[job_id]

        # Queue jobs that are not yet allocated
        for job_id in throughputs:
            if job_id not in self._allocation:
                queue.append(job_id)

        # Sort jobs by remaining time
        queue.sort(key=lambda job_id: self.remaining_times.get(job_id, float('inf')))

        # Allocate resources based on SRTF
        while queue and any(available_workers.values()):
            job_id_to_schedule = queue.pop(0)
            scale_factor = self._scale_factors[job_id_to_schedule]
            for worker_type, available in available_workers.items():
                if available >= scale_factor:
                    self._allocation[job_id_to_schedule] = worker_type
                    available_workers[worker_type] -= scale_factor
                    break

        # Construct final allocation
        final_allocation = {job_id: {worker_type: 0.0 for worker_type in cluster_spec} for job_id in throughputs}
        for job_id, worker_type in self._allocation.items():
            final_allocation[job_id][worker_type] = 1.0

        return final_allocation

# Additional SRTF policy classes with performance or packing enhancements can be defined similarly.

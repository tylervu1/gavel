import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random
import job_id_pair
from policy import Policy, PolicyWithPacking

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
            # Adjust the following line based on the actual structure
            self.remaining_times[job_id] = job_data['remaining_time']  # Replace 'remaining_time' with the correct key

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

class SRTFPolicyWithPacking(PolicyWithPacking):
    def __init__(self, seed=None, packing_threshold=1.5):
        super().__init__()
        self._name = 'SRTF_Packing'
        self._allocation = {}
        self._scale_factors = {}
        self.remaining_times = {}
        self._packing_threshold = packing_threshold
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def update_remaining_times(self, throughputs):
        for job_id, job_data in throughputs.items():
            self.remaining_times[job_id] = job_data.remaining_time

    def _pack(self, queue, throughputs, scale_factors, cluster_spec):
        packed_jobs = set()
        while queue:
            job_id_to_schedule = queue.pop(0)

            if job_id_to_schedule in packed_jobs:
                continue  # Skip if job is already packed

            max_combined_throughput = 0
            best_pair = None

            for other_job_id in queue:
                if other_job_id in packed_jobs:
                    continue  # Skip if other job is already packed

                # Calculate combined throughput if these two jobs are packed
                for worker_type in cluster_spec:
                    combined_throughput = (throughputs[job_id_to_schedule][worker_type] +
                                           throughputs[other_job_id][worker_type])
                    if combined_throughput > max_combined_throughput:
                        max_combined_throughput = combined_throughput
                        best_pair = (job_id_to_schedule, other_job_id)

            if best_pair and max_combined_throughput > self._packing_threshold:
                # Perform packing
                job1, job2 = best_pair
                packed_job_id = job_id_pair.JobIdPair(job1, job2)
                self._allocation[packed_job_id] = max(cluster_spec, key=cluster_spec.get)  # Assign to the worker type with the most availability
                packed_jobs.update([job1, job2])

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)
        queue = sorted(self.remaining_times, key=self.remaining_times.get)

        # Allocate resources based on SRTF
        for job_id in queue:
            if job_id in self._allocation or job_id in packed_jobs:
                continue  # Skip already allocated or packed jobs

            scale_factor = scale_factors[job_id]
            for worker_type, available in available_workers.items():
                if available >= scale_factor:
                    self._allocation[job_id] = worker_type
                    available_workers[worker_type] -= scale_factor
                    break

        # Apply packing logic
        self._pack(queue, throughputs, scale_factors, available_workers)

        # Construct final allocation
        final_allocation = {job_id: {worker_type: 0.0 for worker_type in cluster_spec} for job_id in throughputs}
        for job_id, worker_type in self._allocation.items():
            final_allocation[job_id][worker_type] = 1.0

        return final_allocation
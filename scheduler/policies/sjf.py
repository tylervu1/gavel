import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random

import job_id_pair
from policy import Policy, PolicyWithPacking

class SJFPolicy(Policy):

    def __init__(self, mode='base', seed=None, packing_threshold=1.5):
        super().__init__()
        self._name = 'SJF'
        self._allocation = {}
        self._scale_factors = {}
        self._burst_times = {}  # Tracks burst times for jobs
        # self._rng = random.Random(seed) if seed is not None else random.Random()
        if mode == 'base':
            self._rng = random.Random()
            if seed is not None:
                self._rng.seed(seed)
        elif mode == 'packing':
            self._packing_threshold = packing_threshold

    def update_burst_times(self, job_updates):
        # This method should be called to update the burst times of jobs
        for job_id, burst_time in job_updates.items():
            self._burst_times[job_id] = burst_time

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)

        # Sort jobs by burst time. The shortest burst time job is first
        sorted_jobs = sorted(self._burst_times, key=self._burst_times.get)

        for job_id in sorted_jobs:
            if job_id in self._allocation:
                continue  # Skip already allocated jobs

            scale_factor = scale_factors[job_id]
            for worker_type in available_workers:
                if available_workers[worker_type] >= scale_factor:
                    # Allocate this worker to the job
                    self._allocation[job_id] = worker_type
                    available_workers[worker_type] -= scale_factor
                    break  # Break as the job is allocated

        # Construct the final allocation
        final_allocation = {}
        for job_id in throughputs:
            final_allocation[job_id] = {worker_type: 0.0 for worker_type in cluster_spec}
        for job_id, worker_type in self._allocation.items():
            final_allocation[job_id][worker_type] = 1.0

        return final_allocation

class SJFPolicyWithPerf(Policy):
    def __init__(self, packing=False):
        self._name = 'SJF_Perf'
        self._packing = packing
        self._policy = SJFPolicy(mode='perf')

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        return self._policy.get_allocation(throughputs, scale_factors,
                                           cluster_spec)

class SJFPolicyWithPacking(PolicyWithPacking):
    def __init__(self, packing_threshold=1.5):
        self._name = 'SJF_Packing'
        self._policy = SJFPolicy(mode='packing',
                                  packing_threshold=packing_threshold)

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        return self._policy.get_allocation(throughputs, scale_factors,
                                           cluster_spec)
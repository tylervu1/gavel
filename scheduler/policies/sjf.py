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

class SJFPolicyWithPacking(PolicyWithPacking):

    def __init__(self, seed=None, packing_threshold=1.5):
        self._name = 'SJF_Packing'
        self._packing_threshold = packing_threshold
        self._burst_times = {}
        self._allocation = {}
        self._scale_factors = {}
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def update_burst_times(self, job_updates):
        for job_id, burst_time in job_updates.items():
            self._burst_times[job_id] = burst_time

    def _pack(self, sorted_jobs, throughputs, scale_factors, cluster_spec):
        packed_jobs = set()
        for i, job_id in enumerate(sorted_jobs):
            if job_id in packed_jobs or job_id in self._allocation:
                continue  # Skip if already packed or allocated

            best_packed_throughput = 0
            best_pair = None
            for j, other_job_id in enumerate(sorted_jobs):
                if i == j or other_job_id in packed_jobs or other_job_id in self._allocation:
                    continue  # Skip same job, already packed, or allocated jobs

                # Check if the combination is beneficial
                combined_burst_time = self._burst_times[job_id] + self._burst_times[other_job_id]
                if combined_burst_time > self._packing_threshold:
                    continue  # Skip if combined burst time is too high

                # Calculate combined throughput
                for worker_type in cluster_spec:
                    combined_throughput = throughputs[job_id][worker_type] + throughputs[other_job_id][worker_type]
                    if combined_throughput > best_packed_throughput and combined_throughput > 0:
                        best_packed_throughput = combined_throughput
                        best_pair = (job_id, other_job_id)

            # Allocate resources to the best pair found
            if best_pair:
                job_id, other_job_id = best_pair
                for worker_type in cluster_spec:
                    if cluster_spec[worker_type] >= scale_factors[job_id] + scale_factors[other_job_id]:
                        # Update allocation for packed jobs
                        self._allocation[job_id_pair.JobIdPair(job_id, other_job_id)] = worker_type
                        packed_jobs.update([job_id, other_job_id])
                        cluster_spec[worker_type] -= scale_factors[job_id] + scale_factors[other_job_id]
                        break  # Break as resources are allocated


    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)
        sorted_jobs = sorted(self._burst_times, key=self._burst_times.get)

        # Step 1: Allocate resources to each job based on SJF
        for job_id in sorted_jobs:
            if job_id in self._allocation:
                continue  # Skip if already allocated

            scale_factor = scale_factors[job_id]
            for worker_type, available in available_workers.items():
                if available >= scale_factor:
                    self._allocation[job_id] = worker_type
                    available_workers[worker_type] -= scale_factor
                    break

        # Step 2: Apply packing logic
        self._pack(sorted_jobs, throughputs, scale_factors, available_workers)

        # Step 3: Construct final allocation
        final_allocation = {}
        for job_id in throughputs:
            final_allocation[job_id] = {worker_type: 0.0 for worker_type in cluster_spec}
            if job_id in self._allocation:
                allocated_worker = self._allocation[job_id]
                final_allocation[job_id][allocated_worker] = 1.0
            elif any(isinstance(key, job_id_pair.JobIdPair) and job_id in key for key in self._allocation):
                # For packed jobs
                for key, allocated_worker in self._allocation.items():
                    if isinstance(key, job_id_pair.JobIdPair) and job_id in key:
                        final_allocation[job_id][allocated_worker] = 1.0

        return final_allocation


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
        # Copy of the cluster specification to track available resources
        available_workers = copy.deepcopy(cluster_spec)

        # Initialize final_allocation with all job IDs in throughputs
        final_allocation = {job_id: {worker_type: 0.0 for worker_type in cluster_spec} for job_id in throughputs}

        # Update scale_factors based on current data
        for job_id in scale_factors:
            self._scale_factors[job_id] = scale_factors[job_id]

        # Prepare a queue of jobs not yet allocated
        queue = [job_id for job_id in throughputs if job_id not in self._allocation]

        # Sort jobs by their remaining time
        queue.sort(key=lambda job_id: self.remaining_times.get(job_id, float('inf')))

        # Allocate resources based on SRTF
        while queue and any(available_workers.values()):
            job_id_to_schedule = queue.pop(0)
            scale_factor = self._scale_factors[job_id_to_schedule]

            # Find an available worker for the job with the shortest remaining time
            for worker_type, available in available_workers.items():
                if available >= scale_factor:
                    # Allocate this worker to the job
                    self._allocation[job_id_to_schedule] = worker_type
                    available_workers[worker_type] -= scale_factor
                    break

        # Set allocation values in final_allocation
        for job_id, worker_type in self._allocation.items():
            if job_id in final_allocation and worker_type in final_allocation[job_id]:
                final_allocation[job_id][worker_type] = 1.0

        return final_allocation


class SRTFPolicyWithPacking(PolicyWithPacking):
    def __init__(self, seed=None, packing_threshold=1.5):
        super().__init__()
        self._name = 'SRTF_Packing'
        self._packing_threshold = packing_threshold
        self._remaining_times = {}
        self._allocation = {}
        self._scale_factors = {}
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def update_remaining_times(self, throughputs):
        # Update remaining times based on job updates
        for job_id, job_data in throughputs.items():
            self._remaining_times[job_id] = job_data['remaining_time']  # Adjust key based on actual data structure

    def _pack(self, sorted_jobs, throughputs, scale_factors, cluster_spec):
        packed_jobs = set()
        for job_id in sorted_jobs:
            if job_id in packed_jobs or job_id in self._allocation:
                continue

            best_packed_throughput = 0
            best_pair = None
            for other_job_id in sorted_jobs:
                if other_job_id == job_id or other_job_id in packed_jobs or other_job_id in self._allocation:
                    continue

                combined_throughput, worker_type_for_packing = self._calculate_combined_throughput(job_id, other_job_id, throughputs, cluster_spec)
                if combined_throughput > best_packed_throughput and combined_throughput / (scale_factors[job_id] + scale_factors[other_job_id]) > self._packing_threshold:
                    best_packed_throughput = combined_throughput
                    best_pair = (job_id, other_job_id, worker_type_for_packing)

            if best_pair:
                job1, job2, worker_type = best_pair
                packed_job_id = job_id_pair.JobIdPair(job1, job2)
                self._allocation[packed_job_id] = worker_type
                packed_jobs.update([job1, job2])

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)
        sorted_jobs = sorted(self._remaining_times, key=self._remaining_times.get)

        # Allocate resources based on SRTF logic
        for job_id in sorted_jobs:
            if job_id in packed_jobs or job_id in self._allocation:
                continue

            self._allocate_job(job_id, scale_factors, available_workers)

        # Apply packing logic
        self._pack(sorted_jobs, throughputs, scale_factors, available_workers)

        # Construct final allocation
        return self._construct_final_allocation(throughputs, cluster_spec)

    def _construct_final_allocation(self, throughputs, cluster_spec):
        final_allocation = {}
        for job_id in throughputs:
            final_allocation[job_id] = {worker_type: 0.0 for worker_type in cluster_spec}
            if job_id in self._allocation:
                # Allocate for individual jobs
                worker_type = self._allocation[job_id]
                final_allocation[job_id][worker_type] = 1.0
            elif any(isinstance(key, job_id_pair.JobIdPair) and job_id in key for key in self._allocation):
                # Allocate for packed jobs
                for key, allocated_worker in self._allocation.items():
                    if isinstance(key, job_id_pair.JobIdPair) and job_id in key:
                        final_allocation[job_id][allocated_worker] = 1.0

        return final_allocation

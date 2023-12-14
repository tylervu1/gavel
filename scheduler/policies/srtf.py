import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random
import job_id_pair
from policy import Policy, PolicyWithPacking

class SRTFPolicy(Policy):
    def __init__(self, seed=None):
        super().__init__()
        self._name = 'SRTF'
        self._allocation = {}
        self._scale_factors = {}
        self._remaining_times = {}
        self.running_job = None
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def update_remaining_times(self, job_updates):
        for job_id, remaining_time in job_updates.items():
            self._remaining_times[job_id] = remaining_time

    def on_job_arrival(self, job_id, current_time):
        # Update the remaining times of all jobs, including the newly arrived job
        self.update_remaining_times()  # Update based on current_time

        # Make a scheduling decision
        self.make_scheduling_decision(current_time)

    def on_job_completion(self, job_id, current_time):
        # Mark the job as completed
        if self.running_job == job_id:
            self.running_job = None

        # Update the remaining times of all jobs
        self.update_remaining_times()  # Update based on current_time

        # Make a scheduling decision
        self.make_scheduling_decision(current_time)

    def make_scheduling_decision(self, current_time):
        # Choose the next job to run
        next_job = min(self._remaining_times, key=self._remaining_times.get, default=None)

        if next_job and (self.running_job is None or self._remaining_times[next_job] < self._remaining_times[self.running_job]):
            self.preempt_job(current_time)
            self.schedule_next_job(next_job, current_time)

    def preempt_job(self, current_time):
        if self.running_job:
            # Logic to free up resources for the currently running job
            # Update the allocation for the running job to indicate it's no longer using resources
            self._allocation[self.running_job] = None

    def schedule_next_job(self, next_job, current_time):
        # Logic to allocate resources to the next job
        # Assuming 'next_job' fits into the available resources
        self._allocation[next_job] = 'allocated'  # Replace with actual resource allocation logic
        self.running_job = next_job

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        # Return the current allocation
        return self._allocation


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

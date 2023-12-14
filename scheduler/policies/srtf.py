import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random
import job_id_pair
from policy import Policy, PolicyWithPacking

class SRTFPolicy(Policy):
    def __init__(self, seed=None, packing_threshold=1.5, mode='base'):
        self._name = 'SRTF'
        if seed is not None:
            self._rng = random.Random(seed)
        self._allocation = {}
        self._scale_factors = {}
        self._packing_threshold = packing_threshold
        self._mode = mode
        self.remaining_times = {}

    def update_remaining_times(self, throughputs):
        for job_id, job_data in throughputs.items():
            # Make sure every job in 'throughputs' has an entry in 'remaining_times'
            self.remaining_times[job_id] = job_data.remaining_time


    def _pack(self, queue, throughputs, scale_factors):
        """
        Attempts to pack jobs together to optimize resource utilization.
        This method might be similar to FIFO but can be adjusted for SRTF specifics.
        """
        while len(queue) > 0:
            max_packed_throughput = self._packing_threshold
            job_id_to_pack_with = None
            job_id_to_schedule = queue.pop(0)  # Consider changing this for SRTF specifics

            for scheduled_job_id in self._allocation:
                # Ensure the job is not already paired and is compatible for packing
                if scheduled_job_id.is_pair() or \
                   (scale_factors[scheduled_job_id] != scale_factors[job_id_to_schedule]):
                    continue

                # Calculate the combined throughput and check if it's beneficial to pack
                worker_type = self._allocation[scheduled_job_id]
                merged_job_id = job_id_pair.JobIdPair(scheduled_job_id[0], job_id_to_schedule[0])
                packed_throughput = throughputs[merged_job_id][worker_type]
                normalized_packed_throughput = sum(
                    packed_throughput[i] / throughputs[single_job_id][worker_type]
                    for i, single_job_id in enumerate(merged_job_id.singletons())
                    if packed_throughput[i] > 0.0
                )

                if normalized_packed_throughput > max_packed_throughput:
                    max_packed_throughput = normalized_packed_throughput
                    job_id_to_pack_with = scheduled_job_id

            if job_id_to_pack_with is None:
                break  # No beneficial packing found, respect the queue order
            else:
                # Perform the packing
                merged_job_id = job_id_pair.JobIdPair(job_id_to_pack_with[0], job_id_to_schedule[0])
                worker_type = self._allocation[job_id_to_pack_with]
                self._allocation[merged_job_id] = worker_type
                del self._allocation[job_id_to_pack_with]

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)
        queue = []

        # Update the internal representation of scale_factors.
        for job_id in scale_factors:
            self._scale_factors[job_id] = scale_factors[job_id]

        # Add all jobs that have not been allocated already to the queue.
        for job_id in throughputs:
            if job_id not in self._allocation and not job_id.is_pair():
                queue.append(job_id)

        # Sort jobs based on their remaining time using the separate mapping
        queue.sort(key=lambda job_id: self.remaining_times.get(job_id, float('inf')))

        # Find all available workers.
        available_worker_types = [worker_type for worker_type in available_workers if available_workers[worker_type] > 0]
        available_worker_types.sort()

        # Allocate resources to jobs based on SRTF
        while len(queue) > 0 and len(available_worker_types) > 0:
            job_id_to_schedule = queue.pop(0)  # Get the job with the shortest remaining time
            scale_factor = self._scale_factors[job_id_to_schedule]
            available_worker_types_with_scale_factor = [worker_type for worker_type in available_worker_types if available_workers[worker_type] >= scale_factor]

            if len(available_worker_types_with_scale_factor) == 0:
                break  # No available workers for this job

            # Allocate resources to the job
            worker_type = available_worker_types_with_scale_factor[0]  # Choose the first available worker type
            self._allocation[job_id_to_schedule] = worker_type
            available_workers[worker_type] -= scale_factor

        # Packing logic based on _mode
        if self._mode == 'packing':
            self._pack(queue, throughputs, scale_factors)

        # Construct output allocation with additional checks
        final_allocation = {job_id: {worker_type: 0.0 for worker_type in cluster_spec} for job_id in throughputs}
        for job_id, worker_type in self._allocation.items():
            if job_id in final_allocation and worker_type in final_allocation[job_id]:
                final_allocation[job_id][worker_type] = 1.0
            else:
                # Handle unexpected job_id or worker_type
                # This could be a logging statement or other error handling
                print(f"Warning: Job ID {job_id} or Worker Type {worker_type} not recognized.")

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
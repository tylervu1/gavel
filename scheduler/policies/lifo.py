import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random

import job_id_pair
from policy import Policy, PolicyWithPacking

class LIFOPolicy(Policy):
    def __init__(self, mode='base', seed=None, packing_threshold=1.5):
        self._name = 'LIFO'
        self._mode = mode
        self._allocation = {}
        self._scale_factors = {}
        if mode == 'base':
            self._rng = random.Random()
            if seed is not None:
                self._rng.seed(seed)
        elif mode == 'packing':
            self._packing_threshold = packing_threshold

    def _pack(self, queue, throughputs, scale_factors):
        while len(queue) > 0:
            # Only make a packing decision if combined normalized
            # throughput would provide a signficant gain.
            max_packed_throughput = self._packing_threshold
            job_id_to_pack_with = None
            job_id_to_schedule = queue.pop()

            # Find the already scheduled job with which the next job on
            # the queue will pack best with.
            for scheduled_job_id in self._allocation:
                assert scheduled_job_id != job_id_to_schedule
                assert scheduled_job_id in throughputs
                if scheduled_job_id.is_pair():
                    continue
                if (scale_factors[scheduled_job_id] !=\
                        scale_factors[job_id_to_schedule]):
                    continue
                worker_type = self._allocation[scheduled_job_id]
                merged_job_id = \
                        job_id_pair.JobIdPair(scheduled_job_id[0],
                                              job_id_to_schedule[0])
                packed_throughput = throughputs[merged_job_id][worker_type]
                normalized_packed_throughput = 0.0
                for i, single_job_id in enumerate(merged_job_id.singletons()):
                    if packed_throughput[i] <= 0.0:
                        continue
                    isolated_throughput = \
                            throughputs[single_job_id][worker_type]
                    normalized_packed_throughput += \
                            packed_throughput[i] / isolated_throughput
                if normalized_packed_throughput > max_packed_throughput:
                    max_packed_throughput = normalized_packed_throughput
                    job_id_to_pack_with = scheduled_job_id
            if job_id_to_pack_with is None:
                # Terminate when we cannot find a job to pack with.
                # This respects the FIFO property of no jobs being able
                # to jump ahead in the queue.
                break
            else:
                # Transfer the allocation for the single job to the
                # packed job.
                self._output = None
                merged_job_id = \
                        job_id_pair.JobIdPair(job_id_to_pack_with[0],
                                              job_id_to_schedule[0])
                worker_type = self._allocation[job_id_to_pack_with]
                del self._allocation[job_id_to_pack_with]
                self._allocation[merged_job_id] = worker_type

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        available_workers = copy.deepcopy(cluster_spec)
        queue = []

        # Update the internal representation of scale_factors.
        for job_id in scale_factors:
            self._scale_factors[job_id] = scale_factors[job_id]

        # Reset the allocation when running in performance-aware mode.
        if self._mode != 'base':
            self._allocation = {}

        # Add all jobs that have not been allocated already to the queue.
        for job_id in throughputs:
            if job_id not in self._allocation and not job_id.is_pair():
                queue.append(job_id)

        # Handling completed jobs
        for scheduled_job_id in list(self._allocation.keys()):  # Use a list of keys
            worker_type = self._allocation[scheduled_job_id]
            if scheduled_job_id not in throughputs:
                for single_job_id in scheduled_job_id.singletons():
                    if single_job_id in throughputs:
                        queue.append(single_job_id)
                if len(queue) > 0:
                    job_id_to_schedule = queue.pop()  # Pop last for LIFO
                    if (scale_factors[job_id_to_schedule] <=
                            available_workers[worker_type]):
                        self._allocation[job_id_to_schedule] = worker_type
                        available_workers[worker_type] -= \
                            scale_factors[job_id_to_schedule]
                del self._allocation[scheduled_job_id]
                del self._scale_factors[scheduled_job_id]
            else:
                # Subtract allocated workers from available_workers.
                available_workers[worker_type] -= \
                    scale_factors[scheduled_job_id]

        # Find all available workers.
        available_worker_types = [worker_type for worker_type in available_workers if available_workers[worker_type] > 0]
        available_worker_types.sort()

        # Allocate resources to as many jobs as possible, LIFO style.
        while len(queue) > 0 and len(available_worker_types) > 0:
            job_id_to_schedule = queue.pop()  # Pop last element for LIFO
            scale_factor = scale_factors[job_id_to_schedule]
            available_worker_types_with_scale_factor = []
            original_available_worker_types_mapping = []
            for i, worker_type in enumerate(available_worker_types):
                if available_workers[worker_type] >= scale_factor:
                    available_worker_types_with_scale_factor.append(worker_type)
                    original_available_worker_types_mapping.append(i)
            if len(available_worker_types_with_scale_factor) == 0:
                break
            if self._mode == 'base':
                worker_type_idx = self._rng.randrange(
                        len(available_worker_types_with_scale_factor))
            else:
                # Find the worker_type with best performance for this job.
                worker_type = None
                worker_type_idx = None
                max_throughput = -1
                for i, x in enumerate(available_worker_types_with_scale_factor):
                    throughput = throughputs[job_id_to_schedule][x]
                    if throughput > max_throughput:
                        max_throughput = throughput
                        worker_type = x
                        worker_type_idx = i
            if throughputs[job_id_to_schedule][worker_type] > 0.0:
                self._allocation[job_id_to_schedule] = worker_type
                available_workers[worker_type] -= scale_factors[job_id_to_schedule]
                if available_workers[worker_type] == 0:
                    worker_type_idx =\
                        original_available_worker_types_mapping[worker_type_idx]
                    available_worker_types.pop(worker_type_idx)

        # Packing logic can remain the same as in FIFO or be modified as per requirements
        if self._mode == 'packing':
            self._pack(queue, throughputs, scale_factors)

        # Construct output allocation
        final_allocation = {job_id: {worker_type: 0.0 for worker_type in cluster_spec} for job_id in throughputs}
        for job_id, worker_type in self._allocation.items():
            final_allocation[job_id][worker_type] = 1.0

        return final_allocation


class LIFOPolicyWithPerf(Policy):
    def __init__(self, packing=False):
        self._name = 'LIFO_Perf'
        self._packing = packing
        self._policy = LIFOPolicy(mode='perf')

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        return self._policy.get_allocation(throughputs, scale_factors, cluster_spec)

class LIFOPolicyWithPacking(PolicyWithPacking):
    def __init__(self, packing_threshold=1.5):
        self._name = 'LIFO_Packing'
        self._policy = LIFOPolicy(mode='packing', packing_threshold=packing_threshold)

    def get_allocation(self, throughputs, scale_factors, cluster_spec):
        return self._policy.get_allocation(throughputs, scale_factors, cluster_spec)

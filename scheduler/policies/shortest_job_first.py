import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import copy
import random

import job_id_pair
from policy import Policy, PolicyWithPacking

# class ShortestJobFirstPolicy(Policy):
#     def __init__(self, mode='base', seed=None, packing_threshold=1.5):
#         self._name = 'ShortestJobFirst'
#         self._mode = mode
#         self._allocation = {}
#         self._scale_factors = {}
#         if mode == 'base':
#             self._rng = random.Random()
#             if seed is not None:
#                 self._rng.seed(seed)
#         elif mode == 'packing':
#             self._packing_threshold = packing_threshold

#     def _pack(self, queue, throughputs, scale_factors):
#         while len(queue) > 0:
#             # Only make a packing decision if combined normalized
#             # throughput would provide a signficant gain.
#             max_packed_throughput = self._packing_threshold
#             job_id_to_pack_with = None
#             job_id_to_schedule = queue.pop(0)

#             # Find the already scheduled job with which the next job on
#             # the queue will pack best with.
#             for scheduled_job_id in self._allocation:
#                 assert scheduled_job_id != job_id_to_schedule
#                 assert scheduled_job_id in throughputs
#                 if scheduled_job_id.is_pair():
#                     continue
#                 if (scale_factors[scheduled_job_id] !=\
#                         scale_factors[job_id_to_schedule]):
#                     continue
#                 worker_type = self._allocation[scheduled_job_id]
#                 merged_job_id = \
#                         job_id_pair.JobIdPair(scheduled_job_id[0],
#                                               job_id_to_schedule[0])
#                 packed_throughput = throughputs[merged_job_id][worker_type]
#                 normalized_packed_throughput = 0.0
#                 for i, single_job_id in enumerate(merged_job_id.singletons()):
#                     if packed_throughput[i] <= 0.0:
#                         continue
#                     isolated_throughput = \
#                             throughputs[single_job_id][worker_type]
#                     normalized_packed_throughput += \
#                             packed_throughput[i] / isolated_throughput
#                 if normalized_packed_throughput > max_packed_throughput:
#                     max_packed_throughput = normalized_packed_throughput
#                     job_id_to_pack_with = scheduled_job_id
#             if job_id_to_pack_with is None:
#                 # Terminate when we cannot find a job to pack with.
#                 # This respects the FIFO property of no jobs being able
#                 # to jump ahead in the queue.
#                 return
#             else:
#                 # Pack the job with the best job we found.

class ShortestJobFirstPolicy(Policy):
    def __init__(self, mode='base', seed=None, packing_threshold=1.5):
        self._name = 'ShortestJobFirst'
        self._mode = mode
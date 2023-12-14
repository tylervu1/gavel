import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import cvxpy as cp
import numpy as np

import job_id_pair
from policy import Policy, PolicyWithPacking

class ShortestJobFirstPolicy(Policy):
    def __init__(self, solver):
        self._name = 'ShortestJobFirst'
        self._sjf_perf_policy = \
            ShortestJobFirstPolicyWithPerf(solver)

    def get_allocation(self, unflattened_throughputs, scale_factors, 
                       num_steps_remaining, cluster_spec):
        # Sort jobs by the remaining number of steps
        sorted_jobs = sorted(num_steps_remaining.items(), key=lambda item: item[1])
        sorted_job_ids = [job[0] for job in sorted_jobs]

        # Flatten the throughputs as per the cluster spec
        throughputs, index = self.flatten(unflattened_throughputs, cluster_spec)
        if throughputs is None:
            return None
        (m, n) = throughputs.shape
        job_ids, worker_types = index

        # Prepare scale factors array
        scale_factors_array = self.scale_factors_array(scale_factors, job_ids, m, n)

        # Initialize allocation matrix
        allocation = np.zeros_like(throughputs)

        # Track available capacity in the cluster
        available_capacity = np.sum(cluster_spec, axis=0)  # Assuming cluster_spec is a 2D array with resource capacities

        for job_id in sorted_job_ids:
            # Allocate resources for this job
            job_index = job_ids.index(job_id)
            job_throughput = throughputs[job_index, :]
            job_scale_factor = scale_factors_array[job_index, :]
            
            # Optimize allocation for this job
            job_allocation = self.optimize_job_allocation(job_throughput, job_scale_factor, available_capacity)

            # Update the overall allocation and the available capacity
            allocation[job_index, :] = job_allocation
            available_capacity -= job_allocation

        return self.unflatten(allocation, index)

    def optimize_job_allocation(self, job_throughput, job_scale_factor, cluster_spec):
        # Implement the optimization logic here
        # This method should return the optimal resource allocation for a single job

        # Example optimization code (needs to be adapted to your specific requirements):
        x = cp.Variable(len(job_throughput))
        objective = cp.Maximize(job_throughput @ x)
        constraints = [
            0 <= x,
            x <= job_scale_factor,  # Adjust this to match the job's scale factor
            cp.sum(x) <= np.sum(cluster_spec)  # Total allocation must not exceed total capacity
        ]
        prob = cp.Problem(objective, constraints)
        prob.solve(solver=self._solver)

        return x.value.clip(min=0)  # Ensure non-negative allocation
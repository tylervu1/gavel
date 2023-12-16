# Heterogeneity-Aware Cluster Scheduling Policies for Deep Learning Workloads

This repository contains the source code implementation of the OSDI paper
"Heterogeneity-Aware Cluster Scheduling Policies for Deep Learning Workloads".
The full writeup for our COS316 final project can be found here:
https://docs.google.com/document/d/1UyNbXnTeb6vuWOPzF1QgmYuzp8sCvZ9euJOEKOAidaA/edit?usp=sharing

## Project Goals and Description
Using Rui’s Idea #2 as a template for our project, we wanted to use Stanford’s gavel repository in order to run and evaluate already-implemented and self-implemented scheduling policies using the following metrics: average job completion time (JCT), makespan, and cluster utilization. Scheduling policies are algorithms that are used by operating systems or applications to manage the order in which tasks are executed. It is imperative that these policies exist in order to facilitate the multi-tasking of computation and optimize resource allocation. This project documents and compares different scheduling policies to assess their impact given the specified cluster configurations and workload traces, thereby yielding scheduling simulation results.

## Design Overview
The system is built using three different components: the simulator for cluster experiments, workload traces, and cluster specifications. The main areas of attention in our repository are the scheduler (scheduling mechanism and simulator), policies (implementations of various algorithms), and performance (evaluates results).

- Workload Traces - a record of the jobs given their arrival time and resource requirements.
- Cluster Specifications - available types and quantities of GPU resources.

The simulator is given a workload trace and cluster specifications and yields data regarding the efficiency of the scheduling policy.

## Directory Structure

### `scheduler`
Code for the scheduler, including the scheduling mechanism and simulator
(`scheduler.py`), implementations of performance-aware policies (`policies/`),
`GavelIterator` as a Python module, and a communication stack between the scheduler
and workers that uses [gRPC](https://grpc.io/) (`runtime/`).

`scheduler/notebooks` contains parsing and plotting code to analyze experiment
runs.

### `workloads`
Implementations of target workloads in PyTorch, including changes needed to
integrate with the `GavelIterator`.


## Setup

### Software Dependencies

Gavel is implemented in Python. We have tested Gavel on Ubuntu 16.04 with Python 3.8
and on Ubuntu 20.04 with Python 3.11.5. To make it easier to replicate environments,
we dockerized our application.

To begin, we created a script to generate necessary the Dockerfile and adjust the
`scheduler/requirements.txt` to have the correct libraries.

```bash
chmod +x generate_files.sh
./generate_files.sh
```

Next, we can simply build and run the docker environment.

```bash
docker build -t gavel_project .
docker run -it gavel_project
```

## Getting Started

We evaluated Gavel's heterogeneity-aware policies and scheduling mechanism on a simulation cluster.

To simulate a cluster, we ran the `simulate_scheduler_with_trace.py` on the `medium_test.trace` file. This file provided us a high enough cluster utilization rate that allowed us to evaluate different policies. However, more traces can be found in `traces/physical_cluster`. For consistent results, we kept the cluster amount to 4 and seed to 123.

```bash
python scripts/drivers/simulate_scheduler_with_trace.py -t traces/physical_cluster/medium_test.trace -p <insert-policy> -c 4:0:0 --seed 123
```

Here's an example of how we simulated the 'fifo' policy:

```bash
python scripts/drivers/simulate_scheduler_with_trace.py -t traces/physical_cluster/medium_test.trace -p fifo -c 4:0:0 --seed 123
```

Other arguments for the `simulate_scheduler_with_trace.py` script are shown using the -h option:
```bash
usage: simulate_scheduler_with_trace.py [-h] -t TRACE_FILE
                                        [-p {allox,fifo,fifo_perf,fifo_packed,finish_time_fairness,finish_time_fairness_perf,finish_time_fairness_packed,gandiva,isolated,lifo,max_min_fairness,max_min_fairness_perf,max_min_fairness_packed,max_min_fairness_water_filling,max_min_fairness_water_filling_perf,max_min_fairness_water_filling_packed,max_sum_throughput_perf,max_sum_throughput_normalized_by_cost_perf,max_sum_throughput_normalized_by_cost_perf_SLOs,max_sum_throughput_normalized_by_cost_packed_SLOs,min_total_duration,min_total_duration_perf,min_total_duration_packed,sjf,srtf}]
                                        [--throughputs_file THROUGHPUTS_FILE] [-c CLUSTER_SPEC] [--num_gpus_per_server NUM_GPUS_PER_SERVER] [--seed SEED]
                                        [--solver {ECOS,GUROBI,SCS}] [-d] [--checkpoint_threshold CHECKPOINT_THRESHOLD] [--checkpoint_file CHECKPOINT_FILE]
                                        [--time_per_iteration TIME_PER_ITERATION] [-s WINDOW_START] [-e WINDOW_END]

Run scheduler with trace

optional arguments:
  -h, --help            show this help message and exit
  -t TRACE_FILE, --trace_file TRACE_FILE
                        Trace file
  -p {allox,fifo,fifo_perf,fifo_packed,finish_time_fairness,finish_time_fairness_perf,finish_time_fairness_packed,gandiva,isolated,lifo,max_min_fairness,max_min_fairness_perf,max_min_fairness_packed,max_min_fairness_water_filling,max_min_fairness_water_filling_perf,max_min_fairness_water_filling_packed,max_sum_throughput_perf,max_sum_throughput_normalized_by_cost_perf,max_sum_throughput_normalized_by_cost_perf_SLOs,max_sum_throughput_normalized_by_cost_packed_SLOs,min_total_duration,min_total_duration_perf,min_total_duration_packed,sjf,srtf}, --policy {allox,fifo,fifo_perf,fifo_packed,finish_time_fairness,finish_time_fairness_perf,finish_time_fairness_packed,gandiva,isolated,lifo,max_min_fairness,max_min_fairness_perf,max_min_fairness_packed,max_min_fairness_water_filling,max_min_fairness_water_filling_perf,max_min_fairness_water_filling_packed,max_sum_throughput_perf,max_sum_throughput_normalized_by_cost_perf,max_sum_throughput_normalized_by_cost_perf_SLOs,max_sum_throughput_normalized_by_cost_packed_SLOs,min_total_duration,min_total_duration_perf,min_total_duration_packed,sjf,srtf}
                        Scheduler policy
  --throughputs_file THROUGHPUTS_FILE
                        Oracle throughputs file
  -c CLUSTER_SPEC, --cluster_spec CLUSTER_SPEC
                        Cluster specification in the form of #v100s:#p100s:#k80s
  --num_gpus_per_server NUM_GPUS_PER_SERVER
                        Cluster specification in the form of #v100s:#p100s:#k80s
  --seed SEED           Random seed
  --solver {ECOS,GUROBI,SCS}
                        CVXPY solver
  -d, --debug           Debug
  --checkpoint_threshold CHECKPOINT_THRESHOLD
                        Create checkpoint when this job ID comes in
  --checkpoint_file CHECKPOINT_FILE
                        Load checkpoint located at passed incheckpoint_file
  --time_per_iteration TIME_PER_ITERATION
                        Time per iteration in seconds
  -s WINDOW_START, --window-start WINDOW_START
                        measurement window start (job id)
  -e WINDOW_END, --window-end WINDOW_END
                        Measurement window end (job ID)
```

## Scheduling Policies
Already-implemented:
- FIFO (First-In-First-Out) - jobs scheduled in order of arrival.
- Max_Min_Fairness - emphasizes fairness by maximizing the minimum allocation to any process and ensures that resources are distributed to avoid imbalances.

Self-implemented:
- LIFO (Last-In-First-Out) - jobs scheduled in order of most recently arrived.
- SJF (Shortest Job First) - prioritizes jobs based on execution time.
- SJF_Packed (Shortest Job First with Packing) - variation of SJF that optimizes utilization and throughput by packing shorter jobs together.
- SRTF (Shortest Remaining Time First) - preemptive variation of SJF that can interrupt a currently running process if a shorter remaining time job arrives.

## Performance Evaluation
Our system evaluates each scheduling policy using the following metrics: average job completion time (JCT), makespan, and cluster utilization. Average job completion time is self-explanatory, which is the mean time taken to finish jobs after their arrival time. Makespan is the total time to run all the jobs in the workload trace. Cluster utilization is the efficiency of resource usage to make sure that GPU’s don’t idle. When conducting our experiments, we used 4 GPU’s. All of these metrics allow us to get a good understanding of the strengths and weaknesses of each scheduling policy that we test in the simulator.

# Results
FIFO
- Average JCT - 6.77 hrs
- Makespan - 14.91 hrs
- Cluster Utilization - 81.2%
Max_Min_Fairness
- Average JCT - 8.54 hrs
- Makespan - 12.42 hrs
- Cluster Utilization - 97.5%
LIFO
- Average JCT - 8.02 hrs
- Makespan - 14.15 hrs
- Cluster Utilization - 85.6%
SJF
- Average JCT - 8.37 hrs
- Makespan - 12.53 hrs
- Cluster Utilization - 96.7%
SJF_Packed
- Average JCT - 5.63 hrs
- Makespan - 11.24 hrs
- Cluster Utilization - 83.1%
SRTF
- Average JCT - 7.79 hrs
- Makespan - 12.82 hrs
- Cluster Utilization - 94.5%

## Analysis and Conclusion
We see that FIFO had the second lowest average JCT of 6.77 hours but the largest makespan of 14.91 hours. Max_Min_Fairness exhibited higher average JCT of 8.54 hours, lower makespan of 12.42 hours, and high cluster utilization of 97.5% which suggests that it balances between individual job processing time and overall efficiency well. LIFO had an average performance in all three metrics which indicates that it does not excel in any particular area. SJF had similar performances to Max_Min_Fairness which indicates its reliability and efficiency. SJF_Packed had the lowest average JCT of 5.63 hours and also the lowest makespan of 11.24 hours.

In conclusion, our project demonstrated the differences between each scheduling policy using the metrics we used to test them. Different applications with varying goals may utilize different scheduling policies for varying results. If an application were to prioritize individual job completion time, SJF_Packed is the best choice with the lowest average JCT. If an application were to prioritize a balance between efficient use of resources and overall completion time, Max_Min_Fairness and SRTF would be preferable.
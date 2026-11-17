# CampusCompute

A C command-line prototype demonstrating operating-system concepts.

## Prerequisites

- Ubuntu or another Linux environment
- GCC
- GNU Make
- POSIX threads, shared memory, and semaphores (provided by Linux)

## Build

```bash
make

## Commands

./campuscompute help
./campuscompute fcfs
./campuscompute rr
./campuscompute priority
./campuscompute all
./campuscompute logger
./campuscompute ipc
./campuscompute banker-safe
./campuscompute banker-unsafe
./campuscompute worker-normal
./campuscompute worker-fail
./campuscompute limit
./campuscompute integrated


The banker-safe and banker-unsafe commands prompt for Available, Allocation, and Maximum values. Enter three non-negative integers at each prompt. The program calculates Need and reports whether the entered state is safe.

The worker-fail command demonstrates a controlled simulated failure; it does not represent a real operating-system failure.

The logger writes events to logs/campuscompute.log. The IPC demo removes the shared-memory and semaphore objects it creates. The resource-limit demo restores the original limit when it finishes.

## Clean build

    make clean

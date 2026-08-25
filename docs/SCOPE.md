# Project Scope

## Purpose

This project develops a family of Qwen3-based models specialized for computer engineering and closely related technical work.

The objective is to improve performance on practical engineering tasks while preserving the general capabilities of the original Qwen3 checkpoints.

Development will proceed from small checkpoints to larger models only when the dataset, evaluation process, and training configuration have been validated at the previous stage.

## Core Domains

The project will focus primarily on the following areas.

### 1. Software Engineering

- Software design and architecture
- Code generation
- Code review
- Refactoring
- Debugging
- Testing
- Build systems
- APIs and service design
- Performance analysis
- Production troubleshooting

### 2. Systems Programming

- C and C++
- Rust
- Python for systems tooling
- Memory management
- Concurrency
- Multithreading
- Processes
- Inter-process communication
- Filesystems
- Low-level debugging

### 3. Operating Systems

- Kernel concepts
- Scheduling
- Virtual memory
- Filesystems
- Device management
- Drivers
- System calls
- Synchronization
- Linux internals
- System performance

### 4. Computer Architecture

- CPU architecture
- GPU architecture
- Instruction sets
- Caches
- Memory hierarchies
- NUMA
- SIMD and vector processing
- PCIe
- Accelerators
- Performance and power trade-offs

### 5. Embedded Systems

- Microcontrollers
- Embedded C/C++
- Interrupts
- Timers
- GPIO
- UART
- SPI
- I2C
- ADC/DAC
- RTOS concepts
- Hardware/software interfaces

### 6. Networking

- TCP/IP
- Routing
- Switching
- DNS
- HTTP
- Network debugging
- Socket programming
- Network architecture
- Performance
- Reliability

### 7. Distributed Systems

- Replication
- Partitioning
- Consensus concepts
- Distributed coordination
- Queues
- Caching
- Fault tolerance
- Load balancing
- Service communication
- Failure analysis

### 8. Linux and Infrastructure

- Linux administration
- Shell scripting
- systemd
- Containers
- Docker
- Virtualization
- Storage
- Networking
- Monitoring
- Deployment
- Infrastructure debugging

### 9. Compute and Model Infrastructure

- GPU computing
- CUDA concepts
- Multi-GPU systems
- Distributed execution
- Memory management
- Model inference
- Quantization
- Model serving
- Performance optimization
- Training infrastructure

The focus of this area is the engineering of compute and model infrastructure rather than general model-generated content.

### 10. Secure Engineering

- Secure coding
- Authentication
- Authorization
- Cryptographic concepts
- Network security
- Dependency security
- Threat analysis
- Defensive security
- Vulnerability remediation

### 11. Engineering Reasoning

The models should be able to:

- Diagnose failures from incomplete information
- Compare engineering alternatives
- Explain technical trade-offs
- Identify bottlenecks
- Propose validation procedures
- Read logs and error messages
- Reason about performance
- Design tests
- Separate assumptions from verified facts
- Recognize when additional information is required

## Expected Behavior

The project should favor:

- Technically correct answers over confident answers
- Reproducible solutions
- Practical implementation details
- Clear assumptions
- Appropriate uncertainty
- Verification where possible
- Concise answers when the problem is simple
- Detailed reasoning when the engineering problem requires it

Code should be intended to compile or execute when the task allows automated verification.

## Out of Scope

This project is not intended to specialize in:

- Creative writing
- Roleplay
- Entertainment content
- General social conversation
- Marketing copy
- Fiction
- General trivia unrelated to technical work

General capabilities inherited from Qwen3 do not need to be deliberately removed, but these areas will not drive dataset development.

## Dataset Requirements

Training examples should have a clear reason for inclusion.

Examples should preferably be:

- Technically verifiable
- Relevant to the defined domains
- Non-duplicative
- Clearly written
- Appropriately difficult
- Representative of real engineering work

Large quantities of low-value synthetic examples should not be used simply to increase dataset size.

Training data and evaluation data must remain separate.

## Evaluation Requirements

Every model stage must be evaluated against its corresponding unmodified Qwen3 checkpoint.

Important measurements include:

- Technical correctness
- Code execution or compilation success
- Debugging accuracy
- Systems reasoning
- Engineering decision quality
- Instruction following
- Regression in general capabilities
- Hallucination and unsupported claims

Whenever practical, evaluation should use executable tests rather than subjective scoring alone.

## Scaling Rule

Increasing model size is not considered progress by itself.

A larger checkpoint should only be used when at least one of the following is true:

1. The current model shows clear improvement from the training dataset.
2. Evaluation indicates that model capacity is becoming a limiting factor.
3. The dataset and training pipeline are stable enough to justify additional compute.
4. The next checkpoint is required to validate a new training or infrastructure problem.

If a smaller model does not improve reliably, the dataset or training method should be fixed before scaling.

## Flagship

The long-term target is a fine-tuned Qwen3 235B-A22B checkpoint.

The current target release window is January–March 2027.

This is a target window rather than a fixed deadline. Technical quality, evaluation results, and reproducibility take priority over releasing to meet a date.

## Status

The project is currently in the scope-definition, dataset-design, and evaluation-design stage.

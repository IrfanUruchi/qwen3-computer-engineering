# Eagle Heterogeneous GPU Device Mapping

Captured: 2026-09-13

## Physical configuration

- RTX 3050 6 GB: primary/display GPU
- RTX 5060 8 GB: secondary-slot, headless compute GPU
- Displays are attached to the RTX 3050.
- RTX 5060 has no active display attached.

## NVML / nvidia-smi enumeration

| NVML index | GPU | UUID | PCI bus |
|---:|---|---|---|
| 0 | NVIDIA GeForce RTX 3050 | GPU-dbd6ee2f-94da-1543-6f67-a7c6c24195da | 00000000:01:00.0 |
| 1 | NVIDIA GeForce RTX 5060 | GPU-1c08f954-f4b9-1633-42e2-2fa869f82f1f | 00000000:04:00.0 |

## PyTorch / CUDA enumeration

Within the current WSL PyTorch environment:

| CUDA index | GPU | VRAM |
|---:|---|---:|
| 0 | NVIDIA GeForce RTX 5060 | 7.93 GiB |
| 1 | NVIDIA GeForce RTX 3050 | 6.00 GiB |

Therefore CUDA device numbering and NVML numbering are reversed.

Do not rely on numeric GPU indices for reproducible experiment identity.
Prefer GPU UUIDs and record PCI bus IDs in run manifests.

## Current PCIe observations

- RTX 3050: PCIe Gen3, current x8 link
- RTX 5060: x4 link in the lower slot
- RTX 5060 downshifts PCIe generation while idle
- GPU-to-GPU topology is reported as PXB
- No NVLink is present

This topology is intentionally retained for heterogeneous-GPU experiments.

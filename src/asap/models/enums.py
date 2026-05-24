"""Enumerations for ASAP protocol.

This module defines all enum types used in the protocol to ensure
type safety and prevent magic strings.
"""

from enum import Enum


class TaskStatus(str, Enum):
    """Task lifecycle states.

    Tasks progress through these states during their lifecycle.
    Terminal states are: COMPLETED, FAILED, CANCELLED.

    Example:
        >>> TaskStatus.COMPLETED.is_terminal()
        True
        >>> TaskStatus.WORKING.is_terminal()
        False
    """

    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INPUT_REQUIRED = "input_required"

    @classmethod
    def terminal_states(cls) -> frozenset["TaskStatus"]:
        """Return all terminal states.

        Returns:
            Frozen set containing all terminal task states
        """
        return frozenset({cls.COMPLETED, cls.FAILED, cls.CANCELLED})

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state."""
        return self in self.terminal_states()


class MessageRole(str, Enum):
    """Message sender roles.

    Defines the role of the entity sending a message in a conversation.

    Example:
        >>> MessageRole.USER.value
        'user'
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class UpdateType(str, Enum):
    """Task update types.

    Defines the type of update being sent for a task.

    Example:
        >>> UpdateType.PROGRESS.value
        'progress'
    """

    PROGRESS = "progress"
    INPUT_REQUIRED = "input_required"
    STATUS_CHANGE = "status_change"


class VerificationState(str, Enum):
    """Verification status for marketplace trust badge."""

    VERIFIED = "verified"
    PENDING = "pending"
    REJECTED = "rejected"


class HardwareClass(str, Enum):
    """Hardware class for edge and physical agents (manifest v2.4+)."""

    CLOUD = "cloud"
    SBC = "sbc"
    EDGE_ACCELERATOR = "edge_accelerator"
    MICROCONTROLLER = "microcontroller"
    DESKTOP = "desktop"


class HardwareIoType(str, Enum):
    """Physical I/O interfaces advertised on a manifest (v2.4+)."""

    GPIO = "gpio"
    I2C = "i2c"
    SPI = "spi"
    UART = "uart"
    CSI_CAMERA = "csi_camera"
    USB_CAMERA = "usb_camera"
    AUDIO_IN = "audio_in"
    AUDIO_OUT = "audio_out"
    BLUETOOTH = "bluetooth"
    LORA = "lora"
    BLE = "ble"


class InferenceMode(str, Enum):
    """Inference execution modes (manifest v2.4+)."""

    CLOUD = "cloud"
    LOCAL_CPU = "local_cpu"
    LOCAL_CUDA = "local_cuda"
    LOCAL_METAL = "local_metal"
    LOCAL_NPU = "local_npu"

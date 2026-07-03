"""Hardware backend stub for the HAL interface.

Replace the NotImplementedError bodies with real GPIO/camera calls
when deploying to the physical robot.
"""
from __future__ import annotations
from sim.hal import HAL


class HardwareHAL(HAL):
    """Stub that mirrors the SimHAL interface for the physical robot."""

    def read_ir(self) -> list[float]:
        # TODO: read IR ring from ADC or I2C expander
        raise NotImplementedError

    def read_compass(self) -> float:
        # TODO: read heading from compass/gyro via I2C
        raise NotImplementedError

    def read_ultrasound(self) -> list[float]:
        # TODO: trigger HC-SR04 sensors and measure echo time
        raise NotImplementedError

    def read_line_sensors(self) -> list[bool]:
        # TODO: read reflectance sensors from GPIO or ADC
        raise NotImplementedError

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        # TODO: convert vx/vy/omega to individual wheel speeds and send PWM
        raise NotImplementedError

    def kick(self, angle_deg: float = 0.0) -> None:
        # TODO: pulse the solenoid / servo that controls the kicker
        # (com 2 solenoides ortogonais, decompor angle_deg entre eles)
        raise NotImplementedError

    def set_dribbler(self, on: bool) -> None:
        # TODO: ligar/desligar o motor do rolete do dribbler
        raise NotImplementedError

    def read_position(self) -> tuple[float, float]:
        # TODO: implement via encoder odometry / dead-reckoning
        raise NotImplementedError

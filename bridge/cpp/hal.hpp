// C++ wrapper over the Python HAL object.
//
// Gives strategy code an Arduino-like API so the same logic can be
// copy-pasted between the robot firmware and the simulator with only
// the HAL implementation swapped.
#pragma once

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <utility>
#include <vector>

namespace py = pybind11;

namespace rcj {

class HAL {
public:
    explicit HAL(py::object py_hal) : hal_(std::move(py_hal)) {}

    // ── Sensors ─────────────────────────────────────────────────────
    std::vector<double> read_ir() {
        return hal_.attr("read_ir")().cast<std::vector<double>>();
    }

    double read_compass() {
        return hal_.attr("read_compass")().cast<double>();
    }

    std::vector<double> read_ultrasound() {
        return hal_.attr("read_ultrasound")().cast<std::vector<double>>();
    }

    std::vector<bool> read_line_sensors() {
        return hal_.attr("read_line_sensors")().cast<std::vector<bool>>();
    }

    std::pair<double, double> read_position() {
        return hal_.attr("read_position")().cast<std::pair<double, double>>();
    }

    // ── Actuators ───────────────────────────────────────────────────
    // vx: forward (m/s), vy: left (m/s), omega: CCW (rad/s)
    void set_velocity(double vx, double vy, double omega) {
        hal_.attr("set_velocity")(vx, vy, omega);
    }

    void kick()  { hal_.attr("kick")(); }
    void stop()  { hal_.attr("stop")(); }

private:
    py::object hal_;
};

}  // namespace rcj

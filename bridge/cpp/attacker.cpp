// Decisao::Attacker — the original Arduino C++ logic, running unmodified
// inside the simulator via the C++ HAL wrapper.
//
// This is the same algorithm as examples/attacker_strategy.py (which was
// ported FROM this C++ code); the bridge closes the loop so teams test the
// real firmware logic instead of a Python translation.
//
// Build:  cd bridge && python setup.py build_ext --inplace
// Run:    python -m sim --strategy bridge.cpp_attacker

#include <cmath>
#include <cstdlib>

#include "hal.hpp"

namespace {

constexpr double kMaxPower = 280.0;
constexpr double kMaxSpeed = 1.5;                    // m/s, matches body.max_speed
constexpr double kScale    = kMaxSpeed / kMaxPower;
constexpr double kPi       = 3.14159265358979323846;

// Arduino map() — float math truncated to int, no clamping.
// Mirrors examples/attacker_strategy.py::_map exactly so the C++ and
// Python strategies stay bit-identical in the sim.
int arduino_map(double x, double in_min, double in_max,
                double out_min, double out_max) {
    return static_cast<int>(
        (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min);
}

// IR ring → (ball angle in degrees, detected flag)
// angle: -180..180, 0 = front, + = left (CCW), − = right
void ir_to_ball(const std::vector<double>& ir, double& angle, int& dist) {
    angle = 0.0;
    dist  = 0;
    if (ir.empty()) return;

    std::size_t peak = 0;
    for (std::size_t i = 1; i < ir.size(); ++i)
        if (ir[i] > ir[peak]) peak = i;

    if (ir[peak] < 0.05) return;   // no reliable signal

    angle = (static_cast<double>(peak) / ir.size()) * 360.0;
    if (angle > 180.0) angle -= 360.0;
    dist = 1;
}

}  // namespace

void attacker_strategy(rcj::HAL& hal) {
    const auto ir    = hal.read_ir();
    const auto lines = hal.read_line_sensors();

    double ball_angle = 0.0;
    int    dist       = 0;
    ir_to_ball(ir, ball_angle, dist);

    // Line sensors: [front, back, right, left] (YAML order)
    const bool lf = lines.size() > 0 && lines[0];
    const bool lt = lines.size() > 1 && lines[1];
    const bool ld = lines.size() > 2 && lines[2];
    const bool le = lines.size() > 3 && lines[3];

    int vel_x = 0;   // strafe   (original: + = right)
    int vel_y = 0;   // forward  (original: + = front)

    if (dist != 0 && !(ld || lf || le || lt)) {
        // ── Ball detected, clear of lines ──────────────────────────
        int    power     = 240;
        double mov_angle = std::abs(ball_angle);

        if (mov_angle < 5) {
            mov_angle = 0;
            power     = 280;
        } else if (mov_angle <= 20) {
            power = 240;                                        // angle unchanged
        } else if (mov_angle <= 65) {
            mov_angle = arduino_map(mov_angle, 20,  65,  60,  95);
        } else if (mov_angle <= 95) {
            mov_angle = arduino_map(mov_angle, 60,  95,  65, 130);
        } else if (mov_angle <= 135) {
            mov_angle = arduino_map(mov_angle, 95, 135,  95, 180);
        } else if (mov_angle <= 185) {
            mov_angle = arduino_map(mov_angle, 135, 180, 135, 275);
        }

        if (ball_angle < 0) mov_angle = -mov_angle;

        const double rad = -(mov_angle * kPi / 180.0);
        vel_x = static_cast<int>(std::sin(rad) * power);
        vel_y = static_cast<int>(std::cos(rad) * power);

    } else if (dist != 0) {
        // ── Line sensor active → back away from the edge ───────────
        if (lf) vel_y = -200;
        if (lt) vel_y =  200;
        if (ld) vel_x = -200;
        if (le) vel_x =  200;
    }
    // No ball detected: stop (vel_x = vel_y = 0)

    // Convert to HAL frame: vx = forward, vy = left
    hal.set_velocity(vel_y * kScale, -vel_x * kScale, 0.0);

    // Kick when the ball is straight ahead and close
    double peak = 0.0;
    for (double v : ir) peak = std::max(peak, v);
    if (dist && peak > 0.75 && std::abs(ball_angle) < 20.0)
        hal.kick();
}

// ── Python module ─────────────────────────────────────────────────────
PYBIND11_MODULE(cpp_attacker, m) {
    m.doc() = "RCJ attacker strategy compiled from the original C++ firmware";
    m.def("strategy", [](py::object py_hal) {
        rcj::HAL hal(std::move(py_hal));
        attacker_strategy(hal);
    }, py::arg("hal"), "Decision function: reads sensors, sets actuators.");
}

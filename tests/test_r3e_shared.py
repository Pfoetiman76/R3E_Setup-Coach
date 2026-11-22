"""Tests für r3e_shared.py: Strukturgrößen, Roundtrip und Einheitenumrechnung.

Läuft komplett ohne Windows/RaceRoom: R3EMemory.build_buffer() erzeugt
aus echten ctypes-Strukturen einen Byte-Puffer, den R3EMemory(mem=...) wie
den echten Shared Memory liest.
"""

import ctypes

import pytest

from r3e_coach import r3e_shared as r3s


def test_struct_sizes_match_r3e_header():
    """pack(1), Feld-für-Feld aus r3e.h v3.6 abgetragen."""
    assert ctypes.sizeof(r3s.R3EPlayerData) == 560
    assert r3s.R3E_VERSION_MAJOR == 3 and r3s.R3E_VERSION_MINOR == 6
    assert r3s.R3E_SHARED_MEMORY_NAME == "$R3E"


def test_gamemode_unavailable_means_not_running():
    def mutate(s):
        s.game_mode = r3s.GAMEMODE_UNAVAILABLE
    mem = r3s.R3EMemory(mem=r3s.R3EMemory.build_buffer(mutate))
    frame = mem.read_frame()
    assert frame.running is False


def test_frame_roundtrip_converts_units():
    def mutate(s):
        s.game_mode = r3s.SESSION_PRACTICE  # != unavailable
        s.session_type = r3s.SESSION_PRACTICE
        s.in_pitlane = 0
        s.game_in_menus = 0
        s.game_paused = 0
        s.lap_time_current_self = 42.5
        s.car_speed = 40.0            # m/s -> 144 km/h
        s.throttle = 0.75
        s.brake = 0.10
        s.steer_input_raw = 0.5
        s.steer_lock_degrees = 12      # int32: 0.5 * 12 = 6.0 deg
        s.player.local_g_force.x = 1.4     # g_lat
        s.player.local_g_force.z = -2.0    # g_long = +2.0 (Bremsen negativ)
        s.player.suspension_deflection[:] = [0.021, 0.022, 0.023, 0.024]  # m -> mm
        s.tire_pressure[:] = [180.0, 182.0, 178.0, 176.0]                # kPa -> bar
        for i in range(4):
            for j in range(3):
                s.tire_temp[i].current_temp[j] = 85.0 + i
        s.brake_temp[0].current_temp = 300.0
        s.brake_temp[1].current_temp = 310.0
        s.brake_temp[2].current_temp = 290.0
        s.brake_temp[3].current_temp = 280.0
        s.track_name = b"Sachsenring"
        s.layout_name = b"Sachsenring"
        s.vehicle_info.name = b"Audi R8 LMS"

    mem = r3s.R3EMemory(mem=r3s.R3EMemory.build_buffer(mutate))
    f = mem.read_frame()
    assert f.running is True
    assert f.lap_time == pytest.approx(42.5)
    assert f.speed_kmh == pytest.approx(144.0)
    assert f.throttle == pytest.approx(0.75)
    assert f.brake == pytest.approx(0.10)
    assert f.steer_deg == pytest.approx(6.0)
    assert f.g_lat == pytest.approx(1.4)
    assert f.g_long == pytest.approx(2.0)
    assert f.susp_travel == pytest.approx([21.0, 22.0, 23.0, 24.0])
    assert f.tyre_temp[0] == pytest.approx(85.0)
    assert f.tyre_temp[3] == pytest.approx(88.0)
    assert f.tyre_press == pytest.approx([1.8, 1.82, 1.78, 1.76])
    assert f.brake_temp == pytest.approx([300.0, 310.0, 290.0, 280.0])
    assert f.track == "Sachsenring"
    assert f.layout == "Sachsenring"
    assert f.vehicle == "Audi R8 LMS"


def test_menus_pause_pit_flags_map_to_frame():
    def mutate_running(s):
        s.game_mode = r3s.SESSION_PRACTICE
    f = r3s.R3EMemory(mem=r3s.R3EMemory.build_buffer(mutate_running)).read_frame()
    assert not f.in_menus and not f.paused and not f.in_pitlane

    def mutate_menus(s):
        s.game_mode = r3s.SESSION_PRACTICE
        s.game_in_menus = 1
    f = r3s.R3EMemory(mem=r3s.R3EMemory.build_buffer(mutate_menus)).read_frame()
    assert f.in_menus is True

    def mutate_pit(s):
        s.game_mode = r3s.SESSION_PRACTICE
        s.in_pitlane = 1
    f = r3s.R3EMemory(mem=r3s.R3EMemory.build_buffer(mutate_pit)).read_frame()
    assert f.in_pitlane is True


def test_empty_buffer_is_padded_and_not_running():
    mem = r3s.R3EMemory(mem=b"")  # wird auf Strukturgröße mit Nullen aufgefüllt
    frame = mem.read_frame()
    assert frame.version == (0, 0)  # gepolstert: keine Version -> nicht laufend
    assert frame.running is False


def test_newer_minor_version_flags_warning():
    def mutate(s):
        s.version_minor = 7
        s.game_mode = r3s.SESSION_PRACTICE
    f = r3s.R3EMemory(mem=r3s.R3EMemory.build_buffer(mutate)).read_frame()
    assert f.version == (3, 7)
    assert f.running is True  # laufend, aber Recorder soll warnen

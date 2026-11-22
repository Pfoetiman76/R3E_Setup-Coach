"""0.8.0: Eigener Zugriff auf die RaceRoom-Shared-Memory-Schnittstelle.

Abgetragen aus der offiziellen Definition von Sector3 (sector3studios/
r3e-api, sample-c/src/r3e.h, Strukturversion 3.6, #pragma pack(1)):
Der Spieldatensatz liegt im Shared-Memory "$R3E" vollständig
nicht-ausgerichtet (pack 1) vor; diese ctypes-Strukturen bilden die
Felder bis einschließlich tire_load 1:1 nach. Die riesige
Fahrerliste (all_drivers_data_1) am Ende des Satzes brauchen wir
nicht — die Vorspann-Offsets sind dadurch unverändert gültig.

Wichtig für Prüfbarkeit: Alle Strukturen sind auch offline testbar,
indem ein synthetischer Puffer über dieselben Structs erzeugt und
gelesen wird (Tests/test_r3e_shared.py). Unter Windows wird der
echte Shared Memory über mmap angehängt.
"""

import ctypes as _ctypes
import mmap
import os
import sys
import time

R3E_SHARED_MEMORY_NAME = "$R3E"
R3E_VERSION_MAJOR = 3
R3E_VERSION_MINOR = 6

TIRE_FL = 0
TIRE_FR = 1
TIRE_RL = 2
TIRE_RR = 3
TIRE_INDEX_MAX = 4

GAMEMODE_UNAVAILABLE = -1
SESSION_UNAVAILABLE = -1
SESSION_PRACTICE = 0
SESSION_QUALIFY = 1
SESSION_RACE = 2
SESSION_WARMUP = 3


class _Vec3F64(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("x", _ctypes.c_double), ("y", _ctypes.c_double), ("z", _ctypes.c_double)]


class _Vec3F32(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("x", _ctypes.c_float), ("y", _ctypes.c_float), ("z", _ctypes.c_float)]


class _OriF32(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("pitch", _ctypes.c_float), ("yaw", _ctypes.c_float), ("roll", _ctypes.c_float)]


class R3EPlayerData(_ctypes.Structure):
    # 1:1 aus r3e.h (r3e_playerdata), pack(1)
    _pack_ = 1
    _fields_ = [
        ("user_id", _ctypes.c_int32),
        ("game_simulation_ticks", _ctypes.c_int32),
        ("game_simulation_time", _ctypes.c_double),
        ("position", _Vec3F64),
        ("velocity", _Vec3F64),
        ("local_velocity", _Vec3F64),
        ("acceleration", _Vec3F64),
        ("local_acceleration", _Vec3F64),
        ("orientation", _Vec3F64),
        ("rotation", _Vec3F64),
        ("angular_acceleration", _Vec3F64),
        ("angular_velocity", _Vec3F64),
        ("local_angular_velocity", _Vec3F64),
        ("local_g_force", _Vec3F64),
        ("steering_force", _ctypes.c_double),
        ("steering_force_percentage", _ctypes.c_double),
        ("engine_torque", _ctypes.c_double),
        ("current_downforce", _ctypes.c_double),
        ("voltage", _ctypes.c_double),
        ("ers_level", _ctypes.c_double),
        ("power_mgu_h", _ctypes.c_double),
        ("power_mgu_k", _ctypes.c_double),
        ("torque_mgu_k", _ctypes.c_double),
        ("suspension_deflection", _ctypes.c_double * TIRE_INDEX_MAX),
        ("suspension_velocity", _ctypes.c_double * TIRE_INDEX_MAX),
        ("camber", _ctypes.c_double * TIRE_INDEX_MAX),
        ("ride_height", _ctypes.c_double * TIRE_INDEX_MAX),
        ("front_wing_height", _ctypes.c_double),
        ("front_roll_angle", _ctypes.c_double),
        ("rear_roll_angle", _ctypes.c_double),
        ("third_spring_suspension_deflection_front", _ctypes.c_double),
        ("third_spring_suspension_velocity_front", _ctypes.c_double),
        ("third_spring_suspension_deflection_rear", _ctypes.c_double),
        ("third_spring_suspension_velocity_rear", _ctypes.c_double),
        ("unused1", _ctypes.c_double),
        ("unused2", _ctypes.c_double),
        ("unused3", _ctypes.c_double),
    ]


class _SectorStarts(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("sector1", _ctypes.c_float), ("sector2", _ctypes.c_float),
                ("sector3", _ctypes.c_float)]


class _Flags(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("yellow", _ctypes.c_int32),
        ("yellow_caused_it", _ctypes.c_int32),
        ("yellow_overtake", _ctypes.c_int32),
        ("yellow_positions_gained", _ctypes.c_int32),
        ("sector_yellow", _ctypes.c_int32 * 3),
        ("closest_yellow_distance_into_track", _ctypes.c_float),
        ("blue", _ctypes.c_int32),
        ("black", _ctypes.c_int32),
        ("green", _ctypes.c_int32),
        ("checkered", _ctypes.c_int32),
        ("white", _ctypes.c_int32),
        ("black_and_white", _ctypes.c_int32),
    ]


class _CutTrackPenalties(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("drive_through", _ctypes.c_float), ("stop_and_go", _ctypes.c_float),
                ("pit_stop", _ctypes.c_float), ("time_deduction", _ctypes.c_float),
                ("slow_down", _ctypes.c_float)]


class _DriverInfo(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("name", _ctypes.c_char * 64),
        ("car_number", _ctypes.c_int32),
        ("class_id", _ctypes.c_int32),
        ("model_id", _ctypes.c_int32),
        ("team_id", _ctypes.c_int32),
        ("livery_id", _ctypes.c_int32),
        ("manufacturer_id", _ctypes.c_int32),
        ("user_id", _ctypes.c_int32),
        ("slot_id", _ctypes.c_int32),
        ("class_performance_index", _ctypes.c_int32),
        ("engine_type", _ctypes.c_int32),
        ("car_width", _ctypes.c_float),
        ("car_length", _ctypes.c_float),
        ("rating", _ctypes.c_float),
        ("reputation", _ctypes.c_float),
        ("unused1", _ctypes.c_float),
        ("unused2", _ctypes.c_float),
    ]


class _AidSettings(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("abs", _ctypes.c_int32), ("tc", _ctypes.c_int32), ("esp", _ctypes.c_int32),
                ("countersteer", _ctypes.c_int32), ("cornering", _ctypes.c_int32)]


class _DRS(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("equipped", _ctypes.c_int32), ("available", _ctypes.c_int32),
                ("num_activations_left", _ctypes.c_int32), ("engaged", _ctypes.c_int32)]


class _PushToPass(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("available", _ctypes.c_int32), ("engaged", _ctypes.c_int32),
                ("amount_left", _ctypes.c_int32), ("engaged_time_left", _ctypes.c_float),
                ("wait_time_left", _ctypes.c_float)]


class _TireTemp(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("current_temp", _ctypes.c_float * 3), ("optimal_temp", _ctypes.c_float),
                ("cold_temp", _ctypes.c_float), ("hot_temp", _ctypes.c_float)]


class _BrakeTemp(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("current_temp", _ctypes.c_float), ("optimal_temp", _ctypes.c_float),
                ("cold_temp", _ctypes.c_float), ("hot_temp", _ctypes.c_float)]


class _CarDamage(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [("engine", _ctypes.c_float), ("transmission", _ctypes.c_float),
                ("aerodynamics", _ctypes.c_float), ("suspension", _ctypes.c_float),
                ("unused1", _ctypes.c_float), ("unused2", _ctypes.c_float)]


class R3EShared(_ctypes.Structure):
    """Vorspann von r3e_shared bis einschließlich tire_load (pack 1).

    Die Felder ab num_cars (Fahrerliste, Startprozedur 3.6) fehlen
    bewusst: Wir lesen nur den Teil vor der Liste; die Offsets des
    Vorspanns bleiben dadurch exakt.
    """
    _pack_ = 1
    _fields_ = [
        ("version_major", _ctypes.c_int32),
        ("version_minor", _ctypes.c_int32),
        ("all_drivers_offset", _ctypes.c_int32),
        ("driver_data_size", _ctypes.c_int32),
        ("game_mode", _ctypes.c_int32),
        ("game_paused", _ctypes.c_int32),
        ("game_in_menus", _ctypes.c_int32),
        ("game_in_replay", _ctypes.c_int32),
        ("game_using_vr", _ctypes.c_int32),
        ("game_player_in_garage", _ctypes.c_int32),
        ("player", R3EPlayerData),
        ("track_name", _ctypes.c_char * 64),
        ("layout_name", _ctypes.c_char * 64),
        ("track_id", _ctypes.c_int32),
        ("layout_id", _ctypes.c_int32),
        ("layout_length", _ctypes.c_float),
        ("sector_start_factors", _SectorStarts),
        ("race_session_laps", _ctypes.c_int32 * 3),
        ("race_session_minutes", _ctypes.c_int32 * 3),
        ("event_index", _ctypes.c_int32),
        ("session_type", _ctypes.c_int32),
        ("session_iteration", _ctypes.c_int32),
        ("session_length_format", _ctypes.c_int32),
        ("session_pit_speed_limit", _ctypes.c_float),
        ("session_phase", _ctypes.c_int32),
        ("start_lights", _ctypes.c_int32),
        ("tire_wear_active", _ctypes.c_int32),
        ("fuel_use_active", _ctypes.c_int32),
        ("number_of_laps", _ctypes.c_int32),
        ("session_time_duration", _ctypes.c_float),
        ("session_time_remaining", _ctypes.c_float),
        ("max_incident_points", _ctypes.c_int32),
        ("start_mode", _ctypes.c_int32),
        ("start_group_count", _ctypes.c_int32),
        ("pit_window_status", _ctypes.c_int32),
        ("pit_window_start", _ctypes.c_int32),
        ("pit_window_end", _ctypes.c_int32),
        ("in_pitlane", _ctypes.c_int32),
        ("pit_menu_selection", _ctypes.c_int32),
        ("pit_menu_state", _ctypes.c_int32 * 12),
        ("pit_state", _ctypes.c_int32),
        ("pit_total_duration", _ctypes.c_float),
        ("pit_elapsed_time", _ctypes.c_float),
        ("pit_action", _ctypes.c_int32),
        ("num_pitstops", _ctypes.c_int32),
        ("pit_min_duration_total", _ctypes.c_float),
        ("pit_min_duration_left", _ctypes.c_float),
        ("flags", _Flags),
        ("position", _ctypes.c_int32),
        ("position_class", _ctypes.c_int32),
        ("finish_status", _ctypes.c_int32),
        ("cut_track_warnings", _ctypes.c_int32),
        ("penalties", _CutTrackPenalties),
        ("num_penalties", _ctypes.c_int32),
        ("completed_laps", _ctypes.c_int32),
        ("current_lap_valid", _ctypes.c_int32),
        ("track_sector", _ctypes.c_int32),
        ("lap_distance", _ctypes.c_float),
        ("lap_distance_fraction", _ctypes.c_float),
        ("lap_time_best_leader", _ctypes.c_float),
        ("lap_time_best_leader_class", _ctypes.c_float),
        ("session_best_lap_sector_times", _ctypes.c_float * 3),
        ("lap_time_best_self", _ctypes.c_float),
        ("sector_time_best_self", _ctypes.c_float * 3),
        ("lap_time_previous_self", _ctypes.c_float),
        ("sector_time_previous_self", _ctypes.c_float * 3),
        ("lap_time_current_self", _ctypes.c_float),
        ("sector_time_current_self", _ctypes.c_float * 3),
        ("lap_time_delta_leader", _ctypes.c_float),
        ("lap_time_delta_leader_class", _ctypes.c_float),
        ("time_delta_front", _ctypes.c_float),
        ("time_delta_behind", _ctypes.c_float),
        ("time_delta_best_self", _ctypes.c_float),
        ("best_individual_sector_time_self", _ctypes.c_float * 3),
        ("best_individual_sector_time_leader", _ctypes.c_float * 3),
        ("best_individual_sector_time_leader_class", _ctypes.c_float * 3),
        ("incident_points", _ctypes.c_int32),
        ("lap_valid_state", _ctypes.c_int32),
        ("prev_lap_valid", _ctypes.c_int32),
        ("discharge_rate", _ctypes.c_float),
        ("brake_regen", _ctypes.c_float),
        ("unused1", _ctypes.c_float),
        ("vehicle_info", _DriverInfo),
        ("player_name", _ctypes.c_char * 64),
        ("control_type", _ctypes.c_int32),
        ("car_speed", _ctypes.c_float),
        ("engine_rps", _ctypes.c_float),
        ("max_engine_rps", _ctypes.c_float),
        ("upshift_rps", _ctypes.c_float),
        ("gear", _ctypes.c_int32),
        ("num_gears", _ctypes.c_int32),
        ("car_cg_location", _Vec3F32),
        ("car_orientation", _OriF32),
        ("local_acceleration", _Vec3F32),
        ("total_mass", _ctypes.c_float),
        ("fuel_left", _ctypes.c_float),
        ("fuel_capacity", _ctypes.c_float),
        ("fuel_per_lap", _ctypes.c_float),
        ("virtual_energy_left", _ctypes.c_float),
        ("virtual_energy_capacity", _ctypes.c_float),
        ("virtual_energy_per_lap", _ctypes.c_float),
        ("engine_temp", _ctypes.c_float),
        ("engine_oil_temp", _ctypes.c_float),
        ("fuel_pressure", _ctypes.c_float),
        ("engine_oil_pressure", _ctypes.c_float),
        ("turbo_pressure", _ctypes.c_float),
        ("throttle", _ctypes.c_float),
        ("throttle_raw", _ctypes.c_float),
        ("brake", _ctypes.c_float),
        ("brake_raw", _ctypes.c_float),
        ("clutch", _ctypes.c_float),
        ("clutch_raw", _ctypes.c_float),
        ("steer_input_raw", _ctypes.c_float),
        ("steer_lock_degrees", _ctypes.c_int32),
        ("steer_wheel_range_degrees", _ctypes.c_int32),
        ("aid_settings", _AidSettings),
        ("drs", _DRS),
        ("pit_limiter", _ctypes.c_int32),
        ("push_to_pass", _PushToPass),
        ("brake_bias", _ctypes.c_float),
        ("drs_num_activations_total", _ctypes.c_int32),
        ("ptp_num_activations_total", _ctypes.c_int32),
        ("battery_soc", _ctypes.c_float),
        ("water_left", _ctypes.c_float),
        ("abs_setting", _ctypes.c_int32),
        ("headlights", _ctypes.c_int32),
        ("steer_wheel_max_rotation", _ctypes.c_int32),
        ("tire_type", _ctypes.c_int32),
        ("tire_rps", _ctypes.c_float * TIRE_INDEX_MAX),
        ("tire_speed", _ctypes.c_float * TIRE_INDEX_MAX),
        ("tire_grip", _ctypes.c_float * TIRE_INDEX_MAX),
        ("tire_wear", _ctypes.c_float * TIRE_INDEX_MAX),
        ("tire_flatspot", _ctypes.c_int32 * TIRE_INDEX_MAX),
        ("tire_pressure", _ctypes.c_float * TIRE_INDEX_MAX),
        ("tire_dirt", _ctypes.c_float * TIRE_INDEX_MAX),
        ("tire_temp", _TireTemp * TIRE_INDEX_MAX),
        ("tire_type_front", _ctypes.c_int32),
        ("tire_type_rear", _ctypes.c_int32),
        ("tire_subtype_front", _ctypes.c_int32),
        ("tire_subtype_rear", _ctypes.c_int32),
        ("brake_temp", _BrakeTemp * TIRE_INDEX_MAX),
        ("brake_pressure", _ctypes.c_float * TIRE_INDEX_MAX),
        ("traction_control_setting", _ctypes.c_int32),
        ("engine_map_setting", _ctypes.c_int32),
        ("engine_brake_setting", _ctypes.c_int32),
        ("traction_control_percent", _ctypes.c_float),
        ("tire_on_mtrl", _ctypes.c_int32 * TIRE_INDEX_MAX),
        ("tire_load", _ctypes.c_float * TIRE_INDEX_MAX),
        # Rest (num_cars, Fahrerliste, Startprozedur 3.6) bewusst weggelassen.
    ]


def _text(raw):
    try:
        return raw.decode("utf-8", errors="replace").rstrip("\x00 ").strip()
    except Exception:
        return ""


class TelemetryFrame:
    """Momentaufnahme eines Lesevorgangs — nur ausgefüllte Werte als
    plain Attribute, von der Recorder-Schicht direkt weiterverwendbar."""

    __slots__ = ("running", "in_menus", "paused", "session_type", "in_pitlane",
                 "completed_laps", "lap_time", "speed_kmh", "throttle", "brake",
                 "steer_deg", "g_lat", "g_long", "susp_travel", "tyre_temp",
                 "tyre_press", "brake_temp", "brake_bias_pct", "track", "layout",
                 "vehicle", "version")

    def __init__(self, shared):
        self.running = (shared.version_major == R3E_VERSION_MAJOR
                        and shared.game_mode != GAMEMODE_UNAVAILABLE)
        self.version = (shared.version_major, shared.version_minor)
        self.in_menus = bool(shared.game_in_menus)
        self.paused = bool(shared.game_paused)
        self.session_type = shared.session_type
        self.in_pitlane = shared.in_pitlane == 1
        self.completed_laps = shared.completed_laps
        self.lap_time = None if shared.lap_time_current_self <= 0 else shared.lap_time_current_self
        self.speed_kmh = shared.car_speed * 3.6
        self.throttle = shared.throttle
        self.brake = shared.brake
        lock = shared.steer_lock_degrees if shared.steer_lock_degrees > 0 else 0.0
        self.steer_deg = shared.steer_input_raw * lock
        # Fahrzeug-lokal: +X = links, +Z = hinten (r3e.h). g_lat: links positiv,
        # g_long: vorwärts positiv (Bremsen negativ) wie in MoTeC-GUIDEs.
        self.g_lat = shared.player.local_g_force.x
        self.g_long = -shared.player.local_g_force.z
        self.susp_travel = tuple(shared.player.suspension_deflection[i] * 1000.0
                                 for i in range(TIRE_INDEX_MAX))  # m -> mm
        self.tyre_temp = tuple(
            sum(shared.tire_temp[i].current_temp[j] for j in range(3)) / 3.0
            for i in range(TIRE_INDEX_MAX))
        self.tyre_press = tuple(
            (shared.tire_pressure[i] / 100.0) if shared.tire_pressure[i] >= 0 else None
            for i in range(TIRE_INDEX_MAX))  # kPa -> bar
        self.brake_temp = tuple(shared.brake_temp[i].current_temp
                                for i in range(TIRE_INDEX_MAX))
        self.brake_bias_pct = (shared.brake_bias * 100.0
                               if shared.brake_bias >= 0 else None)
        self.track = _text(shared.track_name)
        self.layout = _text(shared.layout_name) or self.track
        self.vehicle = _text(shared.vehicle_info.name)


class R3EMemory:
    """Anbindung an "$R3E": echtes mmap unter Windows, injizierbarer
    Byte-Puffer für Tests (non-Windows/CI)."""

    def __init__(self, mem=None, name=R3E_SHARED_MEMORY_NAME):
        self._name = name
        self._map = None
        self._mem = mem
        self.tag_used = None
        if mem is None:
            self._open()

    @classmethod
    def try_open(cls, wait_seconds=0.0):
        """Liefert eine R3EMemory oder None, wenn der Shared Memory fehlt."""
        if os.name != "nt":
            return cls(mem=b"", )
        deadline = time.monotonic() + max(0.0, wait_seconds)
        while True:
            try:
                return cls()
            except (FileNotFoundError, OSError):
                if time.monotonic() >= deadline:
                    return None
                time.sleep(0.25)

    def _open(self):
        if os.name != "nt":
            raise OSError("R3E-Shared-Memory ist nur unter Windows verfügbar")
        # 0.9.3: Drei Namensräume probieren. Manche Windows-Setups (Spiel
        # oder Steam erhöht gestartet, andere Nutzersitzung) legen das
        # Mapping statt in der lokalen Sitzung im globalen Namensraum ab.
        for tag in (f"Local\\{self._name}", self._name, f"Global\\{self._name}"):
            try:
                self._map = mmap.mmap(0, 0, tag)
                self._size = min(len(self._map), 4 * 1024 * 1024)
                self.tag_used = tag
                return
            except (FileNotFoundError, OSError):
                continue
        raise FileNotFoundError(f'RaceRoom-Shared-Memory "{self._name}" nicht gefunden')

    def is_real(self):
        return self._map is not None

    def read_frame(self):
        """Liest den Datensatz ein (Kopie) und liefert einen TelemetryFrame."""
        if self._map is not None:
            buf = self._map[: _ctypes.sizeof(R3EShared)]
        elif self._mem is not None:
            buf = bytes(self._mem)[: (len(self._mem) if self._mem else 0)]
            if len(buf) < _ctypes.sizeof(R3EShared):
                buf = buf + b"\x00" * (_ctypes.sizeof(R3EShared) - len(buf))
        else:
            buf = b"\x00" * _ctypes.sizeof(R3EShared)
        shared = _ctypes.cast(_ctypes.create_string_buffer(buf),
                              _ctypes.POINTER(R3EShared)).contents
        return TelemetryFrame(shared)

    def close(self):
        if self._map is not None:
            try:
                self._map.close()
            except Exception:
                pass
            self._map = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    @staticmethod
    def build_buffer(mutate=None):
        """Testhelfer: erzeugt einen echten Puffer aus den ctypes-Strukturen."""
        obj = R3EShared()
        obj.version_major = R3E_VERSION_MAJOR
        obj.version_minor = R3E_VERSION_MINOR
        if mutate:
            mutate(obj)
        return bytes(memoryview(obj).cast("B"))
    

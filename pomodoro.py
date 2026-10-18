# -*- coding: utf-8 -*-
import time

class PomodoroTimer:
    def __init__(self, work_min=25, break_min=5, long_break_min=15, long_break_interval=4):
        """
        Quản lý chu kỳ Pomodoro chuẩn quốc tế (Francesco Cirillo Technique):
        - work_min: Thời gian học tập trung (25 phút)
        - break_min: Thời gian nghỉ ngắn (5 phút)
        - long_break_min: Thời gian nghỉ dài sau 4 chu kỳ (15 phút)
        - long_break_interval: Số chu kỳ trước khi được nghỉ dài (4 chu kỳ)
        """
        self.work_sec = work_min * 60
        self.break_sec = break_min * 60
        self.long_break_sec = long_break_min * 60
        self.long_break_interval = long_break_interval

        self.state = "WORK" # "WORK" hoặc "BREAK"
        self.is_long_break = False
        self.current_break_target = self.break_sec
        self.is_active = True
        self.state_start_time = time.time()
        self.pause_start_time = 0.0
        self.completed_cycles = 0

    def update(self):
        """
        Cập nhật đồng hồ Pomodoro.
        Trả về: (state, time_left_sec, event, is_long_break)
        - event: 'BREAK_START', 'LONG_BREAK_START', 'BREAK_END', hoặc None
        """
        target_sec = self.work_sec if self.state == "WORK" else self.current_break_target

        if not self.is_active:
            elapsed = self.pause_start_time - self.state_start_time
            return self.state, max(0, int(target_sec - elapsed)), None

        now = time.time()
        elapsed = now - self.state_start_time
        event = None

        if self.state == "WORK":
            time_left = max(0, self.work_sec - elapsed)
            if time_left == 0:
                self.state = "BREAK"
                self.state_start_time = now
                self.completed_cycles += 1

                # Mỗi 4 chu kỳ học liên tục -> Thưởng nghỉ dài 15 phút
                if self.completed_cycles % self.long_break_interval == 0:
                    self.is_long_break = True
                    self.current_break_target = self.long_break_sec
                    event = "LONG_BREAK_START"
                else:
                    self.is_long_break = False
                    self.current_break_target = self.break_sec
                    event = "BREAK_START"

                time_left = self.current_break_target
        else: # BREAK
            time_left = max(0, self.current_break_target - elapsed)
            if time_left == 0:
                self.state = "WORK"
                self.is_long_break = False
                self.state_start_time = now
                event = "BREAK_END"
                time_left = self.work_sec

        return self.state, int(time_left), event

    def toggle(self):
        now = time.time()
        if self.is_active:
            self.pause_start_time = now
            self.is_active = False
        else:
            if self.pause_start_time > 0:
                self.state_start_time += (now - self.pause_start_time)
            self.is_active = True
        return self.is_active

    def reset(self):
        self.state = "WORK"
        self.is_long_break = False
        self.current_break_target = self.break_sec
        now = time.time()
        self.state_start_time = now
        self.pause_start_time = now if not self.is_active else 0.0
        self.completed_cycles = 0

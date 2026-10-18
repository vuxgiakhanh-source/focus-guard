import time

class PomodoroTimer:
    def __init__(self, work_min=25, break_min=5):
        """
        Quản lý chu kỳ Pomodoro:
        - work_min: Thời gian tập trung (mặc định 25 phút)
        - break_min: Thời gian giải lao (mặc định 5 phút)
        """
        self.work_sec = work_min * 60
        self.break_sec = break_min * 60

        self.state = "WORK" # "WORK" hoặc "BREAK"
        self.is_active = True
        self.state_start_time = time.time()
        self.completed_cycles = 0

    def update(self):
        """
        Cập nhật đồng hồ Pomodoro.
        Trả về: (state, time_left_sec, event)
        - event: 'BREAK_START' (khi vừa hết giờ học), 'BREAK_END' (khi vừa hết giờ nghỉ), hoặc None
        """
        if not self.is_active:
            return self.state, 0, None

        now = time.time()
        elapsed = now - self.state_start_time
        event = None

        if self.state == "WORK":
            time_left = max(0, self.work_sec - elapsed)
            if time_left == 0:
                self.state = "BREAK"
                self.state_start_time = now
                self.completed_cycles += 1
                event = "BREAK_START"
                time_left = self.break_sec
        else: # BREAK
            time_left = max(0, self.break_sec - elapsed)
            if time_left == 0:
                self.state = "WORK"
                self.state_start_time = now
                event = "BREAK_END"
                time_left = self.work_sec

        return self.state, int(time_left), event

    def toggle(self):
        self.is_active = not self.is_active
        return self.is_active

    def reset(self):
        self.state = "WORK"
        self.state_start_time = time.time()

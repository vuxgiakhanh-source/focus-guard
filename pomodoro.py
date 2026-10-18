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
        self.pause_start_time = 0.0
        self.completed_cycles = 0

    def update(self):
        """
        Cập nhật đồng hồ Pomodoro.
        Trả về: (state, time_left_sec, event)
        - event: 'BREAK_START' (khi vừa hết giờ học), 'BREAK_END' (khi vừa hết giờ nghỉ), hoặc None
        """
        if not self.is_active:
            target_sec = self.work_sec if self.state == "WORK" else self.break_sec
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
        now = time.time()
        if self.is_active:
            # Chuyển sang tạm dừng: lưu lại mốc thời gian tạm dừng
            self.pause_start_time = now
            self.is_active = False
        else:
            # Tiếp tục: bù trừ chính xác khoảng thời gian vừa tạm dừng
            if self.pause_start_time > 0:
                self.state_start_time += (now - self.pause_start_time)
            self.is_active = True
        return self.is_active

    def reset(self):
        self.state = "WORK"
        self.state_start_time = time.time()
        self.pause_start_time = 0.0

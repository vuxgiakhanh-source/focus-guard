# -*- coding: utf-8 -*-
import os
import json
import math
import tempfile
import time
import sys
from datetime import datetime, timedelta

# Đảm bảo in tiếng Việt chuẩn trên Windows console
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "focus_history.json")

class SessionHistoryManager:
    """Quản lý lưu trữ và phân tích lịch sử các phiên học tập FocusGuard"""
    def __init__(self, history_file=None, daily_goal_mins=120):
        if history_file is None:
            history_file = HISTORY_FILE
        elif not os.path.isabs(history_file):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            history_file = os.path.join(base_dir, history_file)
        self.history_file = history_file
        self.daily_goal_mins = daily_goal_mins
        self.history_data = self._load_history()

    def _load_history(self):
        default = {"sessions": [], "created_at": datetime.now().isoformat()}
        if not os.path.exists(self.history_file):
            return default

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or not isinstance(data.get("sessions", []), list):
                raise ValueError("cấu trúc lịch sử không hợp lệ")

            valid_sessions = []
            numeric_fields = (
                "duration_minutes", "duration_seconds", "focus_score",
                "phone_events", "web_events", "distraction_events",
                "drowsy_events", "pomodoro_cycles"
            )
            for raw in data.get("sessions", []):
                if not isinstance(raw, dict):
                    continue
                date_value = raw.get("date")
                try:
                    datetime.strptime(date_value, "%Y-%m-%d")
                except (TypeError, ValueError):
                    continue
                entry = dict(raw)
                valid = True
                for field in numeric_fields:
                    default_value = 100.0 if field == "focus_score" else 0
                    value = entry.get(field, default_value)
                    try:
                        value = float(value)
                    except (TypeError, ValueError, OverflowError):
                        valid = False
                        break
                    if not math.isfinite(value):
                        valid = False
                        break
                    entry[field] = value
                if valid:
                    entry.setdefault("focus_score", 100.0)
                    valid_sessions.append(entry)

            result = dict(data)
            result["sessions"] = valid_sessions
            result.setdefault("created_at", default["created_at"])
            return result
        except (OSError, json.JSONDecodeError, ValueError) as e:
            print(f"[-] Lịch sử học tập lỗi/không đọc được; bắt đầu danh sách mới: {e}")
            return default

    def _save_history(self):
        temp_path = None
        try:
            target_path = os.path.abspath(self.history_file)
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(prefix=".focus_history_", suffix=".tmp", dir=target_dir)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, target_path)
            return True
        except (OSError, TypeError, ValueError) as e:
            print(f"[-] Không thể lưu lịch sử học tập: {e}")
            return False
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def save_session(self, start_time, end_time, focus_score, phone_events, distraction_events, drowsy_events, pomo_cycles, web_events=0, active_study_seconds=None):
        """Lưu lại một phiên học hoàn chỉnh"""
        duration_sec = int(end_time - start_time)
        if duration_sec < 45:
            # Bỏ qua phiên quá ngắn (< 45 giây) để không làm loãng dữ liệu lịch sử và streak
            return None

        study_sec = int(active_study_seconds) if active_study_seconds is not None else duration_sec
        mins = round(study_sec / 60.0, 1)
        start_dt = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
        end_dt = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")
        date_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d")

        session_entry = {
            "id": len(self.history_data.get("sessions", [])) + 1,
            "date": date_str,
            "start_time": start_dt,
            "end_time": end_dt,
            "duration_minutes": mins,
            "duration_seconds": duration_sec,
            "active_study_seconds": study_sec,
            "focus_score": round(focus_score, 1),
            "phone_events": phone_events,
            "web_events": web_events,
            "distraction_events": distraction_events,
            "drowsy_events": drowsy_events,
            "pomodoro_cycles": pomo_cycles
        }

        if "sessions" not in self.history_data:
            self.history_data["sessions"] = []
        self.history_data["sessions"].append(session_entry)
        self._save_history()
        return session_entry

    def calculate_streak(self):
        """Tính chuỗi ngày học tập liên tục (Daily Study Streak)"""
        sessions = self.history_data.get("sessions", [])
        if not sessions:
            return 0, 0

        # Chỉ tính những ngày có tổng thời lượng học tập tích lũy >= 120 giây (2 phút)
        daily_study_seconds = {}
        for s in sessions:
            d = s.get("date")
            if d:
                dur = float(s.get("active_study_seconds", s.get("duration_seconds", s.get("duration_minutes", 0) * 60)))
                daily_study_seconds[d] = daily_study_seconds.get(d, 0.0) + dur

        qualifying_dates = sorted([d for d, sec in daily_study_seconds.items() if sec >= 120.0])
        if not qualifying_dates:
            return 0, 0

        date_objs = [datetime.strptime(d, "%Y-%m-%d").date() for d in qualifying_dates]
        
        # Tính chuỗi hiện tại
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        current_streak = 0
        check_date = today if (today in date_objs) else (yesterday if yesterday in date_objs else None)
        
        if check_date is not None:
            while check_date in date_objs:
                current_streak += 1
                check_date -= timedelta(days=1)

        # Tính chuỗi kỷ lục (Best Streak)
        max_streak = 0
        temp_streak = 1
        for i in range(1, len(date_objs)):
            if date_objs[i] == date_objs[i-1] + timedelta(days=1):
                temp_streak += 1
            else:
                max_streak = max(max_streak, temp_streak)
                temp_streak = 1
        max_streak = max(max_streak, temp_streak) if date_objs else 0

        return current_streak, max_streak

    def get_summary_stats(self):
        """Tính toán thống kê tổng quan toàn bộ, hôm nay và chuỗi học tập"""
        sessions = self.history_data.get("sessions", [])
        current_streak, best_streak = self.calculate_streak()

        if not sessions:
            return {
                "total_sessions": 0,
                "total_minutes": 0.0,
                "avg_score": 100.0,
                "today_minutes": 0.0,
                "today_avg_score": 100.0,
                "today_sessions": 0,
                "today_goal_pct": 0.0,
                "current_streak": 0,
                "best_streak": 0,
                "total_phone": 0,
                "total_distraction": 0,
                "total_drowsy": 0,
                "total_pomodoro": 0
            }

        today_str = datetime.now().strftime("%Y-%m-%d")
        total_mins = sum(s.get("duration_minutes", 0) for s in sessions)

        # Điểm trung bình có trọng số theo thời lượng (Duration-weighted average score)
        # sum(score * duration) / sum(duration)
        total_weight_sec = sum(max(1.0, float(s.get("active_study_seconds", s.get("duration_seconds", s.get("duration_minutes", 0) * 60)))) for s in sessions)
        if total_weight_sec > 0:
            avg_score = round(sum(float(s.get("focus_score", 100)) * max(1.0, float(s.get("active_study_seconds", s.get("duration_seconds", s.get("duration_minutes", 0) * 60)))) for s in sessions) / total_weight_sec, 1)
        else:
            avg_score = 100.0

        today_sessions = [s for s in sessions if s.get("date") == today_str]
        today_mins = sum(s.get("duration_minutes", 0) for s in today_sessions)
        today_weight_sec = sum(max(1.0, float(s.get("active_study_seconds", s.get("duration_seconds", s.get("duration_minutes", 0) * 60)))) for s in today_sessions)
        if today_weight_sec > 0:
            today_avg = round(sum(float(s.get("focus_score", 100)) * max(1.0, float(s.get("active_study_seconds", s.get("duration_seconds", s.get("duration_minutes", 0) * 60)))) for s in today_sessions) / today_weight_sec, 1)
        else:
            today_avg = 100.0
        today_goal_pct = min(100.0, round((today_mins / max(1, self.daily_goal_mins)) * 100.0, 1))

        total_phone = sum(s.get("phone_events", 0) for s in sessions)
        total_dist = sum(s.get("distraction_events", 0) for s in sessions)
        total_drowsy = sum(s.get("drowsy_events", 0) for s in sessions)
        total_pomo = sum(s.get("pomodoro_cycles", 0) for s in sessions)

        return {
            "total_sessions": len(sessions),
            "total_minutes": round(total_mins, 1),
            "avg_score": avg_score,
            "today_sessions": len(today_sessions),
            "today_minutes": round(today_mins, 1),
            "today_avg_score": today_avg,
            "today_goal_pct": today_goal_pct,
            "current_streak": current_streak,
            "best_streak": best_streak,
            "total_phone": total_phone,
            "total_distraction": total_dist,
            "total_drowsy": total_drowsy,
            "total_pomodoro": total_pomo
        }

    def print_report(self, current_session=None):
        """In bảng báo cáo tổng kết đẹp mắt ra terminal"""
        stats = self.get_summary_stats()
        print("\n" + "=" * 65)
        print("          📊 BÁO CÁO TỔNG KẾT HỌC TẬP & NĂNG SUẤT")
        print("=" * 65)

        if current_session:
            print(f" 🎯 PHIÊN VỪA HOÀN THÀNH:")
            print(f"    - Thời lượng        : {current_session['duration_minutes']} phút ({current_session['duration_seconds']}s)")
            print(f"    - ĐIỂM TẬP TRUNG    : {current_session['focus_score']}%")
            print(f"    - Cầm điện thoại    : {current_session['phone_events']} lần")
            print(f"    - Lướt FB / YouTube : {current_session.get('web_events', 0)} lần")
            print(f"    - Quay mặt ra ngoài : {current_session['distraction_events']} lần")
            print(f"    - Buồn ngủ / ngủ gật: {current_session['drowsy_events']} lần")
            print(f"    - Chu kỳ Pomodoro   : {current_session['pomodoro_cycles']} chu kỳ")
            print("-" * 65)

        print(f" 📈 TỔNG KẾT HÔM NAY ({datetime.now().strftime('%d/%m/%Y')}):")
        print(f"    - Số phiên đã học   : {stats['today_sessions']} phiên")
        print(f"    - Tổng thời gian    : {stats['today_minutes']} phút ({round(stats['today_minutes']/60.0, 1)} giờ)")
        print(f"    - Mục tiêu ngày     : {stats['today_goal_pct']}% / {self.daily_goal_mins} phút")
        print(f"    - Điểm tập trung TB : {stats['today_avg_score']}%")
        print(f"    - Chuỗi học liên tục: 🔥 {stats['current_streak']} ngày (Kỷ lục: {stats['best_streak']} ngày)")
        print("-" * 65)
        print(f" 🏆 TỔNG LỊCH SỬ TÍCH LŨY:")
        print(f"    - Tổng thời gian học: {stats['total_minutes']} phút ({round(stats['total_minutes']/60.0, 1)} giờ)")
        print(f"    - Tổng số chu kỳ Pomodoro: {stats['total_pomodoro']}")
        print(f"    - Dữ liệu đã lưu tại: {os.path.abspath(self.history_file)}")
        print("=" * 65 + "\n")

# -*- coding: utf-8 -*-
import os
import json
import time
import sys
from datetime import datetime

# Đảm bảo in tiếng Việt chuẩn trên Windows console
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HISTORY_FILE = "focus_history.json"

class SessionHistoryManager:
    """Quản lý lưu trữ và phân tích lịch sử các phiên học tập FocusGuard"""
    def __init__(self, history_file=HISTORY_FILE):
        self.history_file = history_file
        self.history_data = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions": [], "created_at": datetime.now().isoformat()}

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[-] Không thể lưu lịch sử học tập: {e}")

    def save_session(self, start_time, end_time, focus_score, phone_events, distraction_events, drowsy_events, pomo_cycles, web_events=0):
        """Lưu lại một phiên học hoàn chỉnh"""
        duration_sec = int(end_time - start_time)
        if duration_sec < 10:
            # Bỏ qua phiên quá ngắn (< 10 giây)
            return None

        mins = round(duration_sec / 60.0, 1)
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

    def get_summary_stats(self):
        """Tính toán thống kê tổng quan toàn bộ và hôm nay"""
        sessions = self.history_data.get("sessions", [])
        if not sessions:
            return {
                "total_sessions": 0,
                "total_minutes": 0.0,
                "avg_score": 100.0,
                "today_minutes": 0.0,
                "today_avg_score": 100.0,
                "today_sessions": 0,
                "total_phone": 0,
                "total_distraction": 0,
                "total_drowsy": 0,
                "total_pomodoro": 0
            }

        today_str = datetime.now().strftime("%Y-%m-%d")
        total_mins = sum(s.get("duration_minutes", 0) for s in sessions)
        total_scores = [s.get("focus_score", 100) for s in sessions]
        avg_score = round(sum(total_scores) / len(total_scores), 1) if total_scores else 100.0

        today_sessions = [s for s in sessions if s.get("date") == today_str]
        today_mins = sum(s.get("duration_minutes", 0) for s in today_sessions)
        today_scores = [s.get("focus_score", 100) for s in today_sessions]
        today_avg = round(sum(today_scores) / len(today_scores), 1) if today_scores else 100.0

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
        print(f"    - Điểm tập trung TB : {stats['today_avg_score']}%")
        print("-" * 65)
        print(f" 🏆 TỔNG LỊCH SỬ TÍCH LŨY:")
        print(f"    - Tổng thời gian học: {stats['total_minutes']} phút ({round(stats['total_minutes']/60.0, 1)} giờ)")
        print(f"    - Tổng số chu kỳ Pomodoro: {stats['total_pomodoro']}")
        print(f"    - Dữ liệu đã lưu tại: {os.path.abspath(self.history_file)}")
        print("=" * 65 + "\n")

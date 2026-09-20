"""실제 데이터가 있는 날짜만 버튼으로 골라서 실행하는 간단한 GUI (tkinter만 사용).

주의: 백그라운드 스레드에서는 절대 Tk 위젯을 직접 건드리지 않는다.
스레드는 큐에 문자열/완료신호만 넣고, Tk 쪽 갱신은 메인 스레드가
after()로 큐를 주기적으로 비우면서 처리한다 (tkinter는 다른 스레드에서
위젯을 직접 조작하면 불안정해질 수 있음).
"""

from __future__ import annotations

import queue
import sys
import threading
from datetime import date
from pathlib import Path
from tkinter import Tk, StringVar, END, DISABLED, NORMAL
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import build_report
import updater

_DONE = object()
POLL_INTERVAL_MS = 100
WEEKDAY_KOR = ["월", "화", "수", "목", "금", "토", "일"]


class _QueueStream:
    """print() 출력을 큐에 담기만 하는 스레드-세이프 스트림 (Tk를 건드리지 않음)."""

    def __init__(self, q: "queue.Queue"):
        self._queue = q

    def write(self, data: str) -> None:
        if data:
            self._queue.put(data)

    def flush(self) -> None:
        pass


BG = "#f0f0f0"
FG = "#000000"


def _format_date_label(d: date) -> str:
    return f"{d.month}/{d.day} ({WEEKDAY_KOR[d.weekday()]})"


class App:
    def __init__(self, root: Tk):
        self.root = root
        root.title("종가 크롤러")
        root.geometry("680x460")
        root.minsize(680, 380)
        root.configure(bg=BG)

        # macOS 시스템 Python에 딸려오는 구버전 Tk(8.5)는 다크모드에서
        # 위젯이 배경과 같은 색으로 그려져 안 보이는 버그가 있다.
        # OS 테마를 따라가지 않는 'clam' 테마 + 명시적 색 지정으로 우회한다.
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:  # noqa: BLE001
            pass
        style.configure(".", background=BG, foreground=FG)
        style.configure("TButton", background="#e0e0e0", foreground=FG)

        self.log_queue: "queue.Queue" = queue.Queue()
        self.date_queue: "queue.Queue" = queue.Queue()
        self.update_queue: "queue.Queue" = queue.Queue()
        self._last_output_dir: Path | None = None
        self._date_buttons: list[ttk.Button] = []

        date_frame = ttk.Frame(root, padding=10)
        date_frame.pack(fill="x")

        ttk.Label(date_frame, text="조회할 날짜 (최근 거래일만 선택 가능):").pack(side="left")

        self.refresh_button = ttk.Button(date_frame, text="새로고침", command=self._start_date_fetch)
        self.refresh_button.pack(side="right")

        self.update_button = ttk.Button(date_frame, text="업데이트 확인", command=self._start_update_check)
        self.update_button.pack(side="right", padx=(0, 6))

        self.date_buttons_frame = ttk.Frame(root, padding=(10, 0))
        self.date_buttons_frame.pack(fill="x")

        self.status_var = StringVar(value="사용 가능한 날짜 불러오는 중...")
        ttk.Label(root, textvariable=self.status_var, padding=(10, 6)).pack(fill="x")

        self.log_widget = ScrolledText(root, state=DISABLED, height=16, bg="#ffffff", fg="#000000", insertbackground="#000000")
        self.log_widget.pack(fill="both", expand=True, padx=10, pady=10)

        self.open_output_button = ttk.Button(root, text="결과 폴더 열기", command=self._open_output_dir, state=DISABLED)
        self.open_output_button.pack(pady=(0, 10))

        self._start_date_fetch()

    # ---------- 공용 ----------

    def _set_busy(self, busy: bool) -> None:
        state = DISABLED if busy else NORMAL
        self.refresh_button.configure(state=state)
        self.update_button.configure(state=state)
        for btn in self._date_buttons:
            btn.configure(state=state)

    # ---------- 날짜 목록 조회 ----------

    def _start_date_fetch(self) -> None:
        self._set_busy(True)
        self.status_var.set("사용 가능한 날짜 불러오는 중...")
        for btn in self._date_buttons:
            btn.destroy()
        self._date_buttons.clear()

        thread = threading.Thread(target=self._fetch_dates_worker, daemon=True)
        thread.start()
        self.root.after(POLL_INTERVAL_MS, self._poll_date_queue)

    def _fetch_dates_worker(self) -> None:
        try:
            dates = build_report.get_available_dates()
            self.date_queue.put(("ok", dates))
        except Exception as e:  # noqa: BLE001
            self.date_queue.put(("error", e))

    def _poll_date_queue(self) -> None:
        try:
            status, payload = self.date_queue.get_nowait()
        except queue.Empty:
            self.root.after(POLL_INTERVAL_MS, self._poll_date_queue)
            return

        if status == "error":
            self._set_busy(False)
            self.status_var.set("날짜 조회 실패")
            messagebox.showerror("오류", f"사용 가능한 날짜를 못 불러왔어:\n{payload}")
            return

        dates: list[date] = payload
        for d in dates:
            btn = ttk.Button(
                self.date_buttons_frame,
                text=_format_date_label(d),
                command=lambda d=d: self._on_run(d),
            )
            btn.pack(side="left", padx=(0, 6))
            self._date_buttons.append(btn)

        self._set_busy(False)
        self.status_var.set("날짜를 선택해줘" if dates else "사용 가능한 날짜가 없어")

    # ---------- 실행 ----------

    def _append_log(self, data: str) -> None:
        self.log_widget.configure(state=NORMAL)
        self.log_widget.insert(END, data)
        self.log_widget.see(END)
        self.log_widget.configure(state=DISABLED)

    def _on_run(self, target: date) -> None:
        self._set_busy(True)
        self.open_output_button.configure(state=DISABLED)
        self.status_var.set(f"{target.isoformat()} 데이터 수집 중...")
        self.log_widget.configure(state=NORMAL)
        self.log_widget.delete("1.0", END)
        self.log_widget.configure(state=DISABLED)

        thread = threading.Thread(target=self._run_worker, args=(target,), daemon=True)
        thread.start()
        self.root.after(POLL_INTERVAL_MS, self._poll_log_queue)

    def _run_worker(self, target: date) -> None:
        """백그라운드 스레드. Tk 객체는 일절 만지지 않고 큐에만 쓴다."""
        original_stdout = sys.stdout
        sys.stdout = _QueueStream(self.log_queue)
        error: Exception | None = None
        out_path: Path | None = None
        try:
            out_path = build_report.run(target=target)
        except Exception as e:  # noqa: BLE001
            error = e
        finally:
            sys.stdout = original_stdout
        self.log_queue.put((_DONE, out_path, error))

    def _poll_log_queue(self) -> None:
        """메인 스레드에서만 실행됨. 큐를 비우면서 로그를 갱신하고 완료 신호를 확인한다."""
        done_payload = None
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and item and item[0] is _DONE:
                    done_payload = item
                else:
                    self._append_log(item)
        except queue.Empty:
            pass

        if done_payload is not None:
            _, out_path, error = done_payload
            self._on_done(out_path, error)
            return

        self.root.after(POLL_INTERVAL_MS, self._poll_log_queue)

    def _on_done(self, out_path: Path | None, error: Exception | None) -> None:
        self._set_busy(False)
        if error is not None:
            self.status_var.set("실패")
            messagebox.showerror("오류", f"실행 중 오류가 발생했어:\n{error}")
            return

        self.status_var.set(f"완료: {out_path}")
        self.open_output_button.configure(state=NORMAL)
        self._last_output_dir = out_path.parent if out_path else None

    # ---------- 업데이트 확인 ----------

    def _start_update_check(self) -> None:
        self._set_busy(True)
        self.status_var.set("업데이트 확인 중...")

        thread = threading.Thread(target=self._update_worker, daemon=True)
        thread.start()
        self.root.after(POLL_INTERVAL_MS, self._poll_update_queue)

    def _update_worker(self) -> None:
        try:
            message = updater.check_and_update()
            self.update_queue.put(("ok", message))
        except Exception as e:  # noqa: BLE001
            self.update_queue.put(("error", e))

    def _poll_update_queue(self) -> None:
        try:
            status, payload = self.update_queue.get_nowait()
        except queue.Empty:
            self.root.after(POLL_INTERVAL_MS, self._poll_update_queue)
            return

        self._set_busy(False)

        if status == "error":
            self.status_var.set("업데이트 확인 실패")
            messagebox.showerror("오류", f"업데이트 확인 중 문제가 생겼어:\n{payload}")
            return

        self.status_var.set(payload)
        messagebox.showinfo("업데이트", payload)

    def _open_output_dir(self) -> None:
        if not self._last_output_dir:
            return
        target_dir = self._last_output_dir
        if sys.platform == "darwin":
            import subprocess

            subprocess.run(["open", str(target_dir)], check=False)
        elif sys.platform.startswith("win"):
            import os

            os.startfile(str(target_dir))  # type: ignore[attr-defined]
        else:
            import subprocess

            subprocess.run(["xdg-open", str(target_dir)], check=False)


def main() -> None:
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

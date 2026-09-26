"""Professional semi-auto MT5 trading assistant.

This desktop app is designed as a safe, semi-auto signal system.
It can connect to MetaTrader5 when available, and it falls back to a demo
simulator so the project remains runnable without a broker connection.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from zoneinfo import ZoneInfo

from core.data import fetch_market_data, place_demo_trade
from core.strategy import analyze_forex

PAKISTAN_TZ = ZoneInfo("Asia/Karachi")
TIMEFRAME_LABELS = [
    "1 minute",
    "5 minutes",
    "15 minutes",
    "30 minutes",
    "1 hour",
    "1 day",
]


class TradingAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MT5 Trading Signal Assistant")
        self.geometry("980x760")
        self.minsize(900, 680)
        self.configure(bg="#0f172a")
        self._build_ui()

    def _build_ui(self):
        self.main_frame = ttk.Frame(self, padding=16)
        self.main_frame.pack(fill="both", expand=True)

        header = ttk.Frame(self.main_frame)
        header.pack(fill="x", pady=(0, 12))
        title = ttk.Label(
            header,
            text="MT5 Trading Signal Assistant",
            font=("Segoe UI", 22, "bold"),
        )
        title.pack(anchor="w")
        sub = ttk.Label(
            header,
            text="Semi-auto analysis system — manual review required before order placement",
            foreground="#b91c1c",
            font=("Segoe UI", 10),
        )
        sub.pack(anchor="w")

        top_cards = ttk.Frame(self.main_frame)
        top_cards.pack(fill="x", pady=(0, 12))

        self.connection_frame = ttk.LabelFrame(top_cards, text="Connection")
        self.connection_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.status_text = tk.StringVar(value="Checking MT5 connection…")
        ttk.Label(self.connection_frame, textvariable=self.status_text, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.account_text = tk.StringVar(value="Account: not connected")
        ttk.Label(self.connection_frame, textvariable=self.account_text).pack(anchor="w", padx=10, pady=2)

        self.market_frame = ttk.LabelFrame(top_cards, text="Market")
        self.market_frame.pack(side="left", fill="x", expand=True)
        self.source_text = tk.StringVar(value="Source: pending")
        ttk.Label(self.market_frame, textvariable=self.source_text, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.symbol_text = tk.StringVar(value="Symbol: EURUSD")
        ttk.Label(self.market_frame, textvariable=self.symbol_text).pack(anchor="w", padx=10, pady=2)
        self.price_text = tk.StringVar(value="Last price: --")
        ttk.Label(self.market_frame, textvariable=self.price_text).pack(anchor="w", padx=10, pady=2)

        settings = ttk.LabelFrame(self.main_frame, text="Analysis settings")
        settings.pack(fill="x", pady=(0, 12))

        settings_grid = ttk.Frame(settings)
        settings_grid.pack(fill="x", padx=10, pady=10)

        ttk.Label(settings_grid, text="Symbol").grid(row=0, column=0, sticky="w", padx=5, pady=6)
        self.symbol = ttk.Entry(settings_grid, width=16)
        self.symbol.insert(0, "EURUSD")
        self.symbol.grid(row=0, column=1, sticky="w", padx=5, pady=6)

        ttk.Label(settings_grid, text="Timeframe").grid(row=0, column=2, sticky="w", padx=5, pady=6)
        self.timeframe = ttk.Combobox(settings_grid, values=TIMEFRAME_LABELS, state="readonly", width=18)
        self.timeframe.current(1)
        self.timeframe.grid(row=0, column=3, sticky="w", padx=5, pady=6)

        ttk.Label(settings_grid, text="Lot size").grid(row=0, column=4, sticky="w", padx=5, pady=6)
        self.lot_size = ttk.Entry(settings_grid, width=10)
        self.lot_size.insert(0, "0.10")
        self.lot_size.grid(row=0, column=5, sticky="w", padx=5, pady=6)

        self.auto_trade = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_grid, text="Enable auto trading", variable=self.auto_trade).grid(row=0, column=6, sticky="w", padx=6, pady=6)

        action_row = ttk.Frame(settings_grid)
        action_row.grid(row=1, column=0, columnspan=7, sticky="ew", pady=(6, 0))
        ttk.Button(action_row, text="Refresh signal", command=self.refresh_signal).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text="Place BUY", command=lambda: self.place_trade("BUY")).pack(side="left", padx=8)
        ttk.Button(action_row, text="Place SELL", command=lambda: self.place_trade("SELL")).pack(side="left", padx=8)
        ttk.Button(action_row, text="Close all positions", command=self.close_all_positions).pack(side="left", padx=8)
        ttk.Button(action_row, text="Emergency stop", command=self.emergency_stop).pack(side="left", padx=8)

        signal_panel = ttk.LabelFrame(self.main_frame, text="Latest signal")
        signal_panel.pack(fill="both", expand=True, pady=(0, 12))

        signal_box = ttk.Frame(signal_panel, padding=16)
        signal_box.pack(fill="both", expand=True)

        self.signal_var = tk.StringVar(value="NO TRADE")
        self.signal_label = ttk.Label(
            signal_box,
            textvariable=self.signal_var,
            font=("Segoe UI", 30, "bold"),
            foreground="#f59e0b",
        )
        self.signal_label.pack(anchor="w", pady=(0, 10))

        self.strength_var = tk.StringVar(value="Strength: --")
        ttk.Label(signal_box, textvariable=self.strength_var, font=("Segoe UI", 11)).pack(anchor="w")
        self.trend_var = tk.StringVar(value="Trend: --")
        ttk.Label(signal_box, textvariable=self.trend_var, font=("Segoe UI", 11)).pack(anchor="w")
        self.rsi_var = tk.StringVar(value="RSI: --")
        ttk.Label(signal_box, textvariable=self.rsi_var, font=("Segoe UI", 11)).pack(anchor="w")
        self.volatility_var = tk.StringVar(value="Volatility: --")
        ttk.Label(signal_box, textvariable=self.volatility_var, font=("Segoe UI", 11)).pack(anchor="w")

        self.details = tk.Text(signal_box, height=16, wrap="word", state="disabled", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True, pady=(12, 0))

        self.message_log = tk.Text(self.main_frame, height=8, wrap="word", state="disabled", font=("Consolas", 9))
        self.message_log.pack(fill="x", pady=(0, 10))

        self.refresh_signal()

    def log_message(self, message: str):
        self.message_log.config(state="normal")
        stamp = datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S PKT")
        self.message_log.insert("end", f"[{stamp}] {message}\n")
        self.message_log.see("end")
        self.message_log.config(state="disabled")

    def refresh_signal(self):
        symbol = self.symbol.get().strip().upper()
        timeframe = self.timeframe.get()
        if not symbol:
            messagebox.showerror("Input error", "Please enter a symbol.")
            return
        if not timeframe:
            messagebox.showerror("Input error", "Please choose a timeframe.")
            return

        try:
            market = fetch_market_data(symbol, timeframe)
            analysis = analyze_forex(market["candles"], timeframe)
            if analysis.get("signal") == "BUY":
                self.signal_label.configure(foreground="#22c55e")
            elif analysis.get("signal") == "SELL":
                self.signal_label.configure(foreground="#ef4444")
            else:
                self.signal_label.configure(foreground="#f59e0b")

            self.signal_var.set(analysis["signal"])
            self.strength_var.set(f"Strength: {analysis['strength']}%")
            self.trend_var.set(f"Trend: {analysis['trend']}")
            self.rsi_var.set(f"RSI: {analysis['rsi']}")
            self.volatility_var.set(f"Volatility: {analysis['volatility']}")
            self.source_text.set(f"Source: {market['source']}")
            self.symbol_text.set(f"Symbol: {symbol}")
            self.price_text.set(f"Last price: {analysis['close']}")
            self.status_text.set(f"Connected: {market['source']} | Updated {datetime.now(PAKISTAN_TZ).strftime('%Y-%m-%d %H:%M:%S PKT')}")
            self.account_text.set(f"Account: {market.get('account', 'demo / not connected')}")
            self._write_details(analysis, symbol, timeframe, market["source"])
            self.log_message(f"Signal refreshed for {symbol} ({timeframe}) -> {analysis['signal']}")
        except Exception as exc:  # pragma: no cover - UI guard
            self.status_text.set("Connection failed")
            self.signal_var.set("NO TRADE")
            self.log_message(f"Refresh failed: {exc}")
            messagebox.showerror("Market data error", str(exc))

    def _write_details(self, analysis, symbol, timeframe, source):
        lines = [
            f"Signal: {analysis['signal']}",
            f"Source: {source}",
            f"Symbol: {symbol}",
            f"Timeframe: {timeframe}",
            f"Strength: {analysis['strength']}%",
            f"Trend: {analysis['trend']}",
            f"RSI: {analysis['rsi']}",
            f"Close: {analysis['close']}",
            f"Fast MA: {analysis['fast_ma']}",
            f"Slow MA: {analysis['slow_ma']}",
            f"Volatility: {analysis['volatility']}",
            "",
            "Reasoning:",
            *[f"- {item}" for item in analysis["reasons"]],
            "",
            "Manual trading warning: confirm every trade against the broker chart and your own risk plan.",
        ]
        self.details.config(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", "\n".join(lines))
        self.details.config(state="disabled")

    def place_trade(self, direction: str):
        symbol = self.symbol.get().strip().upper()
        if not symbol:
            messagebox.showwarning("Input required", "Please choose a symbol first.")
            return
        lot_size = self.lot_size.get().strip()
        if not lot_size:
            lot_size = "0.10"
        try:
            lot_size = float(lot_size)
        except ValueError:
            messagebox.showerror("Input error", "Lot size must be a valid number.")
            return

        if self.auto_trade.get():
            try:
                result = place_demo_trade(symbol, direction, lot_size)
                self.log_message(f"Auto-trade request accepted for {direction} {symbol} @ {lot_size} lots")
                messagebox.showinfo("Auto trade request", result)
                return
            except Exception as exc:  # pragma: no cover - UI guard
                messagebox.showerror("Order error", str(exc))
                return

        messagebox.showinfo(
            "Manual trading enabled",
            f"Manual mode is active. Trade request prepared for {direction} {symbol} at {lot_size} lots. "
            "Check the MT5 terminal and approve or reject the order there.",
        )
        self.log_message(f"Manual {direction} trade prepared for {symbol} at {lot_size} lots")

    def close_all_positions(self):
        self.log_message("Close all positions requested by user.")
        messagebox.showinfo("Close all positions", "This action is prepared. Confirm in MT5 or check the broker terminal before closing any open trades.")

    def emergency_stop(self):
        self.auto_trade.set(False)
        self.log_message("Emergency stop activated. Auto trading disabled.")
        messagebox.showwarning("Emergency stop", "Auto trading has been disabled. Manual review is required.")


if __name__ == "__main__":
    app = TradingAssistant()
    app.mainloop()

import pandas as pd
from datetime import datetime, timedelta
import pytz
from tpqoa.tpqoa import tpqoa

class LiveTrader(tpqoa):
    def __init__(
        self,
        cfg,
        instrument,
        bar_length,
        units,
        history_days=1,
        stop_datetime=None,
        stop_loss=None,
        stop_profit=None,
    ):
        """
        Initializes the LiveTrader object.
        """
        # Always define attributes first (avoid AttributeError)
        self._position = 0
        self._profits = []
        self._profit = 0
        self._stop_loss = stop_loss
        self._stop_profit = stop_profit
        self._stop_datetime = (
            stop_datetime.astimezone(pytz.utc) if stop_datetime else None
        )

        print("Checking market status...")

        # ✅ Correction : Vérifie l'heure via OANDA (UTC)
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        weekday = utc_now.weekday()
        hour = utc_now.hour

        if weekday == 5 or (weekday == 6 and hour < 21):
            raise Exception("Sorry, markets are closed (weekend).")
        else:
            print("Markets are open. Starting trading session.")

        # Initialize tpqoa (connect to OANDA)
        super().__init__(cfg)
        self._instrument = instrument
        self._bar_length = pd.to_timedelta(bar_length)
        self._tick_data = pd.DataFrame()
        self._raw_data = None
        self._data = None
        self._last_tick = None
        self._units = units

        # Load historical data
        self.setup_history(history_days)

        # Start data stream
        self.stream_data(self._instrument)

    def __del__(self):
        """Ensure closing of position when object is deleted."""
        try:
            self.close_position()
        except Exception as e:
            print(f"Cleanup error ignored: {e}")

    def setup_history(self, days=1):
        print("Setting up historical data...")
        if days <= 0:
            return

        while True:
            now = datetime.utcnow().replace(microsecond=0)
            past = now - timedelta(days=days)

            mid_price = (
                self.get_history(
                    instrument=self._instrument,
                    start=past,
                    end=now,
                    granularity="S5",
                    price="M",
                    localize=False,
                )
                .c.dropna()
                .to_frame()
            )

            df = mid_price.rename(columns={"c": "mid_price"})
            df = df.resample(self._bar_length, label="right").last().dropna().iloc[:-1]

            self._raw_data = df.copy()
            self._last_tick = self._raw_data.index[-1]

            if (
                pd.to_datetime(datetime.utcnow()).tz_localize("UTC")
                - self._last_tick
            ) < self._bar_length:
                print("History setup complete. Opening live stream.")
                break

    def on_success(self, time, bid, ask):
        print(time, bid, ask)
        recent_tick = pd.to_datetime(time)
        stopped = False

        # Check stop conditions
        if self._stop_datetime and recent_tick >= self._stop_datetime:
            self.stop_stream = True
            self.close_position()
            stopped = True
        elif self._stop_loss and self._profit < self._stop_loss:
            self.stop_stream = True
            self.close_position()
            stopped = True
        elif self._stop_profit and self._profit > self._stop_profit:
            self.stop_stream = True
            self.close_position()
            stopped = True

        if stopped:
            print("Stop triggered, ending stream.")
            return

        # Handle tick
        df = pd.DataFrame(
            {
                "bid_price": bid,
                "ask_price": ask,
                "mid_price": (ask + bid) / 2,
                "spread": ask - bid,
            },
            index=[recent_tick],
        )
        self._tick_data = pd.concat([self._tick_data, df])

        if (recent_tick - self._last_tick) >= self._bar_length:
            self._raw_data = pd.concat(
                [self._raw_data,
                 self._tick_data.resample(self._bar_length, label="right").last().ffill().iloc[:-1]]
            )
            self._tick_data = self._tick_data.iloc[-1:]
            self._last_tick = self._raw_data.index[-1]

            self.define_strategy()
            self.trade()

    def define_strategy(self):
        pass  # Replace by your strategy logic

    def trade(self):
        # Long
        if self._data["position"].iloc[-1] == 1:
            if self._position == 0:
                order = self.create_order(self._instrument, self._units, suppress=True, ret=True)
                self.trade_report(order, 1)
            elif self._position == -1:
                order = self.create_order(self._instrument, self._units * 2, suppress=True, ret=True)
                self.trade_report(order, 1)
            self._position = 1

        # Short
        elif self._data["position"].iloc[-1] == -1:
            if self._position == 0:
                order = self.create_order(self._instrument, -self._units, suppress=True, ret=True)
                self.trade_report(order, -1)
            elif self._position == 1:
                order = self.create_order(self._instrument, -(self._units * 2), suppress=True, ret=True)
                self.trade_report(order, -1)
            self._position = -1

        # Neutral
        elif self._data["position"].iloc[-1] == 0:
            if self._position == 1:
                order = self.create_order(self._instrument, -self._units, suppress=True, ret=True)
                self.trade_report(order, 0)
            elif self._position == -1:
                order = self.create_order(self._instrument, self._units, suppress=True, ret=True)
                self.trade_report(order, 0)
            self._position = 0

    def close_position(self):
        if getattr(self, "_position", 0) != 0:
            order = self.create_order(
                self._instrument,
                units=-(self._position * self._units),
                suppress=True,
                ret=True,
            )
            self.trade_report(order, 0)
            self._position = 0

    def trade_report(self, order, position):
        time = order["time"]
        units = order["units"]
        price = order["price"]
        profit = float(order["pl"])
        self._profits.append(profit)
        self._profit = sum(self._profits)

        print(
            f"{time} : {position} --- {units} units, price ${price}, profit ${profit}, total ${self._profit}"
        )

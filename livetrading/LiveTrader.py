import pandas as pd
import pytz
from datetime import datetime, timedelta
import tpqoa


class MomentumLive(tpqoa.tpqoa):
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
        Initializes the MomentumLive trader for live trading via OANDA.
        """

        # --- Initial safety attributes ---
        self._position = 0
        self._stop_stream = False

        # --- Initialize OANDA connection first ---
        super().__init__(cfg)

        # --- Core parameters ---
        self._instrument = instrument
        self._bar_length = pd.to_timedelta(bar_length)
        self._units = units

        self._tick_data = pd.DataFrame()
        self._raw_data = None
        self._data = None
        self._last_tick = None

        # --- Check if the market is open ---
        if not self.market_is_open():
            raise Exception("Sorry, markets are closed")

        # --- Stop datetime ---
        if stop_datetime:
            utc_datetime = stop_datetime.astimezone(pytz.utc)
            self._stop_datetime = utc_datetime
        else:
            self._stop_datetime = None

        # --- Risk management ---
        self._stop_loss = stop_loss
        self._stop_profit = stop_profit

        # --- Stats ---
        self._profits = []
        self._profit = 0

        # --- Prepare historical data ---
        self.setup_history(history_days)

        # --- Start streaming ---
        self.stream_data(self._instrument)

    # ==========================================================
    # SAFE DESTRUCTOR
    # ==========================================================
    def __del__(self):
        """Ensure that positions are closed safely."""
        try:
            if hasattr(self, "_position") and self._position != 0:
                self.close_position()
        except Exception as e:
            print("Error in __del__ while trying to close position:", e)

    # ==========================================================
    # CHECK MARKET STATUS
    # ==========================================================
    def market_is_open(self):
        """
        Check if the market is producing recent data for the instrument.
        Uses OANDA's historical data endpoint to verify if ticks exist in
        the past minute. If yes, market is open.
        """
        try:
            now = datetime.utcnow().replace(microsecond=0)
            past = now - timedelta(minutes=1)

            hist = self.get_history(
                instrument=self._instrument,
                start=past,
                end=now,
                granularity="S5",
                price="M",
                localize=False,
            )

            series = hist.c.dropna()
            if not series.empty:
                print(f"[MARKET CHECK] {self._instrument}: Market is OPEN ✅")
                return True
            else:
                print(f"[MARKET CHECK] {self._instrument}: No recent data, assume CLOSED ❌")
                return False

        except Exception as e:
            print("market_is_open check failed:", e)
            return False

    # ==========================================================
    # SETUP HISTORY
    # ==========================================================
    def setup_history(self, days=1):
        """Fetch historical data to start live trading."""
        now = datetime.utcnow().replace(microsecond=0)
        past = now - timedelta(days=days)

        print(f"[HISTORY] Loading {days} days of data for {self._instrument}...")
        self._raw_data = self.get_history(
            instrument=self._instrument,
            start=past,
            end=now,
            granularity="M1",
            price="M",
            localize=False,
        )
        print("[HISTORY] Done ✅")

    # ==========================================================
    # STREAM DATA
    # ==========================================================
    def stream_data(self, instrument):
        """
        Start receiving live tick data from OANDA for the instrument.
        """
        print(f"[STREAM] Starting live stream for {instrument} ...")
        self.stream_data(instrument)
        print("[STREAM] Live stream started ✅")

    # ==========================================================
    # POSITION MANAGEMENT
    # ==========================================================
    def close_position(self):
        """Close any open position on the instrument."""
        print(f"[TRADE] Closing open position on {self._instrument} ...")
        self.create_order(self._instrument, units=-self._position)
        self._position = 0
        print("[TRADE] Position closed ✅")

    # ==========================================================
    # PLACEHOLDER FOR STRATEGY LOGIC
    # ==========================================================
    def on_tick(self, tick):
        """
        Called automatically when new tick data is received.
        Implement your trading logic here.
        """
        self._last_tick = tick
        # Example (to customize):
        # price = float(tick['bid'])
        # if price > self._some_moving_average:
        #     self.create_order(self._instrument, units=self._units)
        # else:
        #     self.close_position()
        pass


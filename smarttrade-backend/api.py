from fastapi import FastAPI
from news_sentiment import get_deepseek_recommendation_for_bot
from pydantic import BaseModel
from threading import Thread
import time

app = FastAPI()

class TradeRequest(BaseModel):
    strategy: str
    instrument: str
    granularity: str
    units: int
    window: int = 3  # pour Momentum
    # Ajoute ici d'autres paramètres si besoin

class AlgoRunner(Thread):
    def __init__(self, strategy, instrument, granularity, units, window=3, interval=60):
        super().__init__()
        self.strategy = strategy
        self.instrument = instrument
        self.granularity = granularity
        self.units = units
        self.window = window
        self.interval = interval  # temps entre chaque décision (en secondes)
        self.running = True
        self.trader = None
    def run(self):
        while self.running:
            reco = get_deepseek_recommendation_for_bot()
            if self.strategy == "momentum":
                if not self.trader:
                    from livetrading.MomentumLive import MomentumLive
                    self.trader = MomentumLive(
                        cfg="oanda.cfg",
                        instrument=self.instrument,
                        bar_length=self.granularity,
                        window=self.window,
                        units=self.units
                    )
                if reco == "buy":
                    self.trader._position = 1
                elif reco == "sell":
                    self.trader._position = -1
                else:
                    self.trader._position = 0
            elif self.strategy == "breakout":
                if not self.trader:
                    from livetrading.BollingerBandsLive import BollingerBandsLive
                    self.trader = BollingerBandsLive(
                        cfg="oanda.cfg",
                        instrument=self.instrument,
                        bar_length=self.granularity,
                        sma=20,
                        deviation=2,
                        units=self.units
                    )
                if reco == "buy":
                    self.trader._position = 1
                elif reco == "sell":
                    self.trader._position = -1
                else:
                    self.trader._position = 0
            # Ajoute ici d'autres stratégies avancées
            print(f"[{self.strategy}] Reco: {reco} | Position: {self.trader._position}")
            time.sleep(self.interval)
    def stop(self):
        self.running = False

algo_runner = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/recommendation")
def get_recommendation(req: TradeRequest):
    reco = get_deepseek_recommendation_for_bot()
    return {"recommendation": reco}

# Exemple d'endpoint pour lancer une stratégie (à adapter selon ton bot)
@app.post("/trade")
def trade(req: TradeRequest):
    reco = get_deepseek_recommendation_for_bot()
    result = None
    if req.strategy == "momentum":
        trader = MomentumLive(
            cfg="oanda.cfg",
            instrument=req.instrument,
            bar_length=req.granularity,
            window=req.window,
            units=req.units
        )
        if reco == "buy":
            trader._position = 1
        elif reco == "sell":
            trader._position = -1
        else:
            trader._position = 0
        result = f"Momentum position ajustée : {trader._position}"
    elif req.strategy == "breakout":
        # Exemple simple de breakout (à adapter selon ta logique)
        # Ici, on peut utiliser BollingerBandsLive comme base
        from livetrading.BollingerBandsLive import BollingerBandsLive
        trader = BollingerBandsLive(
            cfg="oanda.cfg",
            instrument=req.instrument,
            bar_length=req.granularity,
            sma=20,  # paramètre typique
            deviation=2,
            units=req.units
        )
        if reco == "buy":
            trader._position = 1
        elif reco == "sell":
            trader._position = -1
        else:
            trader._position = 0
        result = f"Breakout position ajustée : {trader._position}"
    else:
        result = "Stratégie non supportée"
    return {"result": result, "recommendation": reco}

@app.post("/algo/start")
def start_algo(req: TradeRequest):
    global algo_runner
    if algo_runner and algo_runner.is_alive():
        return {"status": "déjà en cours"}
    algo_runner = AlgoRunner(
        strategy=req.strategy,
        instrument=req.instrument,
        granularity=req.granularity,
        units=req.units,
        window=getattr(req, "window", 3),
        interval=60  # toutes les minutes
    )
    algo_runner.start()
    return {"status": "algo lancé"}

@app.post("/algo/stop")
def stop_algo():
    global algo_runner
    if algo_runner:
        algo_runner.stop()
        return {"status": "algo arrêté"}
    return {"status": "aucun algo en cours"}

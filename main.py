import os
import time
import logging
from datetime import datetime
import seaborn as sns
from tpqoa.tpqoa import tpqoa
from news_sentiment import get_deepseek_recommendation_for_bot

# Import des stratégies
from livetrading.BollingerBandsLive import BollingerBandsLive
from livetrading.ContrarianLive import ContrarianLive
from livetrading.MLClassificationLive import MLClassificationLive
from livetrading.MomentumLive import MomentumLive
from livetrading.SMALive import SMALive

from backtesting.ContrarianBacktest import ContrarianBacktest
from backtesting.BollingerBandsBacktest import BollingerBandsBacktest
from backtesting.MomentumBacktest import MomentumBacktest
from backtesting.SMABacktest import SMABacktest
from backtesting.MLClassificationBacktest import MLClassificationBacktest

#############################################
# CONFIGURATION VIA VARIABLES D'ENVIRONNEMENT
#############################################

MODE = os.getenv("MODE", "live")  # "live" ou "backtest"
STRATEGY = os.getenv("STRATEGY", "sma")
INSTRUMENT = os.getenv("INSTRUMENT", "EUR/USD")
GRANULARITY = os.getenv("GRANULARITY", "1H")
UNITS = int(os.getenv("UNITS", 100000))
STOP_PROFIT = os.getenv("STOP_PROFIT", None)
STOP_LOSS = os.getenv("STOP_LOSS", None)
LIVE_INTERVAL = int(os.getenv("LIVE_INTERVAL", 300))  # secondes entre chaque tick

# Pour Backtest
START_DATE = os.getenv("START_DATE", "2024-01-01")
END_DATE = os.getenv("END_DATE", "2024-12-31")
TRADING_COST = float(os.getenv("TRADING_COST", 0.00007))

# SMA
SMAS = int(os.getenv("SMAS", 9))
SMAL = int(os.getenv("SMAL", 20))

# Bollinger Bands
SMA = int(os.getenv("SMA", 9))
DEVIATION = int(os.getenv("DEVIATION", 2))

# Momentum / Contrarian
WINDOW = int(os.getenv("WINDOW", 3))

# ML
LAGS = int(os.getenv("LAGS", 6))

CFG = os.getenv("OANDA_CFG", "oanda.cfg")

#############################################
# LOGGING
#############################################
logging.basicConfig(
    filename="trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

#############################################
# FONCTION POUR INITIALISER LE TRADER
#############################################
def init_trader():
    try:
        oanda = tpqoa(CFG)
        logging.info(f"Connexion OANDA réussie pour {INSTRUMENT}")
    except Exception as e:
        logging.error(f"Erreur connexion OANDA : {e}")
        raise

    if MODE == "live":
        logging.info(f"Mode LIVE activé — Stratégie : {STRATEGY}")

        if STRATEGY == "sma":
            trader = SMALive(CFG, INSTRUMENT, GRANULARITY, SMAS, SMAL, UNITS,
                             stop_loss=STOP_LOSS, stop_profit=STOP_PROFIT)

        elif STRATEGY == "bollinger_bands":
            trader = BollingerBandsLive(CFG, INSTRUMENT, GRANULARITY, SMA, DEVIATION,
                                        stop_profit=STOP_PROFIT)

        elif STRATEGY == "momentum":
            trader = MomentumLive(CFG, INSTRUMENT, GRANULARITY, WINDOW, UNITS,
                                  stop_loss=STOP_LOSS, stop_profit=STOP_PROFIT)

        elif STRATEGY == "contrarian":
            trader = ContrarianLive(CFG, INSTRUMENT, GRANULARITY, WINDOW, UNITS,
                                    stop_loss=STOP_LOSS, stop_profit=STOP_PROFIT)

        elif STRATEGY == "ml_classification":
            trader = MLClassificationLive(CFG, INSTRUMENT, GRANULARITY, LAGS, UNITS,
                                          stop_loss=STOP_LOSS, stop_profit=STOP_PROFIT)
        else:
            raise ValueError(f"Stratégie inconnue : {STRATEGY}")

    else:
        logging.info(f"Mode BACKTEST activé — Stratégie : {STRATEGY}")

        if STRATEGY == "sma":
            trader = SMABacktest(INSTRUMENT, START_DATE, END_DATE, SMAS, SMAL, GRANULARITY, TRADING_COST)

        elif STRATEGY == "bollinger_bands":
            trader = BollingerBandsBacktest(INSTRUMENT, START_DATE, END_DATE, SMA, DEVIATION, GRANULARITY, TRADING_COST)

        elif STRATEGY == "momentum":
            trader = MomentumBacktest(INSTRUMENT, START_DATE, END_DATE, WINDOW, GRANULARITY, TRADING_COST)

        elif STRATEGY == "contrarian":
            trader = ContrarianBacktest(INSTRUMENT, START_DATE, END_DATE, WINDOW, GRANULARITY, TRADING_COST)

        elif STRATEGY == "ml_classification":
            trader = MLClassificationBacktest(INSTRUMENT, START_DATE, END_DATE, GRANULARITY, TRADING_COST)

        else:
            raise ValueError(f"Stratégie inconnue : {STRATEGY}")

    return trader

#############################################
# FONCTION POUR EXECUTER LE LIVE TRADING
#############################################
def run_live(trader):
    logging.info("Démarrage du Live Trading...")
    try:
        while True:
            reco = get_deepseek_recommendation_for_bot()
            logging.info(f"Recommandation DeepSeek : {reco}")

            # Appliquer la recommandation selon la stratégie
            if reco == "buy":
                trader._position = 1
            elif reco == "sell":
                trader._position = -1
            else:
                trader._position = 0

            logging.info(f"Position actuelle : {trader._position}")

            # TODO : exécuter un tick du trader si nécessaire
            # trader.run_tick() ou trader.update() selon votre implémentation
            time.sleep(LIVE_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Arrêt manuel du Live Trading")
    except Exception as e:
        logging.error(f"Erreur durant le Live Trading : {e}")

#############################################
# FONCTION POUR EXECUTER LE BACKTEST
#############################################
def run_backtest(trader):
    logging.info("Démarrage du Backtest...")
    try:
        trader.test()
        if hasattr(trader, "optimize"):
            trader.optimize()
        if hasattr(trader, "plot_results"):
            trader.plot_results()
        logging.info("Backtest terminé ✅")
    except Exception as e:
        logging.error(f"Erreur durant le Backtest : {e}")

#############################################
# MAIN
#############################################
if __name__ == "__main__":
    try:
        trader = init_trader()
        if MODE == "live":
            run_live(trader)
        else:
            run_backtest(trader)
    except Exception as e:
        logging.critical(f"Erreur fatale : {e}")


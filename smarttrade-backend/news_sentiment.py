import requests
import time
import os
from dotenv import load_dotenv

# =====================================================
# 🔧 CONFIGURATION SÉCURISÉE
# =====================================================

# Charge les variables depuis le fichier .env (en local)
load_dotenv()

# Récupère les clés API à partir des variables d'environnement
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

if not DEEPSEEK_API_KEY or not NEWS_API_KEY:
    raise ValueError("⚠️ Les clés API DeepSeek et/ou NewsAPI sont manquantes. Vérifie ton fichier .env ou tes variables Render.")

# =====================================================
# 📰 1. Récupérer les dernières actualités Google News
# =====================================================

def fetch_news_api(query="forex", lang="fr", max_results=10):
    """
    Récupère les dernières actualités Google News liées au mot-clé donné.
    """
    url = f"https://newsapi.org/v2/everything?q={query}&language={lang}&pageSize={max_results}&apiKey={NEWS_API_KEY}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json().get("articles", [])


# =====================================================
# 🧠 2. Analyse de sentiment avec DeepSeek
# =====================================================

def analyze_with_deepseek(article):
    """
    Analyse le sentiment d’un article financier en utilisant DeepSeek Chat API.
    """
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Voici une actualité financière : {article.get('title')}\n"
                    f"{article.get('description')}\n"
                    "Analyse le sentiment (positif, négatif ou neutre) et donne une recommandation de trading (acheter, vendre ou attendre)."
                )
            }
        ]
    }

    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# =====================================================
# 🤖 3. Fonction principale d'analyse complète
# =====================================================

def get_news_sentiment_and_decision():
    """
    Récupère les actualités, les analyse avec DeepSeek et retourne les résultats.
    """
    articles = fetch_news_api()
    results = []

    for article in articles:
        try:
            deepseek_result = analyze_with_deepseek(article)
            results.append({
                "title": article.get("title"),
                "deepseek": deepseek_result
            })
            time.sleep(1)  # éviter de spammer l’API
        except Exception as e:
            results.append({
                "title": article.get("title"),
                "error": str(e)
            })
    return results


# =====================================================
# 💹 4. Recommandation finale pour ton bot de trading
# =====================================================

def get_deepseek_recommendation_for_bot():
    """
    Donne une recommandation finale (buy, sell, hold) basée sur l’analyse DeepSeek.
    """
    decisions = get_news_sentiment_and_decision()
    for d in decisions:
        if "deepseek" in d and d["deepseek"]:
            rec = d["deepseek"].lower()
            if "acheter" in rec or "buy" in rec:
                return "buy"
            elif "vendre" in rec or "sell" in rec:
                return "sell"
            elif "attendre" in rec or "hold" in rec or "neutre" in rec:
                return "hold"
    return "hold"


# =====================================================
# 🧪 5. Exécution directe pour test local
# =====================================================

if __name__ == "__main__":
    decisions = get_news_sentiment_and_decision()
    for d in decisions:
        print("📰 Actualité :", d["title"])
        print("💬 Analyse DeepSeek :", d.get("deepseek"))
        print("---")

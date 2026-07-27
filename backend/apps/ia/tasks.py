"""
Tâches Celery pour l'app IA — réservées à un traitement réellement lourd
(inférence locale, batch...) qui bloquerait une requête HTTP.

Aucune fonctionnalité actuelle de l'app n'en a besoin : les recommandations
(RecommendationLog.compute_for_user) sont un agrégat SQL instantané, et les
appels Claude (services.py) sont des appels API texte de quelques secondes,
du même ordre que les passerelles de paiement déjà synchrones du projet. Le
jour où l'app IA fait un vrai traitement lourd, la tâche irait ici plutôt
que dans une vue.
"""

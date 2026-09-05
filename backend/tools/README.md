# Banc d'audit SUNU MALL

Outils locaux exclus de l'image livrable par `.dockerignore`. Ils refusent une base dont le nom ne commence pas par `sunu_load_`. Ne jamais les pointer vers un environnement partagé ou de production. Les comptes, commandes et paiements créés sont conservés dans la base jetable.

## Préparer le banc

Créer un réseau Docker dédié, PostgreSQL 16 avec une base `sunu_load_fixed`, et Redis 7 sans port public. Fournir les identifiants uniquement via l'environnement, sans les écrire dans les rapports. Construire l'image depuis `backend/` avec `--build-arg REQUIREMENTS_FILE=requirements/dev.txt`. Les outils exigent le code source monté ou copié dans `/app/tools` ; l'image finale seule n'inclut pas ces scripts.

Lancer Django avec `DJANGO_SETTINGS_MODULE=tools.audit_settings`, `POSTGRES_DB=sunu_load_fixed`, les variables PostgreSQL et `REDIS_URL` du réseau isolé ; `AUDIT_REDIS=1` active le cache partagé. Appliquer `python manage.py migrate --noinput`. Démarrer Gunicorn avec quatre workers synchrones et un timeout de 30 secondes, sous une limite de 2 CPU et 1 Gio. Exposer uniquement sur `127.0.0.1`. Les emails restent en mémoire et les paiements en sandbox. Aucune clé externe n'est nécessaire.

## Mesurer

Depuis `/app`, dans le conteneur du serveur d'audit :

```bash
python -m tools.marketplace_load --url http://localhost:8000/api --clients 30,60,120,300 --output /tmp/load.json
python -m tools.rate_limit_probe
```

Le parcours crée deux vendeurs par l'API, les vérifie, fait approuver leurs boutiques par un admin de test, configure trois catégories globales et douze produits avec variantes et stocks. Les acheteurs sont provisionnés avant la mesure. Un tiers achète dans deux boutiques, via deux commandes. Le test des dernières unités oppose trente acheteurs à cinq unités. Le JSON agrège latences, statuts, SQL par requête, connexions/verrous PostgreSQL échantillonnés toutes les 200 ms et compteurs cgroup CPU/mémoire. Aucun jeton ni mot de passe n'est enregistré.

`rate_limit_probe` envoie douze identifiants invalides simultanément ; sur une fenêtre neuve, attendre dix réponses 400 et deux 429. Ne pas le relancer dans la même minute pour mesurer une fenêtre neuve.

`AUDIT_PROVISIONING=1` relève explicitement les limites et ne doit pas être activé pour tester les protections. La mesure historique `baseline.json` l'utilisait ; la mesure finale utilise les protections et Redis. Elles ne constituent donc pas une comparaison temporelle strictement à configuration identique.

## Limites de la méthode

Le générateur consomme les mêmes 2 CPU/1 Gio que les workers. Le plafond mesuré concerne le banc complet. La base est petite, le réseau local, le cache et le stockage PostgreSQL chauds après provisionnement. Les étapes durent quelques secondes et ne sont pas un test d'endurance. Les emails SMTP, les fournisseurs de paiement, l'IA et le stockage d'images distant ne sont pas sollicités sous charge. Les attentes de verrous incluent l'attente SQL ; `slowest_sql_ms` ne remplace pas une analyse `pg_stat_statements` avec plans sur un volume représentatif.

Pour une campagne de capacité de production, déplacer le générateur hors du conteneur, charger une volumétrie réaliste, mesurer par phase les ressources, exécuter une montée progressive puis un palier long et instrumenter les fournisseurs externes.

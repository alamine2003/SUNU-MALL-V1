# SUNU MALL — Documentation Globale de l'Environnement

Bienvenue sur le dépôt de **SUNU MALL**, une place de marché (marketplace) sénégalaise en ligne permettant à chaque vendeur de gérer sa propre boutique (produits, commandes, livreurs), accessible via des interfaces web et mobiles.

Ce dépôt utilise une structure de **mono-repo** regroupant toutes les briques logicielles du projet.

---

## 👥 Rôles au sein de l'Équipe

| Rôle | Périmètre technique |
| :--- | :--- |
| **CTO (Lead Infra / DevOps & Backend)** | Architecture, déploiement, sécurité, base de données |
| **Développeur Backend** | API REST (Django DRF), tâches asynchrones (Celery) |

| **Développeuse Frontend** | Boutique et espaces vendeur (React + Vite) |
| **Développeuse Mobile & IA** | Application Client (React Native) & Intégration IA |
| **Développeur Mobile, IA & DevOps** | App mobile, intégration IA et support infrastructure / CI-CD |

---

## 📁 Architecture du Mono-repo

```
sunu-mall/
├── backend/            # API REST - Django + Django REST Framework + Celery
├── frontend/           # Boutique et espaces vendeur - React + Vite
├── mobile/             # Application mobile Client - React Native (Expo)
├── infra/              # Configuration Docker Compose, Nginx, Variables d'env & Monitoring
│   ├── env/            # Variables d'environnement templates (dev, prod, staging)
│   ├── nginx/          # Configuration du reverse proxy de routage
│   ├── monitoring/     # Configuration Prometheus, Grafana & Loki
│   └── scripts/        # Scripts d'exploitation (migration, backup, restore, deploy)
└── docs/               # Documentations fonctionnelles et décisions d'architecture
```

---

## 🛠️ Configuration et Démarrage de l'Environnement Local

### 1. Prérequis
Assurez-vous d'avoir installé sur votre machine :
* [Docker](https://www.docker.com/) et **Docker Compose**
* [Git](https://git-scm.com/)
* [Node.js](https://nodejs.org/) (pour tester les frontends en local hors Docker si besoin)

### 2. Configuration des variables d'environnement
Avant de démarrer les conteneurs, vous devez dupliquer les fichiers d'environnement d'exemple et configurer vos clés secrètes :

```bash
# Configuration des services Docker (infra/env)
cp infra/env/backend.env.example infra/env/backend.env
cp infra/env/postgres.env.example infra/env/postgres.env
cp infra/env/redis.env.example infra/env/redis.env
cp infra/env/minio.env.example infra/env/minio.env
cp infra/env/grafana.env.example infra/env/grafana.env

# Configuration locale des projets (si vous les lancez hors Docker)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

### 3. Lancement de la Stack de Développement
Pour lancer l'ensemble des services en local avec Docker Compose :

```bash
# Lancement en tâche de fond (détaché)
docker compose -f infra/docker-compose.dev.yml up --build -d

# Visualisation des logs du backend uniquement
docker compose -f infra/docker-compose.dev.yml logs -f backend
```

### 4. Paiements Wave et Orange Money avec NabooPay

Le backend utilise l'API NabooPay v2 pour créer un checkout hébergé. En local,
`PAYMENT_SANDBOX=True` simule le paiement. Pour activer le flux réel, renseigner
dans `infra/env/backend.env` :

```dotenv
PAYMENT_SANDBOX=False
NABOOPAY_API_KEY=<clé API NabooPay>
NABOOPAY_BASE_URL=https://api.naboopay.com
NABOOPAY_WEBHOOK_SECRET=<secret du webhook NabooPay>
```

Déclarer ensuite dans le tableau de bord NabooPay l'URL publique
`https://votre-domaine.example/api/payments/webhooks/naboopay/`. Le webhook
doit être en HTTPS ; le serveur vérifie `X-Signature`, le montant XOF et ignore
les notifications déjà traitées. Documentation :
[API NabooPay v2](https://docs.naboopay.com/api-reference) et
[webhooks](https://docs.naboopay.com/api-reference/webhooks).

Les commandes non payées réservent le stock pendant 30 minutes. En production,
faire fonctionner Celery worker et Beat : la tâche est planifiée toutes les
5 minutes. La commande suivante permet aussi une exécution manuelle :

```bash
python manage.py expire_pending_payments
```

Un paiement confirmé après expiration reprend le stock seulement s'il reste
disponible. Si la commande est annulée ou le stock épuisé, l'encaissement est
conservé et une demande de remboursement est créée. Le remboursement reste à
effectuer manuellement puis à confirmer dans l'administration.

L'écran Abonnements permet de reprendre ou d'annuler un paiement en attente,
y compris après rechargement. Dans le catalogue, désactiver un produit le
retire de la vente en conservant ses variantes et l'historique des commandes.

Ne jamais mettre la clé API ou le secret de webhook dans le frontend.

---

## 🌐 Adresses des Services et Consoles

Une fois la stack démarrée, les services suivants sont accessibles :

### 🚀 Points d'entrée Utilisateurs & API
* **Boutique et espaces vendeur (React/Vite) :** [http://localhost:3010](http://localhost:3010)
* **API Backend Django (DRF) :** [http://localhost:8080/api/](http://localhost:8080/api/)
* **Administration Django :** [http://localhost:8080/admin/](http://localhost:8080/admin/)
* **Nginx Reverse Proxy (Global) :** [http://localhost:8081](http://localhost:8081)
  * `/` -> Redirige vers le Frontend
  * `/api/` -> Redirige vers le Backend (API)
  * `/admin/` -> Redirige vers l'Administration Django

### 📊 Stockage de Données & Outils d'Administration
* **Base de données PostgreSQL :** Accessible sur le port `5433` de la machine hôte
* **Interface PgAdmin :** [http://localhost:5051](http://localhost:5051) (Login par défaut : `admin@sunumall.com` / `admin`)
* **Console Web MinIO (S3) :** [http://localhost:9011](http://localhost:9011) (identifiants configurés dans `infra/env/minio.env`)
* **API S3 MinIO (Stockage Media) :** [http://localhost:9010](http://localhost:9010)

---

## 📈 Monitoring et Supervision

Les conteneurs Prometheus et Grafana sont fournis, mais leur présence ne constitue pas une supervision de production. La configuration versionnée collecte uniquement les métriques de Prometheus lui-même ; les exporters, alertes et tableaux de bord applicatifs restent à brancher.

* **Prometheus :** [http://localhost:9091](http://localhost:9091) — Configuration minimale ; collecte applicative et base de données à configurer.
* **Grafana :** [http://localhost:3031](http://localhost:3031) — Permet de visualiser les métriques collectées via des tableaux de bord. (Identifiants : `admin` / mot de passe configuré dans Grafana).
* **Centralisation des logs :** Loki/Promtail ne sont pas déployés par les fichiers Compose versionnés.

---

## 🗄️ Gestion de la Base de Données et Sauvegardes

Des scripts automatisés sont à votre disposition dans le dossier `infra/scripts/` :

* **Exécuter les migrations Django :**
  ```bash
  docker compose -f infra/docker-compose.dev.yml exec backend python manage.py migrate
  ```
* **Sauvegarder la base de données et les fichiers médias (MinIO) :**
  ```bash
  bash infra/scripts/backup.sh
  ```
  *(Crée une archive SQL et tar.gz dans un dossier `backups/`)*
* **Restaurer une sauvegarde :**
  ```bash
  bash infra/scripts/restore.sh YYYYMMDD_HHMMSS --confirm-restore
  ```

---

## 🤝 Workflow Git et Règles de Contribution

Pour maintenir un code propre et éviter les conflits dans le mono-repo, toute l'équipe doit respecter le workflow suivant :

### 1. Stratégie de Branches (Gitflow)
* `main` : Contient le code stable en production. Aucun commit direct n'est autorisé.
* `develop` : Branche d'intégration. C'est à partir d'elle qu'on crée les branches de fonctionnalités et que l'on merge.
* `feature/<nom-fonctionnalite>` : Branche de travail créée depuis `develop`.

### 2. Règles de Commit (Conventional Commits)
Le format des messages de commit doit suivre le schéma suivant : `type(zone): description courte`

Exemples :
* `feat(backend): ajoute le modèle CustomUser avec 4 rôles`
* `fix(frontend): résout le problème de chargement du panier`
* `chore(infra): intègre Grafana Loki dans docker-compose`
* `docs(readme): met à jour le guide de démarrage de l'environnement`

### 3. Processus de Pull Request (PR)
1. Poussez votre branche feature sur GitHub et ouvrez une PR ciblant `develop`.
2. Complétez la description en expliquant le *quoi*, le *pourquoi* et la méthode de test.
3. Attendez le passage réussi des tests automatiques sur la CI (GitHub Actions).
4. Obtenez l'approbation d'un des relecteurs responsables désignés dans le fichier `CODEOWNERS`.
5. Fusionnez la PR en mode *Squash and Merge*.

## Revue approfondie du 5 septembre 2026

Voir [le rapport, les mesures et les limites](docs/audit-approfondi-2026-09-05.md) et [les scripts de reproduction](backend/tools/README.md). Les contrôles locaux ne valent pas validation du déploiement distant.

### Sessions web et mise en production

Le navigateur conserve uniquement le jeton d'accès en mémoire. Le renouvellement utilise un cookie HttpOnly et les routes `/api/auth/browser/`, protégées par CSRF. Les anciens jetons du localStorage sont effacés : une reconnexion sera nécessaire lors de la migration. Les routes JWT JSON existantes restent disponibles aux autres clients.

Préférer frontend et API sous le même domaine, via le reverse proxy ; le Compose de production construit maintenant le frontend avec `/api`. Pour des sites distincts (GitHub Pages et Railway, par exemple), configurer `AUTH_REFRESH_COOKIE_SAMESITE=None`, HTTPS et les origines exactes `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS`. Cela aligne aussi le cookie CSRF. Les navigateurs bloquant les cookies tiers peuvent toujours empêcher cette configuration de fonctionner : un domaine commun évite cette dépendance.

Le mode production exige une clé Django aléatoire d'au moins 50 caractères, les hôtes autorisés, une URL frontend HTTPS et un backend email autre que console. Configurer SMTP réellement ; l'audit a utilisé des emails en mémoire. Redis doit être joignable : les actions sensibles échouent avec 503 si leur compteur partagé ne peut pas être contrôlé. `TRUSTED_PROXY_COUNT` doit correspondre aux proxies de confiance qui réécrivent les en-têtes entrants.

Le proxy de production exige `infra/nginx/ssl/fullchain.pem` et `privkey.pem` ; la configuration locale reste en HTTP. Le renouvellement des certificats reste à organiser. Les identifiants `minioadmin` des exemples sont réservés au développement.

Le stockage utilise désormais `STORAGES` de Django. Créer le bucket S3/MinIO, configurer son accès public aux images et `MINIO_PUBLIC_ENDPOINT`. Si des médias avaient été écrits sur le disque local par l'ancienne configuration ignorée, les transférer au bucket en préservant les clés avant la bascule ; aucune donnée existante n'a été déplacée automatiquement.

Appliquer les migrations versionnées après sauvegarde. Railway exécute désormais `python manage.py migrate --noinput` comme commande de pré-déploiement et interrompt la mise en ligne si elle échoue. Vérifier d'abord les anciens stocks négatifs, réservations supérieures au stock et lignes de commande/paiement dupliquées : les migrations les détectent avec un message explicite, refusent les nouvelles contraintes et ne corrigent pas arbitrairement les données. `checkout_key` est un UUID facultatif : réutiliser la même clé et le même contenu lors d'une reprise réseau retourne la commande existante (200) ; un contenu différent retourne 409. Les clients sans clé conservent le comportement précédent.

Le fichier `infra/env/backend.env` alimente Django. Les fichiers `infra/env/minio.env` et `infra/env/grafana.env` alimentent uniquement les services correspondants afin de ne pas leur transmettre les secrets du backend. Les identifiants MinIO des deux fichiers doivent correspondre.

Les scripts `infra/scripts/` fonctionnent indépendamment du dossier courant. Les sauvegardes sont privées (`umask 077`) et les fichiers incomplets restent temporaires. Pour une sauvegarde cohérente DB/médias, suspendre les écritures ; pour une restauration, arrêter aussi MinIO. Restaurer d'abord sur une copie et contrôler le résultat ; les scripts n'effectuent pas une restauration atomique entre PostgreSQL et le système de fichiers. Externaliser et chiffrer les archives, puis tester régulièrement leur restauration.

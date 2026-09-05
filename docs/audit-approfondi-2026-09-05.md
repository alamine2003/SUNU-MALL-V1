# SUNU MALL — Revue approfondie du 5 septembre 2026

Travail effectué dans le clone SUNU MALL placé dans Documents. Cette revue prolonge les corrections précédentes et préserve les changements qui existaient déjà dans le clone. La réussite des contrôles locaux ne constitue pas une validation du déploiement distant.

**Conclusion : le socle web/API est sensiblement plus robuste, mais la mise en production complète ne peut pas encore être déclarée validée.** Le scénario de 30 clients passe ; les dernières unités ne sont pas survendues. Les paiements réels, la supervision, la restauration et la mise à niveau mobile demandent encore du travail explicite.

## Périmètre et preuves

Lecture des modules Django, modèles, permissions, serializers, API, composants et stores React, application Expo, dépendances, CI/CD, Docker, nginx et scripts d'exploitation. Les corrections importantes sont vérifiées par tests automatisés, requêtes HTTP sur PostgreSQL, concurrence entre connexions réelles et parcours dans le navigateur. Le scan textuel est un complément ; il ne constitue ni un audit exhaustif de l'historique Git ni une certification d'absence de vulnérabilité.

| Vérification finale | Résultat |
|---|---|
| Backend PostgreSQL, pytest | 127 tests réussis en 34,35 s ; 15 avertissements |
| Ruff sur les applications et migrations manquantes | Réussite ; aucune migration manquante |
| Couverture pytest-cov | 86 % du périmètre instrumenté, qui inclut aussi des tests ; pas une couverture métier exhaustive |
| Frontend | 32 tests réussis ; lint, typage et build réussis, dont build sous `/SUNU-MALL-V1/` |
| Mobile | Typage, lint, 2 tests et exports JavaScript/Hermes Android et iOS réussis |
| Images Docker backend et frontend | Constructions réussies ; dépendances de développement auditées côté backend |
| Sécurité Django production | `check --deploy --tag security --fail-level WARNING` réussi avec paramètres fictifs isolés |
| Schéma OpenAPI | Le contrôle complet de déploiement signale 45 avertissements : dette documentée, pas un contrôle intégral vert |
| nginx HTTPS et scripts shell | `nginx -t` réussi avec certificat local jetable ; syntaxe Bash vérifiée |
| Dépendances | Python : 0 avis connus après audit ; web : 0 ; mobile : 39, dont 6 élevés, 31 modérés et 2 faibles |

Les nombres de dépendances désignent des résultats de scanners datés, parfois propagés aux dépendances parentes ; ce ne sont pas autant de vulnérabilités indépendantes exploitables dans l'application. L'audit Python final ajoute seulement l'outil d'audit dans un conteneur jetable ; le pip corrigé est bien installé par le Dockerfile.

Preuves : [contrôles finaux](audit/validation.json), [charge finale](audit/fixed.json), [référence avant cette revue](audit/baseline.json), [index et plan SQL](audit/database-review.json), [limitation avant](audit/rate-limit-before.json) et [après](audit/rate-limit-after.json), [Python](audit/backend-dependencies-after.json), [web](audit/frontend-dependencies.json), [mobile](audit/mobile-dependencies-after.json), [scan textuel](audit/static-scan.json), [reproduction](../backend/tools/README.md).

## 1. Problèmes critiques découverts ou réexaminés

Les anomalies de stock et de paiement de la revue précédente étaient déjà corrigées dans la référence initiale de cette campagne. Elles ont été réexaminées et leur couverture renforcée ; les chiffres de comparaison ne représentent donc pas une version historique entièrement vulnérable.

| Gravité | Problème → Cause → Risque → Correction appliquée → Résultat |
|---|---|
| **CRITIQUE** | Survente / succès tardif après annulation → transitions et réservations concurrentes → paiement encaissé sans marchandise ou consommation du stock d'autrui → transactions, verrouillage ordonné des variantes/inventaires, état de réservation explicite, demande unique de remboursement lorsque la commande ne peut être honorée → 30 acheteurs sur 5 unités : exactement 5 ventes, 5 commandes, 5 paiements, stock et réservations à zéro. |
| **ÉLEVÉ** | Commande créée deux fois après une réponse perdue → absence de clé de reprise → double réservation et double commande pour une intention → UUID `checkout_key` facultatif, empreinte du contenu, unicité par acheteur et verrou par acheteur → 8 soumissions simultanées identiques : une création 201, sept reprises 200, une commande et un paiement ; contenu différent : 409. |
| **ÉLEVÉ** | Deux appels d'initiation au prestataire → vérification/réutilisation non sérialisée → plusieurs sessions de paiement → verrou du paiement pendant l'initiation et réutilisation de la référence → deux requêtes concurrentes ne déclenchent qu'un appel fournisseur dans le test. Une réponse fournisseur perdue reste une limite distincte. |
| **ÉLEVÉ** | Totaux de vente incohérents → agrégat calculé avant verrouillage du total journalier → une écriture ancienne remplace un total plus récent → verrouillage du total boutique/jour avant agrégation → huit paiements simultanés donnent exactement huit ventes et le montant attendu. |

## 2. Vulnérabilités de sécurité

| Gravité | Problème → Cause → Risque → Correction appliquée → Résultat |
|---|---|
| **ÉLEVÉ** | Refresh JWT persistant en localStorage → accessible aux scripts de la page → vol de session en cas de XSS → refresh en cookie HttpOnly, access token en mémoire, suppression du stockage historique et contrôle CSRF de toutes les écritures navigateur → rotation, origine étrangère refusée, logout et absence de refresh dans le JSON testés. |
| **ÉLEVÉ** | Limite de connexion dépassable en parallèle → compteur DRF lu puis réécrit sans atomicité, même avec Redis → protection brute force affaiblie → compteur Redis Lua atomique pour les scopes sensibles, fenêtre fixe et refus 503 si Redis indisponible → avant : 12 réponses 400 ; après : 10 réponses 400 et 2 réponses 429 pour une limite de 10/minute. |
| **ÉLEVÉ** | Produits d'une boutique suspendue encore accessibles par certains chemins → filtres de visibilité dispersés → contournement de la suspension → sélection commune pour catalogue, variantes et assistant → lectures publiques refusées, accès propriétaire/admin conservé et testé. |
| **ÉLEVÉ** | Changement de mot de passe via le flux invité sur un compte existant → contrôle insuffisant du type de compte → remplacement sans mot de passe actuel → conversion réservée aux comptes sans mot de passe utilisable → refus 400 et mot de passe inchangé dans le test. |
| **ÉLEVÉ** | Secrets/configurations de développement pouvant entrer dans une image ou un lancement de production → `COPY . .` sans exclusions et paramètres faibles → fuite ou environnement mal protégé → `.dockerignore`, exigences de secret/hôtes/HTTPS/email, refus des identifiants MinIO de développement, réglages prod imposés aux services Compose → image construite ; contrôle sécurité Django réussi avec configuration de test dédiée. |
| **MOYEN** | Image valide avec contenu ajouté ou métadonnées indésirables → simple reconnaissance du format → contenu dangereux hébergé sous un nom fourni par le client → décodage puis réencodage JPEG/PNG/WebP, nom et type maîtrisés, limites de taille/pixels → test d'image avec suffixe HTML réussi. |
| **MOYEN** | Email privé du propriétaire exposé publiquement → champ serializer sans contrôle du lecteur → collecte d'emails de connexion → champ nul pour le public et les autres comptes, présent pour propriétaire/admin → tests de visibilité réussis. |
| **MOYEN** | UUID mal formé, valeurs IA invalides ou réponse fournisseur inattendue → validations incomplètes → erreurs 500 et détails internes → validations DRF, prix finis, erreurs fournisseur génériques, webhook JSON objet obligatoire → régressions couvertes. |

Les requêtes métier examinées utilisent l'ORM ; les rares `cursor.execute` ajoutés servent à la mesure SQL ou au timeout des tests et ne concatènent pas d'entrée utilisateur. Aucun usage de `dangerouslySetInnerHTML` ni secret fournisseur correspondant aux motifs recherchés n'a été trouvé dans les sources examinées. Le `eval` signalé par le scan est l'exécution d'un script Redis constant, pas du JavaScript ou Python fourni par un utilisateur. Les données récemment consultées peuvent rester en localStorage ; les jetons de session n'y sont plus conservés.

Les contrôles d'accès existants entre acheteurs, vendeurs, livreurs et administrateurs ont été conservés et retestés. Le cookie HttpOnly n'élimine pas à lui seul le risque XSS : un script exécuté dans l'origine pourrait encore agir avec les droits de la page.

**Limites de session :** un domaine commun frontend/API est préférable. GitHub Pages et Railway sur des sites distincts exigent `SameSite=None`, HTTPS, CORS/CSRF exacts et l'acceptation des cookies tiers. Les cookies CSRF et refresh utilisent désormais la même politique. Les JWT JSON restent disponibles pour compatibilité avec les autres clients. La révocation d'un refresh ne révoque pas instantanément un access token déjà émis.

Références de configuration : [stockage Django](https://docs.djangoproject.com/en/5.2/ref/settings/#storages), [cache Redis Django](https://docs.djangoproject.com/en/5.2/topics/cache/#redis), [protection CSRF Django](https://docs.djangoproject.com/en/5.2/ref/csrf/).

## 3. Code mort supprimé

**FAIBLE — Maintenance :** suppression de cinq permissions sans appelant, de méthodes utilitaires de catalogue non utilisées, de chemins redondants de mutation du stock, de `Wishlist.remove_product`, de la surcharge triviale de `User.check_password` et du helper web `apiPut`. Le [manifeste](audit/removed-code.json) identifie les méthodes retirées.

Retrait des dépendances de développement inutilisées : factory-boy, black, isort, django-debug-toolbar et ipython. Pytest et pytest-django ont été actualisés. Les modèles persistants dormants et leurs migrations ont été conservés : supprimer des tables contenant potentiellement des données n'aurait pas été un simple nettoyage de code.

## 4. Parties simplifiées

**MOYEN — Lisibilité :** une règle commune de visibilité des produits remplace des filtres divergents. Les statuts comptant comme ventes utilisent `Order.SALES_STATUSES`. Le panier charge ses lignes une fois pour les sérialiser et calculer le total. Les abonnements ne parcourent plus tous les utilisateurs à chaque consultation : l'entretien global passe par une tâche planifiée, avec notification idempotente.

Les tâches d'expiration des paiements et d'entretien des abonnements utilisent Celery/Beat déjà présents. Aucune nouvelle file, aucun microservice et aucun framework supplémentaire n'ont été introduits.

## 5. Problèmes SOLID corrigés

**MOYEN — Responsabilités :** les transitions de paiement sont sorties des vues HTTP ; webhook, simulation et expiration appellent le même service. La commande de maintenance n'importe donc plus une vue. Les sélections de catalogue partagées sont isolées des permissions HTTP et de la sérialisation. Le transport des sessions web est isolé du store React, ce qui réduit les imports croisés.

Les validations restent dans les serializers et les invariants transactionnels dans les modèles/services concernés. Aucun repository générique, interface sans second usage ou couche supplémentaire n'a été ajouté pour appliquer SOLID formellement.

## 6. Fichiers et composants découpés

| Ancien point de concentration | Découpage utile |
|---|---|
| Vues du catalogue, plus de 500 lignes | `catalog/views/products.py`, `stores.py`, `categories.py`, `reviews.py`, `helpers.py` ; exports conservés dans `__init__.py` |
| Transitions mêlées aux endpoints de paiement | `payments/services.py`, partagé avec la commande d'expiration et les tâches |
| Authentification navigateur mêlée à l'API générale | `auth/browser.py`, `auth/throttles.py`, `frontend/src/lib/session.ts` |
| Scripts de diagnostic dans le produit | `backend/tools/`, exclus de l'image livrable |

**FAIBLE — Dette conservée :** certains modèles et écrans restent longs. Ils n'ont pas été découpés uniquement pour réduire leur nombre de lignes. Le chargement différé des pages web établi lors de la revue précédente reste en place.

## 7. Structures de données améliorées

- **MOYEN :** `set` pour dédupliquer les catégories, repérer les variantes répétées et exclure les produits déjà recommandés ; dictionnaires pour rétablir un classement sans recherche linéaire répétée.
- **MOYEN :** préchargement relationnel des images, variantes, inventaires, lignes de commande, livraison et paiement ; listes bornées à la dernière demande de remboursement et à la dernière position GPS.
- **ÉLEVÉ :** unicité relationnelle `(order, product_variant)` et `(customer, checkout_key)` ; contrôle des quantités en base, pas seulement dans le formulaire.
- **MOYEN :** compteur partagé Redis pour les protections sensibles ; pas de cache de stock susceptible de devenir une source de vérité périmée.
- Pagination existante de 20 éléments conservée sur les listes standard. Les collections spécifiques non paginées restent à surveiller à grande volumétrie ; pas de Queue/Stack introduite sans besoin.

## 8. Problèmes de base de données

| Gravité | Problème → Cause → Risque → Correction appliquée → Résultat |
|---|---|
| **MOYEN** | N+1 catalogue et commandes → relations lues dans les serializers → coût croissant avec chaque ligne → `select_related` / `prefetch_related` ciblés → catalogue : maximum 29 → 7 SQL ; liste de commandes : 76 → 7 sur le scénario. |
| **ÉLEVÉ** | Invariants de stock non garantis en base → validations applicatives seules → données incohérentes via une autre écriture → contraintes quantité ≥ 0, réservation ≥ 0 et réservation ≤ quantité → violations refusées dans les tests. |
| **ÉLEVÉ** | Suppression cassant les historiques → relations destructives ou erreur PROTECT non traitée → perte de traçabilité / 500 → archivage des boutiques et produits, suppression de variante refusée avec message métier → historique conservé et comportement testé. |
| **MOYEN** | Réglage de stockage obsolète ignoré par Django → fichiers écrits au mauvais emplacement → médias absents après remplacement d'un conteneur → `STORAGES` explicite et stockage mémoire correctement surchargé en test → configuration corrigée ; migration des anciens médias à préparer avant bascule. |

Les index existants de clés étrangères, références prestataire, échéances de paiement et unicité boutique/jour ont été examinés. Les nouvelles contraintes d'unicité créent les index correspondants. Aucun index existant n'a été supprimé sans preuve d'inutilité. Le [plan réel](audit/database-review.json) documente l'agrégat journalier sur la base de test. À forte volumétrie, remplacer `created_at__date` par un intervalle temporel et évaluer un index `(store_id, created_at)` est pertinent ; le test actuel ne justifie pas de prétendre avoir optimisé une base de millions de lignes.

Les migrations ont été générées et appliquées dans les bases isolées. Elles vérifient explicitement les inventaires invalides, quantités non positives et doublons de livraison, ligne ou paiement avant d'ajouter les contraintes. Un jeu historique incohérent interrompt donc le pré-déploiement avec les identifiants concernés : examiner et réparer ces données après rapprochement métier, puis relancer. Railway applique les migrations dans une commande de pré-déploiement ; une erreur empêche la nouvelle version de démarrer.

## 9. Problèmes de concurrence

| Scénario | Vérification et résultat |
|---|---|
| 30 clients sur les 5 dernières unités | 5 commandes créées et payées, 25 refus métier 400, aucune réservation restante, aucune quantité négative |
| 8 ajouts au même panier | Quantité finale exactement 8, aucun ajout perdu |
| Ajout pendant un checkout partiel | Verrou commun du panier avant les stocks ; seules les quantités achetées sont retirées, l’ajout concurrent reste présent |
| 8 confirmations de paiements | Total quotidien exact, sans écrasement d'un agrégat récent |
| 8 reprises du même checkout | Une commande, un paiement, une réservation ; réutilisation avec autre contenu refusée |
| Deux initiations d'un paiement | Un seul appel prestataire simulé |
| Paniers A/B et B/A | Ordre de verrouillage déterministe, régression couverte |
| Paiement après annulation/expiration | Pas de réactivation abusive ; reprise du stock disponible ou demande de remboursement unique |
| Livraison d'une commande impayée / réaffectation | Affectation refusée ; commande et livraison verrouillées, droits revérifiés après attente du verrou |

**ÉLEVÉ — Limite externe :** le verrou local ne résout pas un timeout survenu après création d'une transaction chez le prestataire mais avant réception de sa référence. Une garantie de non-duplication externe exige le mécanisme d'idempotence/réconciliation du fournisseur et un test contractuel. Aucun paiement réel n'a été envoyé pendant cette revue.

La clé de checkout est facultative pour préserver les anciens clients. La protection contre les reprises ne s'applique pas aux requêtes qui l'omettent. Le web la conserve pendant la tentative courante ; une nouvelle tentative volontaire reçoit une nouvelle clé.

## 10. Résultats du test avec 30 clients

Deux vendeurs sont inscrits et vérifiés via l'API. L'administrateur de test approuve leurs boutiques et crée trois catégories globales ; les vendeurs les utilisent pour leurs produits. Cette séparation correspond aux droits actuels : le vendeur ne possède pas la taxonomie globale. Chaque vendeur configure sa boutique, crée six produits avec prix/variantes/stocks et les publie.

Trente acheteurs démarrent ensemble. Ils consultent boutiques et catégories, recherchent, ouvrent deux fiches, ajoutent les deux produits au panier, modifient les quantités, commandent, confirment un paiement sandbox et consultent leurs commandes. Dix acheteurs effectuent ce parcours dans les deux boutiques : **40 commandes pour 30 clients, 520 requêtes**. Les achats multi-boutiques restent des commandes distinctes.

| Clients simultanés | Requêtes | Durée | Débit | p50 | p95 | p99 | Maximum | Erreurs inattendues |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 520 | 1,940 s | 268,04/s | 89 ms | 173 ms | 180 ms | 182 ms | 0 |
| 60 | 1 040 | 3,757 s | 276,82/s | 168 ms | 359 ms | 379 ms | 384 ms | 0 |
| 120 | 2 080 | 7,611 s | 273,29/s | 343 ms | 695 ms | 714 ms | 724 ms | 0 |
| 300 | 5 200 | 20,241 s | 256,90/s | 905 ms | 1 914 ms | 1 970 ms | 1 984 ms | 0 |

Banc : PostgreSQL 16, Redis 7, quatre workers Gunicorn synchrones, 2 CPU et 1 Gio pour le conteneur API. **Le générateur tourne dans ce même conteneur** et consomme donc une partie des ressources mesurées. Le réseau est local et le catalogue petit ; ces résultats ne sont pas une promesse de capacité de production.

Navigateur réel : connexion, restauration de session après réouverture, fiche produit, ajout au panier et quantité 2 / total 2 000 FCFA vérifiés. Le parcours d'adresse, retrait et paiement sandbox est aussi contrôlé. Une vérification de fiche a été faite pendant un palier de lecture de 30 clients ; ce contrôle ponctuel ne mesure pas les Web Vitals et ne prouve pas que tout le parcours navigateur est resté sous charge continue.

## 11. Points de rupture et goulots observés

**MOYEN — Dégradation de latence mesurée :** si l'objectif opérationnel retenu est un p95 inférieur à une seconde, il est respecté à 120 clients et dépassé à 300. Le seuil se situe entre ces deux paliers ; aucun palier intermédiaire ne permet de le préciser davantage. Le débit n'augmente pratiquement plus au-delà de 60 clients.

Sur les quatre paliers et la course finale (33,694 s), le conteneur consomme environ **62,49 secondes CPU**, soit **1,85 cœur en moyenne sur une limite de 2**, et cumule **9,34 s de temps de throttling cgroup**. La mémoire atteint **511,7 Mio**. Ces mesures incluent le générateur ; elles indiquent une pression CPU sur le banc, sans isoler précisément la part Django de celle du client de charge.

PostgreSQL : au maximum **6 connexions**, **5 actives** et **1 en attente de verrou**, selon un échantillonnage de 200 ms. Aucun épuisement de connexions ou deadlock n'a été observé. Les p95 de temps SQL total par requête vont de 14,7 à 17,1 ms ; des requêtes individuelles atteignent environ 30 ms. Les transactions attendent parfois les stocks ou le total boutique/jour.

Les confirmations de paiement, la liste des commandes et le checkout sont les endpoints les plus coûteux en latence agrégée. Leurs p95 mélangent les quatre paliers et ne doivent pas être lus comme un résultat propre aux seuls 30 clients.

**Aucun point de rupture dure n'a été atteint jusqu'à 300 clients** : pas de 500, timeout, crash ou OOM dans ce scénario. Rien n'est établi au-delà de cette charge. Les dépendances externes ont été simulées : les appels synchrones à NabooPay, SMTP et l'IA peuvent occuper les quatre workers et dégrader le service bien plus tôt si ces fournisseurs deviennent lents. C'est un risque déduit du code, pas un seuil mesuré ici.

## 12. Limites actuelles de l'application

- **ÉLEVÉ :** audit mobile encore à 39 signalements, dont six élevés liés à la chaîne React Native/Metro et à `image-size`. Le critique `tar` est corrigé, ainsi que le parseur XML compatible. Une montée d'Expo/React Native est nécessaire pour traiter proprement le reste ; les exports ne remplacent pas des builds natifs signés ni des tests sur appareils.
- **ÉLEVÉ :** paiements Wave/Orange Money, signatures réelles de webhook, délais prestataire et remboursements effectifs non validés en environnement fournisseur. Le remboursement est une demande/confirmation administrative, pas une émission automatique d'argent.
- **ÉLEVÉ :** supervision applicative et alertes absentes de la configuration Prometheus livrée. Les scripts de sauvegarde/restauration ont été réparés, mais une restauration de bout en bout n'a pas été exécutée sur la pile complète.
- **MOYEN :** l'application mobile reste un socle limité ; elle n'a pas la couverture fonctionnelle du web. Le GPS ne diffuse pas en temps réel via WebSocket ; SMS, génération de certains rapports et statistiques de trafic restent incomplets.
- **MOYEN :** certaines adresses et données descriptives historiques restent des références modifiables, plutôt que des instantanés immuables de commande. La suppression/modification d'adresse mérite un traitement métier dédié.
- **MOYEN :** aucun test d'endurance, de panne réseau prolongée, de perte du cache ou de gros catalogue n'a été exécuté à l'échelle de production. Redis en panne est couvert au niveau du throttle unitaire ; cela n'est pas un exercice de bascule de toute la plateforme.
- **MOYEN :** le schéma OpenAPI ne décrit pas correctement plusieurs APIViews/actions et certains champs calculés. Le contrôle complet signale 45 avertissements, notamment serializers non déduits et faux utilisateurs anonymes lors de la génération.

## 13. Optimisations réalisées

| Opération | Maximum SQL initial | Maximum SQL final |
|---|---:|---:|
| Liste de produits | 29 | 7 |
| Fiche produit | 7 | 5 |
| Liste des commandes | 76 | 7 |
| Détail de commande | 15 | 6 |
| Modification d'une ligne de panier | 14 | 9 |
| Checkout | 38 | 38 |
| Confirmation de paiement | 46 | 50 |

La confirmation ajoute des opérations de cohérence ; elle n'est pas présentée comme une optimisation du nombre de requêtes. Le recalcul inutile des ventes au checkout en attente a été supprimé ; les opérations de reprise idempotente et de conservation du panier concurrent compensent ce gain en nombre de requêtes. Les compteurs panier/favoris sont désormais alimentés par les réponses API, y compris après checkout ; le compteur préserve les articles de l’autre boutique et ignore une réponse du compte précédent (tests ajoutés). Les rafraîchissements de token concurrents sont mutualisés côté web et les réponses de recherche anciennes ne remplacent plus les résultats récents.

La référence initiale était plus rapide sur certains paliers : par exemple environ 170 ms de p95 à 30 clients contre 173 ms sur la dernière mesure après correction. Elle utilisait des limites fortement relevées et un cache local. **La baisse des N+1 est démontrée ; un gain global de débit ne l'est pas.** Les contrôles partagés et les garanties de concurrence ont un coût assumé.

## 14. Optimisations recommandées, non nécessaires immédiatement

**MOYEN :** refaire les mesures avec générateur séparé, plusieurs tailles de catalogue et palier de 30–60 minutes ; définir un SLO et suivre p95/p99, erreurs, saturation CPU, âge des paiements en attente et attentes de verrous.

**MOYEN :** lorsque le volume le justifie, examiner les plans de recherche texte et d'agrégation, les index composites ciblés, puis seulement envisager recherche spécialisée, pool de connexions ou cache de catalogue. Le test actuel ne montre pas de saturation PostgreSQL imposant PgBouncer ou des réplicas.

**MOYEN :** déplacer les notifications hors de la réponse HTTP avec reprise contrôlée ; instrumenter les délais prestataires et définir un circuit d'échec. Ne pas conserver un verrou transactionnel long autour d'un appel distant sans stratégie d'idempotence fournisseur.

**FAIBLE :** compléter les annotations OpenAPI, borner les collections spécifiques et détailler les tests UI des espaces vendeur/admin. Un découpage supplémentaire du monolithe ou une architecture microservices n'est pas justifié à ce stade.

## 15. Dette technique restante et évaluation globale

| Dimension | Évaluation après corrections |
|---|---|
| Architecture | Monolithe modulaire adapté ; responsabilités principales mieux séparées, sans nouvelles couches génériques |
| Qualité du code | Améliorée par suppression du code sans usage, validations communes et tests de régression ; documentation API encore incomplète |
| Sécurité | Protections web/API renforcées et testées ; dépendances mobiles, configuration distante et fournisseurs restent à valider |
| Performances | 30 clients passent confortablement sur ce banc ; N+1 principaux réduits ; aucune promesse sur gros catalogue ou réseau réel |
| Scalabilité | Pression CPU et file d'attente visibles, débit plafonné sur 2 CPU ; pas de besoin démontré de distribuer la base |
| Maintenabilité | Services communs, découpage du catalogue, scripts reproductibles et CI élargie ; fonctionnalités amorcées toujours présentes |
| Robustesse production | Meilleure cohérence transactionnelle ; non validée de bout en bout tant que paiement réel, stockage, observabilité, TLS et restauration ne sont pas éprouvés |

Avant livraison : sauvegarder et contrôler les données historiques, appliquer les migrations, préparer les médias S3, choisir une topologie de cookies fonctionnelle, fournir les secrets et certificats, démarrer worker/Beat, valider les fournisseurs et éprouver une restauration. Ces étapes nécessitent l'environnement de déploiement réel ; elles n'ont pas été exécutées sur les services de l'utilisateur.

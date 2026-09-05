# Revue technique SUNU MALL

> Revue historique. La [nouvelle revue approfondie du 5 septembre 2026](audit-approfondi-2026-09-05.md) contient les contrôles et mesures les plus récents.

## État vérifié lors de la revue précédente

- Backend Django : 99 tests passants sur PostgreSQL, lint Ruff et contrôle des migrations sans changement.
- Frontend React/Vite : typage, lint, 25 tests et build passants ; audit npm sans vulnérabilité signalée lors de l'installation.
- Mobile Expo : installation reproductible, typage, lint et 2 tests passants localement ; contrôles ajoutés à la CI.
- Images Docker backend et frontend construites avec succès.
- Le frontend est une SPA Vite unique ; le `seller-dashboard/` annoncé dans
  l'ancienne documentation n'existe pas et a été retiré de l'orchestration.

## Correctifs locaux

### Suite de la revue : 11 anomalies corrigées localement

1. Un succès de paiement après expiration ou échec reprend le stock disponible
   atomiquement, sans consommer les réservations des autres commandes.
2. Un succès après annulation, ou lorsque le stock n'est plus disponible,
   conserve l'encaissement et crée une seule demande de remboursement ; la
   commande reste annulée et aucune livraison n'est déclenchée.
3. Les nouvelles adresses email sont normalisées ; la connexion et le renvoi
   de vérification retrouvent les anciennes adresses avec majuscules. Les
   collisions historiques restent distinguées par leur casse exacte.
4. La suppression d'un produit le désactive et conserve ses variantes et
   l'historique des commandes. L'interface annonce cette désactivation.
5. Un favori peut être retiré même si le produit ou sa boutique est inactif.
6. Un commerçant ne peut plus activer lui-même une boutique suspendue ; les
   transitions passent par les actions d'administration.
7. Le rattachement d'un produit à sa boutique et d'une variante à son produit
   est immuable, ce qui interdit les transferts entre commerçants.
8. Les paniers verrouillent les variantes et stocks dans le même ordre. Un
   test avec deux connexions PostgreSQL couvre les paniers en ordre inverse.
9. Les abonnements en attente peuvent être repris ou annulés après fermeture
   de la fenêtre. Un paiement expiré ou échoué est remplacé ; un succès tardif
   d'un abonnement annulé crée une demande de remboursement. Les contrôles de
   simulation ne sont affichés que pour une session sandbox.
10. Les statistiques globales des utilisateurs sont réservées à l'admin,
    conformément aux permissions déclarées sur l'action.
11. Le résumé et les statistiques journalières utilisent le même périmètre
    de commandes payées ; les commandes en attente et annulées sont exclues.

Ces correctifs ajoutent 23 tests backend et 5 tests d'interaction frontend.
Ils sont vérifiés dans le clone local, sans déploiement. Les prérequis et
fonctionnalités incomplets recensés ci-dessous restent distincts de ces bugs.

### Correctifs précédents

- Intégration NabooPay v2 pour `wave` et `orange_money` : création de
  transaction, checkout hébergé, réutilisation d'une session existante et
  redirection frontend.
- Webhook `POST /api/payments/webhooks/naboopay/` signé par HMAC SHA-256,
  validation de la devise et du montant, confirmation idempotente et
  déclenchement de la livraison seulement après paiement confirmé.
- Protection contre les doubles écritures de transactions et contre le
  traitement d'un remboursement invalide ou déjà terminé.
- Le mode production ne retombe plus silencieusement sur le sandbox pour un
  moyen de paiement inconnu.
- Ajout d'une image Docker frontend Vite et correction des services Compose et
  nginx qui pointaient vers des composants absents.
- Réservation de stock transactionnelle au checkout, commit à la confirmation
  du paiement, libération à l'échec/annulation et expiration des paiements
  abandonnés via `python manage.py expire_pending_payments`.
- Validation des coordonnées GPS, des zones GeoJSON, des horaires de boutique,
  des prix et des fichiers image ; mise à jour des statistiques pour exclure
  les commandes non payées.
- Mise à niveau de React Router, Vite, Vitest et PostCSS ; lazy-loading des
  écrans frontend et contrôle mobile ajouté à la CI.

## À compléter avant la mise en production

### Bloquant métier

- Enregistrer les clés NabooPay dans le gestionnaire de secrets, déclarer le
  webhook HTTPS en production et valider un paiement Wave et Orange Money avec
  les identifiants de test puis de production.
- Ajouter la vérification serveur de la transaction auprès de NabooPay si leur
  compte de production l'exige, puis brancher le remboursement NabooPay au lieu
  de la confirmation manuelle actuelle.
- Le panier et `Order` sont encore mono-boutique alors que le cahier des
  charges promet un panier multi-boutiques.
- Planifier `expire_pending_payments` toutes les 5 à 10 minutes en production
  (cron, Celery Beat ou scheduler Railway) ; le code est prêt mais aucun
  ordonnanceur n'est déclaré dans le dépôt.

### Fonctionnalités incomplètes

- `DeliveryTracking.broadcast`,
  `TrafficStatistic.compute_for_store`, `Report.generate` et
  `SponsoredProduct.spend_today` sont encore des stubs ou des valeurs fixes.
- Les notifications SMS/push, la messagerie live et le suivi GPS temps réel
  n'ont pas de fournisseur ou de canal WebSocket branché.
- Le flux d'authentification implémente email + mot de passe, alors que le CDC
  demande téléphone + OTP pour certains parcours.
- La politique de retours, les délais d'acceptation 24–48 h et le calcul des
  gains livreur ne sont pas encore modélisés complètement.

### Qualité et exploitation

- Les dépendances frontend embarquées en production n'ont plus de vulnérabilité
  haute/critique connue ; les outils Vite/Vitest sont également à jour au
  moment de cette revue.
- La CI ne couvre pas encore les captures E2E, les tests de webhook contre un
  environnement NabooPay de test, ni une vérification de configuration de
  production avec secrets manquants.
- Les comptes par défaut et valeurs d'exemple MinIO/pgAdmin restent réservés
  au développement ; ils doivent être remplacés dans chaque environnement
  déployé.

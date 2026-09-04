# Revue technique SUNU MALL

## État vérifié

- Backend Django : 57 tests passants, contrôle des migrations sans changement.
- Frontend React/Vite : typage, lint, 20 tests et build passants.
- Images Docker backend et frontend construites avec succès.
- Le frontend est une SPA Vite unique ; le `seller-dashboard/` annoncé dans
  l'ancienne documentation n'existe pas et a été retiré de l'orchestration.

## Correctifs livrés

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
- Le stock n'est pas réservé avec verrouillage lors du checkout ; une commande
  abandonnée peut aussi laisser un état métier incomplet.

### Fonctionnalités incomplètes

- `DeliveryZone.contains`, `DeliveryTracking.broadcast`,
  `TrafficStatistic.compute_for_store`, `Report.generate` et
  `SponsoredProduct.spend_today` sont encore des stubs ou des valeurs fixes.
- Les notifications SMS/push, la messagerie live et le suivi GPS temps réel
  n'ont pas de fournisseur ou de canal WebSocket branché.
- Le flux d'authentification implémente email + mot de passe, alors que le CDC
  demande téléphone + OTP pour certains parcours.
- La politique de retours, les délais d'acceptation 24–48 h et le calcul des
  gains livreur ne sont pas encore modélisés complètement.

### Qualité et exploitation

- `npm audit` signale 11 vulnérabilités dans l'arbre frontend ; les dépendances
  doivent être mises à niveau et retestées dans une PR dédiée.
- Le build produit encore un chunk JavaScript supérieur à 500 kB ; le code
  mérite du lazy-loading par espace et par carte.
- La CI ne couvre pas encore les captures E2E, les tests de webhook avec un
  environnement NabooPay de test, ni une vérification de configuration de
  production avec secrets manquants.
- Les comptes par défaut et valeurs d'exemple MinIO/pgAdmin restent réservés
  au développement ; ils doivent être remplacés dans chaque environnement
  déployé.

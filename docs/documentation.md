# Endpoint : statistiques du tableau de bord administrateur

## `GET /api/users/admin/dashboard/stats/`

Retourne les indicateurs affichés sur `/admin` (dashboard administrateur). Réservé aux comptes ayant le rôle **admin** (permission `IsAdmin`) — toute autre requête reçoit une 403.

### Réponse

```json
{
    "users": {
        "total": 20,
        "active": 20,
        "unverified": 3
    },
    "stores": {
        "total": 4,
        "active": 4,
        "pending_review": 0,
        "suspended": 0
    },
    "trend": {
        "new_users": [
            { "date": "2026-07-13", "count": 0 },
            { "date": "2026-07-14", "count": 0 }
        ],
        "new_stores": [
            { "date": "2026-07-13", "count": 0 },
            { "date": "2026-07-14", "count": 2 }
        ]
    }
}
```

### Détail des champs

| Champ | Type | Description |
|---|---|---|
| `users.total` | int | Nombre total d'utilisateurs enregistrés, tous rôles confondus. |
| `users.active` | int | Utilisateurs avec `is_active=True` (compte non désactivé). |
| `users.unverified` | int | Utilisateurs dont l'email n'a pas encore été vérifié (`is_verified=False`). |
| `stores.total` | int | Nombre total de boutiques créées. |
| `stores.active` | int | Boutiques au statut `active` (validées, visibles publiquement). |
| `stores.pending_review` | int | Boutiques au statut `inactive`, en attente de validation admin. |
| `stores.suspended` | int | Boutiques suspendues par un admin. |
| `trend.new_users` | tableau | Nombre de nouveaux comptes créés par jour, sur les 14 derniers jours (rempli à `0` pour les jours sans inscription — pas de trou dans la série). |
| `trend.new_stores` | tableau | Même principe que `new_users`, mais pour les créations de boutiques. |

### Implémentation

- Vue : `UserViewSet.admin_dashboard_stats` — `backend/apps/users/views.py`.
- Les séries `trend.*` sont calculées **côté serveur** via une agrégation SQL (`TruncDate` + `Count`, fonction `_daily_counts`), et non en récupérant une liste d'utilisateurs/boutiques côté client — ça évite qu'une pagination tronquée fausse le graphique une fois la marketplace suffisamment grande (voir commit `cb63c63`).
- Consommé côté frontend par `usersApi.getDashboardStats()` (`frontend/src/api/users.ts`) et affiché sur `frontend/src/pages/admin/index.tsx` via le composant `TrendChart`.

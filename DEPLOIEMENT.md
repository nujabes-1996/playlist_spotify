# 🚀 Déploiement de bout en bout — playlist_spotify

Guide complet et autonome : d'un serveur vierge jusqu'à l'application en ligne en HTTPS.
Compter ~15 minutes.

---

## 1. Vue d'ensemble

Deux conteneurs Docker orchestrés par `docker-compose.prod.yml` :

```
                  ┌──────────────────────────────────────────┐
   Internet       │  Serveur                                   │
  ───────────►    │                                            │
   :80 / :443     │   ┌─────────────┐      /api/*   ┌────────┐ │
                  │   │  web (Caddy) │ ───────────► │backend │ │
                  │   │  HTTPS auto  │              │FastAPI │ │
                  │   │  sert le SPA │              │uvicorn │ │
                  │   └─────────────┘    / + assets └────┬───┘ │
                  │                                       │     │
                  │                              data/app.db    │
                  │                              (SQLite, volume)│
                  └──────────────────────────────────────────┘
```

- **`web`** (Caddy) — unique point d'entrée. Obtient et renouvelle **automatiquement** le
  certificat TLS (Let's Encrypt), sert le frontend React buildé, et proxifie `/api` vers le backend.
- **`backend`** (FastAPI) — **non exposé** sur Internet, joignable uniquement par Caddy via le
  réseau Docker. 1 seul worker (APScheduler + SQLite).
- **Données** — un seul fichier SQLite `data/app.db` (config, playlists, blacklist, token Spotify).
  **Pas de base de données séparée à installer.**

---

## 2. Prérequis

### a. Le serveur
- Une machine Linux (VPS, Raspberry Pi, etc.) avec un accès SSH.
- **Docker + Docker Compose v2**. S'ils ne sont pas installés :
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER     # puis se reconnecter en SSH
  docker compose version            # doit afficher v2.x
  ```

### b. Le domaine (DNS)
- Un nom de domaine, ex. `playlist.mondomaine.fr`.
- Un enregistrement **A** (et **AAAA** si IPv6) pointant vers l'IP publique du serveur.
- Vérifier la propagation :
  ```bash
  dig +short playlist.mondomaine.fr   # doit renvoyer l'IP du serveur
  ```

### c. Le pare-feu
- **Ports 80 et 443 ouverts** depuis Internet (obligatoire : Let's Encrypt valide le certificat
  via ces ports).
  ```bash
  # exemple avec ufw
  sudo ufw allow 80
  sudo ufw allow 443
  ```

### d. Une app Spotify
- Créée sur https://developer.spotify.com/dashboard.
- Récupérer `Client ID` et `Client Secret` (ils seront saisis dans l'app, pas dans un fichier).

---

## 3. Récupérer le code sur le serveur

```bash
git clone <url-du-repo> playlist_spotify
cd playlist_spotify
```

---

## 4. Configurer le déploiement

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

Renseigner :
```ini
DOMAIN=playlist.mondomaine.fr      # ton domaine exact
ACME_EMAIL=toi@exemple.fr          # email Let's Encrypt (alertes d'expiration)
SESSION_SECRET=<valeur générée>    # voir ci-dessous — OBLIGATOIRE en prod
```

Générer un `SESSION_SECRET` fort et aléatoire, puis le coller dans `.env.prod` :
```bash
openssl rand -hex 32
```

> ⚠️ **`SESSION_SECRET` est obligatoire en prod.** Le cookie de session est *signé, pas
> chiffré* : sans secret fort (ou s'il reste la valeur de dev), n'importe qui pourrait forger
> une session et usurper un compte. Le backend **refuse de démarrer** si `SESSION_SECRET` est
> absent ou égal au défaut de dev. Ne jamais committer une vraie valeur.
>
> ⚠️ Aucun credential Spotify ici — chaque utilisateur les saisit sur l'écran de connexion
> de l'app. Le fichier `.env.prod` est gitignoré.

---

## 5. Déclarer la Redirect URI côté Spotify

Dashboard Spotify → ton app → **Settings** → **Redirect URIs**, ajouter **exactement** :

```
https://playlist.mondomaine.fr/api/v1/auth/callback
```

(Remplacer par ton domaine. Doit correspondre à `SPOTIFY_REDIRECT_URI`, injecté automatiquement.)

---

## 6. Lancer le déploiement

```bash
make deploy            # équivalent : ./scripts/deploy.sh
```

Cette commande build les images puis démarre les conteneurs.
Caddy obtient le certificat TLS dans les secondes qui suivent. Vérifier :

```bash
make logs              # chercher : "certificate obtained successfully"
make ps                # les 2 conteneurs doivent être "running"/"healthy"
```

---

## 7. Premier lancement de l'application

L'app est **multi-utilisateurs** : chaque personne se connecte avec son propre compte Spotify
et ses propres credentials d'app Spotify. Il n'y a plus de « wizard de setup » mono-utilisateur.

1. Ouvrir **`https://playlist.mondomaine.fr`** (le cadenas HTTPS doit être valide).
2. L'**écran de connexion** s'affiche : saisir `Client ID` / `Client Secret` de l'app Spotify,
   puis cliquer **Connect Spotify**. Ces credentials sont enregistrés en base par utilisateur
   (jamais dans un fichier ni dans Git).
3. L'écran affiche la **Redirect URI exacte** à enregistrer dans le dashboard Spotify (valeur
   fournie par le backend = `https://<DOMAIN>/api/v1/auth/callback`). Elle doit correspondre
   **exactement** à celle déclarée à l'étape 5. Chaque utilisateur enregistre **la même** URL de
   callback dans **sa propre** app Spotify.
4. Le flux OAuth Spotify s'ouvre → autoriser → retour automatique sur le dashboard de l'app.
5. Configurer la fréquence de synchronisation. C'est en ligne ✅

### 7 bis. Checklist de vérification post-déploiement (smoke-test manuel)

Le vrai flux OAuth Spotify ne peut pas être testé en pytest ; le dérouler **une fois** après
chaque déploiement :

1. `SESSION_SECRET` renseigné dans `.env.prod` → le conteneur `backend` démarre (`make ps`
   le montre `healthy`). S'il manque, le backend refuse de booter (voir logs).
2. Ouvrir `https://<DOMAIN>` → la **Redirect URI affichée dans l'app** correspond exactement à
   celle enregistrée dans le dashboard Spotify.
3. Un **nouvel utilisateur** saisit ses credentials + se connecte → il atterrit sur son dashboard.
4. DevTools → Application → Cookies : le cookie `session` est `Secure` + `HttpOnly` +
   `SameSite=Lax`.
5. **Logout** (bouton dans la barre latérale) → cookie effacé → se reconnecter avec **le même
   compte** → mêmes données, **aucun doublon** d'utilisateur créé.

---

## 8. Exploitation au quotidien

| Action | Commande |
|--------|----------|
| Déployer / mettre à jour | `make deploy` |
| Suivre les logs | `make logs` |
| État des conteneurs | `make ps` |
| Redémarrer | `make restart` |
| Arrêter (données conservées) | `make down` |
| Sauvegarder la base | `make backup` → `backups/app-<date>.db` |

### Mettre à jour après un changement de code
```bash
git pull
make deploy            # rebuild + redémarre, sans perdre les données
```

### Sauvegardes automatiques
La seule donnée critique est `data/app.db`. Automatiser via crontab :
```bash
crontab -e
# Sauvegarde quotidienne à 3h du matin :
0 3 * * * cd /chemin/vers/playlist_spotify && make backup
```

---

## 9. Dépannage

| Symptôme | Cause probable / solution |
|----------|---------------------------|
| Pas de HTTPS / erreur certificat | Ports 80/443 non ouverts, ou DNS pas encore propagé. Vérifier `dig` + pare-feu, puis `make restart`. |
| `auth_error` après connexion Spotify | La Redirect URI **affichée dans l'app** (fournie par le backend) ne correspond pas exactement à celle du dashboard Spotify. Chaque utilisateur doit enregistrer le même `https://<DOMAIN>/api/v1/auth/callback` dans **sa propre** app Spotify. |
| Le backend refuse de démarrer / `RuntimeError: SESSION_SECRET...` | `SESSION_SECRET` absent (ou égal au défaut de dev) en posture prod. Générer `openssl rand -hex 32`, le mettre dans `.env.prod`, `make restart`. |
| 502 / l'API ne répond pas | Backend pas encore prêt. `make logs` ; vérifier que le conteneur `backend` est `healthy`. |
| « Spotify credentials not configured » | L'utilisateur ne s'est pas connecté — ressaisir Client ID/Secret sur l'écran de connexion. |
| Le frontend s'affiche mais pas de données | Vérifier que la sync a tourné (logs du scheduler) et que le compte Spotify est connecté. |

---

## 10. Points d'attention

- **Ne pas mettre plus d'un conteneur `backend`.** APScheduler tourne in-process et SQLite ne
  supporte pas les écritures concurrentes multi-process. Pour scaler horizontalement il faudrait
  migrer vers Postgres + scheduler distribué — **non nécessaire** pour cet usage (multi-utilisateurs
  mais faible volume, un seul process backend).
- Le **dev local** reste inchangé : `docker-compose up` (Vite :5173 + uvicorn `--reload` :8000).
  La prod utilise un fichier compose distinct (`docker-compose.prod.yml`).
- Le `.env` racine (anciens credentials Spotify) **n'est pas utilisé** en prod et reste gitignoré.
  À supprimer / régénérer s'il a pu fuiter.

---

## Récapitulatif express

```bash
# Sur le serveur, une fois Docker installé et le DNS pointé :
git clone <repo> playlist_spotify && cd playlist_spotify
cp .env.prod.example .env.prod && nano .env.prod   # DOMAIN + ACME_EMAIL + SESSION_SECRET
openssl rand -hex 32                                # → coller dans SESSION_SECRET
# (ajouter la Redirect URI affichée par l'app dans le dashboard Spotify)
make deploy
# → ouvrir https://<DOMAIN>, se connecter avec ses credentials Spotify. Terminé.
```

ENV_FILE := .env.prod
COMPOSE  := docker compose --env-file $(ENV_FILE) -f docker-compose.prod.yml

.PHONY: deploy logs down restart ps backup

deploy:        ## Build + démarre (ou met à jour) la prod
	$(COMPOSE) up -d --build

logs:          ## Suit les logs en temps réel
	$(COMPOSE) logs -f

down:          ## Arrête et supprime les conteneurs (les données restent)
	$(COMPOSE) down

restart:       ## Redémarre les conteneurs
	$(COMPOSE) restart

ps:            ## État des conteneurs
	$(COMPOSE) ps

backup:        ## Sauvegarde horodatée de la base SQLite dans backups/
	@mkdir -p backups
	@cp data/app.db backups/app-$$(date +%Y%m%d-%H%M%S).db
	@echo "✅ Backup → backups/app-$$(date +%Y%m%d-%H%M%S).db"

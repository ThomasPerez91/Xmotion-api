run:
	docker-compose up -d --build

reload:
	docker-compose down --volumes && docker-compose up --build -d

# Stopper les containers
stop:
	docker-compose down

# Afficher les logs
logs:
	docker-compose logs -f

# Lancer un shell dans le container API
shell:
	docker exec -it syncaurapi_api_1 sh

# Lancer un shell Redis
redis-shell:
	docker exec -it syncaurapi_redis_1 redis-cli
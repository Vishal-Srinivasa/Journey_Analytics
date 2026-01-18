docker build -t journey_analytics .
docker run --env-file .env -p 8503:8503 journey_analytics
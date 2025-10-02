CREATE USER keycloak WITH PASSWORD 'change-me';
CREATE DATABASE keycloak OWNER keycloak;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;